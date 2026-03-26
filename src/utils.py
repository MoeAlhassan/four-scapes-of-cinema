"""Shared paths and utility functions for the film network analysis pipeline."""

from pathlib import Path

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent
DATA_RAW = PROJECT_ROOT / "data" / "raw"
DATA_PROCESSED = PROJECT_ROOT / "data" / "processed"
DATA_NETWORKS = PROJECT_ROOT / "data" / "networks"

# IMDb files
TITLE_BASICS = DATA_RAW / "title.basics.tsv"
TITLE_RATINGS = DATA_RAW / "title.ratings.tsv"
TITLE_PRINCIPALS = DATA_RAW / "title.principals.tsv"
TITLE_CREW = DATA_RAW / "title.crew.tsv"
NAME_BASICS = DATA_RAW / "name.basics.tsv"

# TMDB
TMDB_MOVIES = DATA_RAW / "tmdb_movies.csv"

# Processed outputs
FILMS_PARQUET = DATA_PROCESSED / "films.parquet"
PEOPLE_PARQUET = DATA_PROCESSED / "people.parquet"
FILM_PEOPLE_PARQUET = DATA_PROCESSED / "film_people.parquet"
WIKIDATA_PARQUET = DATA_PROCESSED / "wikidata_origins.parquet"

# Thresholds
MIN_VOTES = 153_000

# Ensure directories exist
for d in [DATA_RAW, DATA_PROCESSED, DATA_NETWORKS]:
    d.mkdir(parents=True, exist_ok=True)


def load_imdb_tsv(path, **kwargs):
    """Load an IMDb TSV file, replacing '\\N' with NaN."""
    import pandas as pd
    return pd.read_csv(path, sep='\t', na_values='\\N', low_memory=False, **kwargs)
