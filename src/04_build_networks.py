"""Build four scape networks from processed film data.

Networks:
  1. Mediascape  — person-person weighted by Newman projection of film co-appearance
  2. Ethnoscape  — same edges, attributed with cross-origin / same-origin
  3. Financescape — subgraph restricted to films with budget+revenue data
  4. Ideoscape   — person-person edges weighted by genre Jaccard similarity
"""

import json
import pandas as pd
import networkx as nx
from collections import defaultdict
from itertools import combinations
from tqdm import tqdm
from utils import (
    FILMS_PARQUET, PEOPLE_PARQUET, FILM_PEOPLE_PARQUET,
    WIKIDATA_PARQUET, DATA_NETWORKS,
)


def newman_weight(cast_size):
    """Newman weighting: 1 / (k - 1) for a film with k cast/crew.

    Downweights connections from large-cast films (where co-appearance is less
    meaningful) and upweights connections from small-cast films.
    """
    if cast_size <= 1:
        return 0.0
    return 1.0 / (cast_size - 1)


def build_person_film_groups(film_people):
    """Group people by film, returning dict of tconst -> list of nconsts."""
    return film_people.groupby("tconst")["nconst"].apply(
        lambda x: list(set(x))
    ).to_dict()


def build_mediascape(film_people, people):
    """Build person-person network from film co-appearance with Newman weighting."""
    G = nx.Graph()
    film_groups = build_person_film_groups(film_people)

    # Add all people as nodes with name attribute
    name_map = people.set_index("nconst")["primaryName"].to_dict()
    for nconst in film_people["nconst"].unique():
        G.add_node(nconst, name=name_map.get(nconst, ""))

    edge_weights = defaultdict(float)
    edge_film_count = defaultdict(int)

    for tconst, people_list in tqdm(film_groups.items(), desc="Mediascape edges"):
        w = newman_weight(len(people_list))
        if w == 0:
            continue
        for p1, p2 in combinations(sorted(people_list), 2):
            edge_weights[(p1, p2)] += w
            edge_film_count[(p1, p2)] += 1

    for (p1, p2), weight in edge_weights.items():
        G.add_edge(p1, p2, weight=weight, n_films=edge_film_count[(p1, p2)])

    print(f"Mediascape: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")
    return G


def build_ethnoscape_split(mediascape, origins):
    """Split mediascape into cross-origin and same-origin subgraphs.

    Cross-origin: only edges between people from different countries.
    Same-origin: only edges between people from the same country.
    Edges where either person's origin is unknown are excluded from both.

    This creates structurally distinct networks that capture how geographic
    flows differ from pure collaboration flows (Appadurai's ethnoscape).
    """
    origin_map = origins.set_index("nconst")["country"].to_dict()

    G_cross = nx.Graph()
    G_same = nx.Graph()

    # Add all nodes with country attribute to both
    for node in mediascape.nodes():
        country = origin_map.get(node)
        G_cross.add_node(node, **mediascape.nodes[node], country=country)
        G_same.add_node(node, **mediascape.nodes[node], country=country)

    cross_count = 0
    same_count = 0
    unknown_count = 0

    for u, v, data in mediascape.edges(data=True):
        c1 = origin_map.get(u)
        c2 = origin_map.get(v)
        if c1 and c2:
            if c1 != c2:
                G_cross.add_edge(u, v, **data)
                cross_count += 1
            else:
                G_same.add_edge(u, v, **data)
                same_count += 1
        else:
            unknown_count += 1

    # Remove isolated nodes (no edges in this subgraph)
    cross_isolates = list(nx.isolates(G_cross))
    same_isolates = list(nx.isolates(G_same))
    G_cross.remove_nodes_from(cross_isolates)
    G_same.remove_nodes_from(same_isolates)

    print(f"Ethnoscape cross-origin: {G_cross.number_of_nodes()} nodes, {cross_count} edges")
    print(f"Ethnoscape same-origin:  {G_same.number_of_nodes()} nodes, {same_count} edges")
    print(f"Edges with unknown origin (excluded): {unknown_count}")

    return G_cross, G_same


