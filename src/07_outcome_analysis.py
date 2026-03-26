"""Outcome analysis: linking network structure to film performance.

Analyses:
  1. Geographic diversity (Blau index) → avg rating + avg ROI
  2. Mediation: diversity → budget → rating (does budget explain the effect?)
  3. Cluster tightness (clustering coefficient) → outcomes (directors)
  4. Brokerage (betweenness centrality) → outcomes (directors)
  5. Writer clustering → rating (controlling for budget)
  6. Writer brokerage → rating (controlling for budget)
  7. Writer community quality breakdown

Uses OLS with robust standard errors.
"""

import json
import pandas as pd
import numpy as np
import statsmodels.api as sm
from utils import FILMS_PARQUET, PEOPLE_PARQUET, FILM_PEOPLE_PARQUET, DATA_NETWORKS


def build_director_outcomes(films, film_people, metrics):
    """Build per-director dataset with avg rating, avg ROI, and network metrics."""
    directors = film_people[film_people["category"] == "director"].copy()
    director_films = directors.merge(
        films[["tconst", "averageRating", "roi", "budget", "startYear"]],
        on="tconst",
    )

    agg = director_films.groupby("nconst").agg(
        avg_rating=("averageRating", "mean"),
        avg_roi=("roi", lambda x: x.dropna().mean() if x.notna().any() else np.nan),
        n_films=("tconst", "nunique"),
        avg_budget=("budget", lambda x: x.dropna().mean() if x.notna().any() else np.nan),
        avg_year=("startYear", lambda x: x.dropna().astype(float).mean()),
    ).reset_index()

    agg = agg.merge(metrics, on="nconst", how="left")
    return agg


def run_regression(df, y_col, x_cols, name):
    """Run OLS regression with robust standard errors (HC1)."""
    subset = df.dropna(subset=[y_col] + x_cols)
    if len(subset) < 30:
        print(f"  Skipping {name}: only {len(subset)} observations")
        return None

    X = sm.add_constant(subset[x_cols].astype(float))
    y = subset[y_col].astype(float)

    # Drop infinite values
    mask = np.isfinite(X).all(axis=1) & np.isfinite(y)
    X = X[mask]
    y = y[mask]

    if len(y) < 30:
        print(f"  Skipping {name}: only {len(y)} finite observations")
        return None

    model = sm.OLS(y, X).fit(cov_type="HC1")

    print(f"\n{'─'*60}")
    print(f"Regression: {name}")
    print(f"{'─'*60}")
    print(f"  N = {len(y)}, R² = {model.rsquared:.4f}, Adj R² = {model.rsquared_adj:.4f}")
    print(f"  F-stat = {model.fvalue:.2f}, p = {model.f_pvalue:.4e}")
    for var in model.params.index:
        sig = ""
        if model.pvalues[var] < 0.001:
            sig = "***"
        elif model.pvalues[var] < 0.01:
            sig = "**"
        elif model.pvalues[var] < 0.05:
            sig = "*"
        print(f"  {var:30s} β={model.params[var]:10.4f}  SE={model.bse[var]:.4f}  p={model.pvalues[var]:.4f} {sig}")

    return {
        "name": name,
        "n": int(len(y)),
        "r_squared": float(model.rsquared),
        "adj_r_squared": float(model.rsquared_adj),
        "f_stat": float(model.fvalue),
        "f_pvalue": float(model.f_pvalue),
        "coefficients": {
            var: {
                "coef": float(model.params[var]),
                "std_err": float(model.bse[var]),
                "p_value": float(model.pvalues[var]),
                "ci_lower": float(model.conf_int().loc[var, 0]),
                "ci_upper": float(model.conf_int().loc[var, 1]),
            }
            for var in model.params.index
        },
    }


