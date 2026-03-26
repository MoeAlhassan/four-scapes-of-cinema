"""Compute per-network metrics and community detection for all four scapes.

For each scape computes: degree centrality, betweenness centrality,
eigenvector centrality, clustering coefficient, Leiden community assignment.
Also computes Blau geographic diversity index for directors/producers.
"""

import json
import pandas as pd
import numpy as np
import networkx as nx
import igraph as ig
import leidenalg
from collections import Counter
from utils import DATA_NETWORKS, WIKIDATA_PARQUET, FILM_PEOPLE_PARQUET

LEIDEN_SEED = 42
SCAPE_NAMES = ["mediascape", "ethnoscape_cross", "ethnoscape_same", "financescape", "ideoscape"]


def nx_to_igraph(G):
    """Convert NetworkX graph to igraph for Leiden community detection."""
    mapping = {node: i for i, node in enumerate(G.nodes())}
    reverse_mapping = {i: node for node, i in mapping.items()}
    edges = [(mapping[u], mapping[v]) for u, v in G.edges()]
    weights = [G[u][v].get("weight", 1.0) for u, v in G.edges()]
    ig_graph = ig.Graph(n=len(mapping), edges=edges, directed=False)
    ig_graph.es["weight"] = weights
    return ig_graph, reverse_mapping


def compute_metrics(G, name):
    """Compute standard network metrics for a graph."""
    print(f"\n{'='*60}")
    print(f"Computing metrics for {name}")
    print(f"{'='*60}")
    print(f"  Nodes: {G.number_of_nodes()}, Edges: {G.number_of_edges()}")
    print(f"  Density: {nx.density(G):.6f}")

    # Largest connected component
    components = list(nx.connected_components(G))
    largest_cc = max(components, key=len)
    G_cc = G.subgraph(largest_cc).copy()
    print(f"  Connected components: {len(components)}")
    print(f"  Largest CC: {len(largest_cc)} nodes ({len(largest_cc)/G.number_of_nodes()*100:.1f}%)")

    # Centrality metrics (on largest CC)
    print("  Computing degree centrality...")
    degree = nx.degree_centrality(G_cc)

    print("  Computing betweenness centrality (sampled k=500)...")
    betweenness = nx.betweenness_centrality(
        G_cc, weight="weight", k=min(500, len(G_cc))
    )

    print("  Computing eigenvector centrality...")
    try:
        eigenvector = nx.eigenvector_centrality(G_cc, weight="weight", max_iter=1000)
    except nx.PowerIterationFailedConvergence:
        print("    Eigenvector centrality did not converge — using degree as proxy")
        eigenvector = degree

    print("  Computing clustering coefficients...")
    clustering = nx.clustering(G_cc, weight="weight")

    # Leiden community detection
    print("  Running Leiden community detection...")
    ig_graph, reverse_mapping = nx_to_igraph(G_cc)
    partition = leidenalg.find_partition(
        ig_graph,
        leidenalg.ModularityVertexPartition,
        weights=ig_graph.es["weight"],
        seed=LEIDEN_SEED,
    )
    communities = {}
    for comm_id, members in enumerate(partition):
        for member in members:
            node = reverse_mapping[member]
            communities[node] = comm_id

    print(f"  Communities found: {len(partition)}")
    print(f"  Modularity: {partition.modularity:.4f}")
    sizes = sorted([len(c) for c in partition], reverse=True)
    print(f"  Top 5 community sizes: {sizes[:5]}")

    # Assemble per-node metrics
    metrics = []
    for node in G_cc.nodes():
        metrics.append({
            "nconst": node,
            f"{name}_degree": degree.get(node, 0),
            f"{name}_betweenness": betweenness.get(node, 0),
            f"{name}_eigenvector": eigenvector.get(node, 0),
            f"{name}_clustering": clustering.get(node, 0),
            f"{name}_community": communities.get(node, -1),
        })

    return pd.DataFrame(metrics)


def compute_blau_index(film_people, origins):
    """Compute Blau geographic diversity index per director/producer.

    Blau = 1 - sum(p_i^2) where p_i is proportion of collaborators from country i.
    Ranges from 0 (all same country) to ~1 (evenly spread across many countries).
    """
    directors_producers = film_people[
        film_people["category"].isin(["director", "producer"])
    ].copy()

    origin_map = origins.set_index("nconst")["country"].to_dict()

    results = []
    for nconst, group in directors_producers.groupby("nconst"):
        their_films = group["tconst"].unique()
        collaborators = film_people[
            (film_people["tconst"].isin(their_films)) &
            (film_people["nconst"] != nconst)
        ]["nconst"].unique()

        countries = [origin_map[c] for c in collaborators if c in origin_map]
        if not countries:
            results.append({"nconst": nconst, "blau_index": None, "n_collab_with_origin": 0})
            continue

        total = len(countries)
        counts = Counter(countries)
        proportions = [c / total for c in counts.values()]
        blau = 1 - sum(p**2 for p in proportions)

        results.append({
            "nconst": nconst,
            "blau_index": blau,
            "n_collab_with_origin": total,
            "n_countries": len(counts),
        })

    return pd.DataFrame(results)


def main():
    # Load networks from JSON
    scapes = {}
    for name in SCAPE_NAMES:
        path = DATA_NETWORKS / f"{name}.json"
        if not path.exists():
            print(f"WARNING: {path} not found, skipping {name}")
            continue
        with open(path) as f:
            data = json.load(f)
        G = nx.node_link_graph(data)
        scapes[name] = G

    # Compute metrics per scape
    all_metrics = []
    for name, G in scapes.items():
        metrics_df = compute_metrics(G, name)
        all_metrics.append(metrics_df)

    # Merge all metrics on nconst
    combined = all_metrics[0]
    for df in all_metrics[1:]:
        combined = combined.merge(df, on="nconst", how="outer")

    # Add Blau index
    film_people = pd.read_parquet(FILM_PEOPLE_PARQUET)
    if WIKIDATA_PARQUET.exists():
        origins = pd.read_parquet(WIKIDATA_PARQUET)
        print("\nComputing Blau geographic diversity index...")
        blau = compute_blau_index(film_people, origins)
        combined = combined.merge(blau, on="nconst", how="left")
        print(f"  Directors/producers with Blau: {blau['blau_index'].notna().sum()}")
        print(f"  Mean Blau index: {blau['blau_index'].mean():.4f}")
    else:
        print("No Wikidata file — skipping Blau index")

    # Save
    combined.to_csv(DATA_NETWORKS / "metrics.csv", index=False)
    print(f"\nSaved metrics for {len(combined)} people to {DATA_NETWORKS / 'metrics.csv'}")

    # Save community assignments separately
    comm_cols = ["nconst"] + [c for c in combined.columns if "community" in c]
    combined[comm_cols].to_csv(DATA_NETWORKS / "communities.csv", index=False)

    # Quick sanity check: top people by degree
    from utils import PEOPLE_PARQUET
    people = pd.read_parquet(PEOPLE_PARQUET)
    m = combined.merge(people[["nconst", "primaryName"]], on="nconst", how="left")
    for scape in SCAPE_NAMES:
        col = f"{scape}_degree"
        if col in m.columns:
            print(f"\nTop 5 by {scape} degree:")
            top = m.nlargest(5, col)[["primaryName", col]]
            for _, row in top.iterrows():
                print(f"  {row['primaryName']}: {row[col]:.4f}")


if __name__ == "__main__":
    main()