def build_financescape(film_people, films, people):
    """Build person-person network restricted to films with financial data."""
    financial_films = films[films["budget"].notna() & films["revenue"].notna()].copy()
    financial_tconsts = set(financial_films["tconst"])
    print(f"Films with financial data: {len(financial_tconsts)}")

    fp_financial = film_people[film_people["tconst"].isin(financial_tconsts)]
    film_groups = fp_financial.groupby("tconst")["nconst"].apply(
        lambda x: list(set(x))
    ).to_dict()

    budget_map = financial_films.set_index("tconst")["budget"].to_dict()
    revenue_map = financial_films.set_index("tconst")["revenue"].to_dict()
    roi_map = financial_films.set_index("tconst")["roi"].to_dict()

    name_map = people.set_index("nconst")["primaryName"].to_dict()

    G = nx.Graph()
    edge_budgets = defaultdict(list)
    edge_weights = defaultdict(float)

    for tconst, people_list in tqdm(film_groups.items(), desc="Financescape edges"):
        w = newman_weight(len(people_list))
        if w == 0:
            continue
        for p1, p2 in combinations(sorted(people_list), 2):
            edge_weights[(p1, p2)] += w
            edge_budgets[(p1, p2)].append({
                "budget": budget_map.get(tconst, 0),
                "revenue": revenue_map.get(tconst, 0),
                "roi": roi_map.get(tconst),
            })

    for (p1, p2), budgets in edge_budgets.items():
        avg_budget = sum(b["budget"] for b in budgets) / len(budgets)
        avg_revenue = sum(b["revenue"] for b in budgets) / len(budgets)
        rois = [b["roi"] for b in budgets if b["roi"] is not None]
        avg_roi = sum(rois) / len(rois) if rois else None
        G.add_node(p1, name=name_map.get(p1, ""))
        G.add_node(p2, name=name_map.get(p2, ""))
        G.add_edge(p1, p2,
                    weight=edge_weights[(p1, p2)],
                    avg_budget=avg_budget,
                    avg_revenue=avg_revenue,
                    avg_roi=avg_roi,
                    n_films=len(budgets))

    print(f"Financescape: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")
    return G


def build_ideoscape(film_people, films, people):
    """Build person-person network weighted by genre similarity (Jaccard)."""
    # Genre set per film
    genre_sets = {}
    for _, row in films.iterrows():
        if pd.notna(row.get("genres")):
            genre_sets[row["tconst"]] = set(row["genres"].split(","))

    # Person genre portfolios
    person_genres = defaultdict(set)
    film_groups = build_person_film_groups(film_people)

    for tconst, people_list in film_groups.items():
        genres = genre_sets.get(tconst, set())
        for p in people_list:
            person_genres[p].update(genres)

    name_map = people.set_index("nconst")["primaryName"].to_dict()

    G = nx.Graph()
    edge_data = defaultdict(lambda: {"newman_weight": 0.0, "shared_films": 0})

    for tconst, people_list in tqdm(film_groups.items(), desc="Ideoscape edges"):
        w = newman_weight(len(people_list))
        if w == 0:
            continue
        for p1, p2 in combinations(sorted(people_list), 2):
            edge_data[(p1, p2)]["newman_weight"] += w
            edge_data[(p1, p2)]["shared_films"] += 1

    for (p1, p2), data in edge_data.items():
        g1 = person_genres.get(p1, set())
        g2 = person_genres.get(p2, set())
        jaccard = len(g1 & g2) / len(g1 | g2) if (g1 and g2) else 0.0
        G.add_node(p1, name=name_map.get(p1, ""), genres=list(person_genres.get(p1, set())))
        G.add_node(p2, name=name_map.get(p2, ""), genres=list(person_genres.get(p2, set())))
        G.add_edge(p1, p2,
                    weight=data["newman_weight"],
                    genre_similarity=jaccard,
                    n_films=data["shared_films"])

    print(f"Ideoscape: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")
    return G


def graph_to_json(G, name):
    """Export graph to node-link JSON for Observable."""
    data = nx.node_link_data(G)
    path = DATA_NETWORKS / f"{name}.json"
    with open(path, "w") as f:
        json.dump(data, f, default=str)
    print(f"  Saved {path} ({path.stat().st_size / 1e6:.1f} MB)")


def main():
    print("Loading processed data...")
    films = pd.read_parquet(FILMS_PARQUET)
    people = pd.read_parquet(PEOPLE_PARQUET)
    film_people = pd.read_parquet(FILM_PEOPLE_PARQUET)

    origins = pd.DataFrame()
    if WIKIDATA_PARQUET.exists():
        origins = pd.read_parquet(WIKIDATA_PARQUET)
        print(f"Loaded {len(origins)} Wikidata origin records")
    else:
        print("WARNING: No Wikidata origins file. Ethnoscape will have no country data.")

    # Build networks
    mediascape = build_mediascape(film_people, people)
    ethno_cross, ethno_same = build_ethnoscape_split(mediascape, origins)
    financescape = build_financescape(film_people, films, people)
    ideoscape = build_ideoscape(film_people, films, people)

    # Export to JSON
    graph_to_json(mediascape, "mediascape")
    graph_to_json(ethno_cross, "ethnoscape_cross")
    graph_to_json(ethno_same, "ethnoscape_same")
    graph_to_json(financescape, "financescape")
    graph_to_json(ideoscape, "ideoscape")

    print("\nAll networks built and exported.")


if __name__ == "__main__":
    main()