def run_mediation(df, x_col, mediator_col, y_col, controls, name):
    """Run Baron-Kenny mediation analysis: X → M → Y.

    Steps:
      1. Total effect:  X → Y (without mediator)
      2. X → M:         does X predict the mediator?
      3. Direct effect:  X → Y controlling for M
      Indirect = total - direct
    """
    cols = [x_col, mediator_col, y_col] + controls
    subset = df.dropna(subset=cols)
    mask = np.all(np.isfinite(subset[cols].astype(float)), axis=1)
    subset = subset[mask]

    if len(subset) < 30:
        print(f"  Skipping mediation {name}: only {len(subset)} observations")
        return None

    print(f"\n{'─'*60}")
    print(f"Mediation: {name}")
    print(f"{'─'*60}")
    print(f"  N = {len(subset)}")

    # Step 1: Total effect (X → Y, no mediator)
    X1 = sm.add_constant(subset[[x_col] + controls].astype(float))
    m1 = sm.OLS(subset[y_col].astype(float), X1).fit(cov_type="HC1")
    total = m1.params[x_col]
    print(f"\n  Step 1 — Total effect ({x_col} → {y_col}):")
    print(f"    β = {total:.4f}, p = {m1.pvalues[x_col]:.4f}")

    # Step 2: X → Mediator
    X2 = sm.add_constant(subset[[x_col] + controls].astype(float))
    m2 = sm.OLS(subset[mediator_col].astype(float), X2).fit(cov_type="HC1")
    print(f"\n  Step 2 — {x_col} → {mediator_col}:")
    print(f"    β = {m2.params[x_col]:.4f}, p = {m2.pvalues[x_col]:.4f}")

    # Step 3: Direct effect (X → Y controlling for mediator)
    X3 = sm.add_constant(subset[[x_col, mediator_col] + controls].astype(float))
    m3 = sm.OLS(subset[y_col].astype(float), X3).fit(cov_type="HC1")
    direct = m3.params[x_col]
    indirect = total - direct
    pct = (indirect / total * 100) if total != 0 else 0

    print(f"\n  Step 3 — Direct effect ({x_col} → {y_col}, controlling for {mediator_col}):")
    for var in [x_col, mediator_col] + controls:
        sig = ""
        if m3.pvalues[var] < 0.001:
            sig = "***"
        elif m3.pvalues[var] < 0.01:
            sig = "**"
        elif m3.pvalues[var] < 0.05:
            sig = "*"
        print(f"    {var:30s} β={m3.params[var]:10.4f}  p={m3.pvalues[var]:.4f} {sig}")
    print(f"    R² = {m3.rsquared:.4f}")

    print(f"\n  Summary:")
    print(f"    Total effect:          {total:.4f}")
    print(f"    Direct effect:         {direct:.4f}")
    print(f"    Indirect (via {mediator_col}): {indirect:.4f} ({pct:.0f}% mediated)")

    return {
        "name": name,
        "n": int(len(subset)),
        "total_effect": {"coef": float(total), "p_value": float(m1.pvalues[x_col])},
        "x_to_mediator": {"coef": float(m2.params[x_col]), "p_value": float(m2.pvalues[x_col])},
        "direct_effect": {"coef": float(direct), "p_value": float(m3.pvalues[x_col])},
        "indirect_effect": float(indirect),
        "pct_mediated": float(pct),
        "r_squared_full": float(m3.rsquared),
        "mediator_effect": {
            "coef": float(m3.params[mediator_col]),
            "p_value": float(m3.pvalues[mediator_col]),
        },
    }


def build_writer_outcomes(films, film_people, metrics):
    """Build per-writer dataset with avg rating, budget, and network metrics."""
    writers = film_people[film_people["category"] == "writer"].copy()
    writer_films = writers.merge(
        films[["tconst", "averageRating", "roi", "budget"]],
        on="tconst",
    )

    agg = writer_films.groupby("nconst").agg(
        avg_rating=("averageRating", "mean"),
        avg_budget=("budget", lambda x: x.dropna().mean() if x.notna().any() else np.nan),
        avg_roi=("roi", lambda x: x.dropna().mean() if x.notna().any() else np.nan),
        n_films=("tconst", "nunique"),
    ).reset_index()

    agg = agg.merge(metrics, on="nconst", how="left")
    # Log-transform budget for regression
    agg["log_budget"] = np.log10(agg["avg_budget"].clip(lower=1))
    return agg


def writer_community_breakdown(writers_df):
    """Show highest and lowest-rated writer communities with sample members."""
    wm = writers_df.copy()

    comm = wm.groupby("mediascape_community").agg(
        avg_rating=("avg_rating", "mean"),
        n_writers=("nconst", "count"),
        avg_clustering=("mediascape_clustering", "mean"),
    ).reset_index()
    comm = comm[comm["n_writers"] >= 10].sort_values("avg_rating", ascending=False)

    print(f"\n{'─'*60}")
    print("Writer communities by average rating")
    print(f"{'─'*60}")

    rows = []
    for _, row in comm.iterrows():
        cid = row["mediascape_community"]
        community_members = wm[wm["mediascape_community"] == cid]
        top_members = community_members.nlargest(3, "n_films")
        names = top_members["primaryName"].tolist()
        entry = {
            "community": int(cid),
            "avg_rating": round(row["avg_rating"], 2),
            "n_writers": int(row["n_writers"]),
            "avg_clustering": round(row["avg_clustering"], 4),
            "sample_writers": names,
        }
        rows.append(entry)

    print("\n  Top 5 (highest-rated):")
    for r in rows[:5]:
        print(f"    Community {r['community']:2d}: rating={r['avg_rating']:.2f}, "
              f"n={r['n_writers']}, clustering={r['avg_clustering']:.4f}  |  "
              f"{', '.join(r['sample_writers'])}")

    print("\n  Bottom 5 (lowest-rated):")
    for r in rows[-5:]:
        print(f"    Community {r['community']:2d}: rating={r['avg_rating']:.2f}, "
              f"n={r['n_writers']}, clustering={r['avg_clustering']:.4f}  |  "
              f"{', '.join(r['sample_writers'])}")

    return rows


