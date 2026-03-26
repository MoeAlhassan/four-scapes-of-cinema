"""Cross-network disjuncture analysis — measuring where scapes converge and diverge.

Computes:
  - Spearman rank correlation of centrality across all scape pairs
  - NMI and ARI of community assignments across all scape pairs
  - Per-person disjuncture score (variance of normalized centrality ranks)
"""

import json
import pandas as pd
import numpy as np
from scipy.stats import spearmanr
from sklearn.metrics import normalized_mutual_info_score, adjusted_rand_score
from utils import DATA_NETWORKS, PEOPLE_PARQUET

SCAPE_NAMES = ["mediascape", "ethnoscape_cross", "ethnoscape_same", "financescape", "ideoscape"]


def centrality_correlations(metrics):
    """Spearman rank correlation of degree/betweenness across scape pairs."""
    results = []
    for metric_type in ["degree", "betweenness", "eigenvector"]:
        cols = [f"{s}_{metric_type}" for s in SCAPE_NAMES]
        available = [c for c in cols if c in metrics.columns]

        for i, c1 in enumerate(available):
            for c2 in available[i + 1:]:
                subset = metrics[[c1, c2]].dropna()
                if len(subset) < 10:
                    continue
                rho, pval = spearmanr(subset[c1], subset[c2])
                results.append({
                    "metric": metric_type,
                    "scape_1": c1.replace(f"_{metric_type}", ""),
                    "scape_2": c2.replace(f"_{metric_type}", ""),
                    "spearman_rho": round(rho, 4),
                    "p_value": pval,
                    "n": len(subset),
                })
    return pd.DataFrame(results)


def community_comparisons(metrics):
    """NMI and ARI of community assignments across scape pairs."""
    results = []
    comm_cols = [f"{s}_community" for s in SCAPE_NAMES]
    available = [c for c in comm_cols if c in metrics.columns]

    for i, c1 in enumerate(available):
        for c2 in available[i + 1:]:
            subset = metrics[[c1, c2]].dropna()
            subset = subset[(subset[c1] >= 0) & (subset[c2] >= 0)]
            if len(subset) < 10:
                continue
            nmi = normalized_mutual_info_score(
                subset[c1].astype(int), subset[c2].astype(int)
            )
            ari = adjusted_rand_score(
                subset[c1].astype(int), subset[c2].astype(int)
            )
            results.append({
                "scape_1": c1.replace("_community", ""),
                "scape_2": c2.replace("_community", ""),
                "nmi": round(nmi, 4),
                "ari": round(ari, 4),
                "n": len(subset),
            })
    return pd.DataFrame(results)


def per_person_disjuncture(metrics):
    """Compute disjuncture score per person — variance of normalized centrality ranks.

    High disjuncture = person is important in some scapes but not others.
    This is the core Appadurai-inspired metric.
    """
    degree_cols = [f"{s}_degree" for s in SCAPE_NAMES]
    available = [c for c in degree_cols if c in metrics.columns]

    # Rank within each scape (percentile rank)
    ranks = pd.DataFrame({"nconst": metrics["nconst"]})
    for col in available:
        valid = metrics[col].notna()
        ranks.loc[valid, col + "_rank"] = metrics.loc[valid, col].rank(pct=True)

    rank_cols = [c + "_rank" for c in available]
    ranks["disjuncture_score"] = ranks[rank_cols].var(axis=1)
    ranks["rank_spread"] = ranks[rank_cols].max(axis=1) - ranks[rank_cols].min(axis=1)

    return ranks[["nconst", "disjuncture_score", "rank_spread"] + rank_cols]


def main():
    metrics = pd.read_csv(DATA_NETWORKS / "metrics.csv")
    people = pd.read_parquet(PEOPLE_PARQUET)

    # Centrality correlations
    print("=" * 60)
    print("CENTRALITY CORRELATIONS ACROSS SCAPES")
    print("=" * 60)
    corr_df = centrality_correlations(metrics)
    if not corr_df.empty:
        print(corr_df.to_string(index=False))
    else:
        print("  No valid correlations computed")

    # Community comparisons
    print(f"\n{'='*60}")
    print("COMMUNITY STRUCTURE COMPARISONS (NMI / ARI)")
    print("=" * 60)
    comm_df = community_comparisons(metrics)
    if not comm_df.empty:
        print(comm_df.to_string(index=False))
        print("\n  Interpretation: NMI < 0.3 = meaningful disjuncture, > 0.5 = alignment")
    else:
        print("  No valid comparisons computed")

    # Per-person disjuncture
    print(f"\n{'='*60}")
    print("PER-PERSON DISJUNCTURE SCORES")
    print("=" * 60)
    disj_df = per_person_disjuncture(metrics)
    print(f"  Mean disjuncture: {disj_df['disjuncture_score'].mean():.4f}")
    print(f"  Median disjuncture: {disj_df['disjuncture_score'].median():.4f}")
    print(f"  Std disjuncture: {disj_df['disjuncture_score'].std():.4f}")

    # Top 20 most disjunct people
    top_disj = disj_df.nlargest(20, "disjuncture_score").merge(
        people[["nconst", "primaryName"]], on="nconst"
    )
    print(f"\nTop 20 most 'disjunct' people (different importance across scapes):")
    for _, row in top_disj.iterrows():
        print(f"  {row['primaryName']}: disjuncture={row['disjuncture_score']:.4f}, spread={row['rank_spread']:.4f}")

    # Save all results
    corr_df.to_csv(DATA_NETWORKS / "centrality_correlations.csv", index=False)
    comm_df.to_csv(DATA_NETWORKS / "community_comparisons.csv", index=False)
    disj_df.to_csv(DATA_NETWORKS / "disjuncture_scores.csv", index=False)

    # Combined JSON summary for Observable
    summary = {
        "centrality_correlations": corr_df.to_dict(orient="records") if not corr_df.empty else [],
        "community_comparisons": comm_df.to_dict(orient="records") if not comm_df.empty else [],
        "summary_stats": {
            "mean_disjuncture": float(disj_df["disjuncture_score"].mean()),
            "median_disjuncture": float(disj_df["disjuncture_score"].median()),
            "std_disjuncture": float(disj_df["disjuncture_score"].std()),
        },
    }
    with open(DATA_NETWORKS / "disjuncture.json", "w") as f:
        json.dump(summary, f, indent=2)

    print(f"\nSaved disjuncture analysis to {DATA_NETWORKS}")


if __name__ == "__main__":
    main()
