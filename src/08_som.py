"""Self-Organizing Map for film professional archetypes.

Constructs a feature vector per person from centrality scores across all 4 scapes,
clustering coefficients, Blau diversity index, avg rating, and avg ROI.
Normalizes features, trains SOM, and exports grid with heatmap overlays.
"""

import json
import pandas as pd
import numpy as np
from minisom import MiniSom
from utils import DATA_NETWORKS, FILMS_PARQUET, FILM_PEOPLE_PARQUET, PEOPLE_PARQUET

SOM_X, SOM_Y = 15, 15  # Grid dimensions
SOM_ITERATIONS = 10000
SOM_SIGMA = 3.0
SOM_LEARNING_RATE = 0.5
RANDOM_SEED = 42

SCAPE_NAMES = ["mediascape", "ethnoscape_cross", "ethnoscape_same", "financescape", "ideoscape"]


def build_feature_matrix(metrics):
    """Build normalized feature matrix for SOM training.

    Returns (X, nconsts, feature_cols, df) where X is the feature matrix.
    """
    # Centrality features: degree + betweenness per scape
    feature_cols = []
    for scape in SCAPE_NAMES:
        for metric in ["degree", "betweenness"]:
            col = f"{scape}_{metric}"
            if col in metrics.columns:
                feature_cols.append(col)
        clust = f"{scape}_clustering"
        if clust in metrics.columns:
            feature_cols.append(clust)

    # Blau index
    if "blau_index" in metrics.columns:
        feature_cols.append("blau_index")

    # Average rating + ROI per person
    film_people = pd.read_parquet(FILM_PEOPLE_PARQUET)
    films = pd.read_parquet(FILMS_PARQUET)

    person_films = film_people.merge(films[["tconst", "averageRating", "roi"]], on="tconst")
    avg_rating = person_films.groupby("nconst")["averageRating"].mean().reset_index()
    avg_rating.columns = ["nconst", "avg_rating"]
    avg_roi = person_films.groupby("nconst")["roi"].mean().reset_index()
    avg_roi.columns = ["nconst", "avg_roi"]

    df = metrics.merge(avg_rating, on="nconst", how="left")
    df = df.merge(avg_roi, on="nconst", how="left")
    feature_cols.extend(["avg_rating", "avg_roi"])

    # Impute missing with median + add missing indicators
    for col in feature_cols:
        df[f"{col}_missing"] = df[col].isna().astype(int)
        median_val = df[col].median()
        df[col] = df[col].fillna(median_val if pd.notna(median_val) else 0)

    # Z-score normalization
    for col in feature_cols:
        std = df[col].std()
        if std > 0:
            df[col] = (df[col] - df[col].mean()) / std

    X = df[feature_cols].values.astype(np.float64)
    nconsts = df["nconst"].values

    # Remove any rows with NaN/Inf
    mask = np.isfinite(X).all(axis=1)
    X = X[mask]
    nconsts = nconsts[mask]
    df = df[mask].reset_index(drop=True)

    return X, nconsts, feature_cols, df


def train_som(X):
    """Train the SOM and return the trained model."""
    som = MiniSom(
        SOM_X, SOM_Y, X.shape[1],
        sigma=SOM_SIGMA,
        learning_rate=SOM_LEARNING_RATE,
        random_seed=RANDOM_SEED,
    )
    som.pca_weights_init(X)
    print(f"Training SOM ({SOM_X}x{SOM_Y} grid, {SOM_ITERATIONS} iterations)...")
    som.train(X, SOM_ITERATIONS, verbose=True)
    return som


def main():
    metrics = pd.read_csv(DATA_NETWORKS / "metrics.csv")
    people = pd.read_parquet(PEOPLE_PARQUET)

    X, nconsts, feature_cols, df = build_feature_matrix(metrics)
    print(f"Feature matrix: {X.shape[0]} people × {X.shape[1]} features")
    print(f"Features: {feature_cols}")

    som = train_som(X)

    # Map each person to their BMU (best matching unit)
    bmu_map = {}
    grid_populations = np.zeros((SOM_X, SOM_Y))
    grid_features = {col: np.zeros((SOM_X, SOM_Y)) for col in feature_cols}
    grid_counts = np.zeros((SOM_X, SOM_Y))

    # Also collect names for the top people in each cell
    grid_people = [[[] for _ in range(SOM_Y)] for _ in range(SOM_X)]
    name_map = people.set_index("nconst")["primaryName"].to_dict()

    for i, x in enumerate(X):
        bmu = som.winner(x)
        nconst = nconsts[i]
        bmu_map[nconst] = {"x": int(bmu[0]), "y": int(bmu[1])}
        grid_populations[bmu[0], bmu[1]] += 1
        grid_counts[bmu[0], bmu[1]] += 1
        for j, col in enumerate(feature_cols):
            grid_features[col][bmu[0], bmu[1]] += df.iloc[i][col]
        grid_people[bmu[0]][bmu[1]].append(name_map.get(nconst, nconst))

    # Average features per cell
    for col in feature_cols:
        mask = grid_counts > 0
        grid_features[col][mask] /= grid_counts[mask]

    # Trim people lists to top 5 per cell (for JSON size)
    for i in range(SOM_X):
        for j in range(SOM_Y):
            grid_people[i][j] = grid_people[i][j][:5]

    # Compute U-matrix (average distance to neighboring cells)
    umatrix = np.zeros((SOM_X, SOM_Y))
    weights = som.get_weights()  # shape: (SOM_X, SOM_Y, n_features)
    for i in range(SOM_X):
        for j in range(SOM_Y):
            neighbors = []
            for di in [-1, 0, 1]:
                for dj in [-1, 0, 1]:
                    if di == 0 and dj == 0:
                        continue
                    ni, nj = i + di, j + dj
                    if 0 <= ni < SOM_X and 0 <= nj < SOM_Y:
                        dist = np.linalg.norm(weights[i, j] - weights[ni, nj])
                        neighbors.append(dist)
            umatrix[i, j] = np.mean(neighbors) if neighbors else 0

    print(f"U-matrix range: {umatrix.min():.4f} - {umatrix.max():.4f}")

    # Export SOM data
    som_data = {
        "grid_size": {"x": SOM_X, "y": SOM_Y},
        "features": feature_cols,
        "populations": grid_populations.tolist(),
        "heatmaps": {col: grid_features[col].tolist() for col in feature_cols},
        "umatrix": umatrix.tolist(),
        "person_bmus": {str(k): v for k, v in bmu_map.items()},
        "sample_people": grid_people,
    }

    with open(DATA_NETWORKS / "som_grid.json", "w") as f:
        json.dump(som_data, f)

    print(f"\nSOM trained and exported to {DATA_NETWORKS / 'som_grid.json'}")
    print(f"Grid occupancy: {(grid_populations > 0).sum():.0f}/{SOM_X * SOM_Y} cells occupied")
    print(f"Max cell population: {grid_populations.max():.0f}")
    occupied = grid_populations[grid_populations > 0]
    print(f"Mean cell population (occupied): {occupied.mean():.1f}")
    print(f"Median cell population (occupied): {np.median(occupied):.1f}")


if __name__ == "__main__":
    main()