def main():
    films = pd.read_parquet(FILMS_PARQUET)
    film_people = pd.read_parquet(FILM_PEOPLE_PARQUET)
    metrics = pd.read_csv(DATA_NETWORKS / "metrics.csv")
    people = pd.read_parquet(PEOPLE_PARQUET)

    results = []

    # ================================================================
    # DIRECTOR ANALYSIS
    # ================================================================
    directors = build_director_outcomes(films, film_people, metrics)
    directors = directors.merge(people[["nconst", "primaryName"]], on="nconst", how="left")
    # Log-transform budget for mediation
    directors["log_budget"] = np.log10(directors["avg_budget"].clip(lower=1))

    print(f"Directors with metrics: {len(directors)}")
    print(f"Directors with rating data: {directors['avg_rating'].notna().sum()}")
    print(f"Directors with ROI data: {directors['avg_roi'].notna().sum()}")

    # === RQ1: Geographic diversity → outcomes ===
    print(f"\n{'='*60}")
    print("RQ1: Geographic Diversity → Outcomes")
    print("=" * 60)

    if "blau_index" in directors.columns:
        r = run_regression(
            directors, "avg_rating",
            ["blau_index", "n_films"],
            "Diversity → Rating (total effect)",
        )
        if r:
            results.append(r)

        r = run_regression(
            directors, "avg_roi",
            ["blau_index", "n_films"],
            "Diversity → ROI",
        )
        if r:
            results.append(r)

        # Mediation: Diversity → Budget → Rating
        print(f"\n{'='*60}")
        print("MEDIATION: Diversity → Budget → Rating")
        print("=" * 60)

        med = run_mediation(
            directors,
            x_col="blau_index",
            mediator_col="log_budget",
            y_col="avg_rating",
            controls=["n_films"],
            name="Diversity → Budget → Rating",
        )
        if med:
            results.append(med)

    # === RQ2: Director cluster tightness → outcomes ===
    print(f"\n{'='*60}")
    print("RQ2: Director Cluster Tightness → Outcomes")
    print("=" * 60)

    r = run_regression(
        directors, "avg_rating",
        ["mediascape_clustering", "n_films"],
        "Director Cluster Tightness → Rating",
    )
    if r:
        results.append(r)

    r = run_regression(
        directors, "avg_roi",
        ["mediascape_clustering", "n_films"],
        "Director Cluster Tightness → ROI",
    )
    if r:
        results.append(r)

    # === RQ3: Director brokerage → outcomes ===
    print(f"\n{'='*60}")
    print("Director Brokerage → Outcomes")
    print("=" * 60)

    r = run_regression(
        directors, "avg_rating",
        ["mediascape_betweenness", "n_films"],
        "Director Brokerage → Rating",
    )
    if r:
        results.append(r)

    r = run_regression(
        directors, "avg_roi",
        ["mediascape_betweenness", "n_films"],
        "Director Brokerage → ROI",
    )
    if r:
        results.append(r)

    # ================================================================
    # WRITER ANALYSIS
    # ================================================================
    print(f"\n{'='*60}")
    print("WRITER NETWORK → OUTCOMES")
    print("=" * 60)

    writers = build_writer_outcomes(films, film_people, metrics)
    writers = writers.merge(people[["nconst", "primaryName"]], on="nconst", how="left")
    print(f"\nWriters with metrics: {len(writers)}")

    # Writer clustering → rating (controlling for budget)
    r = run_regression(
        writers, "avg_rating",
        ["mediascape_clustering", "log_budget", "n_films"],
        "Writer Clustering → Rating (budget-controlled)",
    )
    if r:
        results.append(r)

    # Writer brokerage → rating (controlling for budget)
    r = run_regression(
        writers, "avg_rating",
        ["mediascape_betweenness", "log_budget", "n_films"],
        "Writer Brokerage → Rating (budget-controlled)",
    )
    if r:
        results.append(r)

    # Writer cross-origin brokerage → rating (controlling for budget)
    if "ethnoscape_cross_betweenness" in writers.columns:
        r = run_regression(
            writers, "avg_rating",
            ["ethnoscape_cross_betweenness", "log_budget", "n_films"],
            "Writer Cross-Origin Brokerage → Rating (budget-controlled)",
        )
        if r:
            results.append(r)

    # Writer community breakdown
    comm_data = writer_community_breakdown(writers)

    # ================================================================
    # SAVE ALL RESULTS
    # ================================================================
    output = {
        "regressions": results,
        "writer_communities": comm_data,
    }
    with open(DATA_NETWORKS / "regression_results.json", "w") as f:
        json.dump(output, f, indent=2)
    print(f"\nSaved {len(results)} regression results + writer communities to "
          f"{DATA_NETWORKS / 'regression_results.json'}")


if __name__ == "__main__":
    main()
