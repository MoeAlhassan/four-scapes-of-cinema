"""Fetch budget/revenue data from TMDB API for our top films.

Usage:
    1. Create .env file in project root with: TMDB_API_KEY=your_key_here
    2. Run: python 01b_download_tmdb.py

Queries TMDB's /find endpoint by IMDb ID for each film, then fetches
the movie details for budget and revenue. Caches results to avoid
re-querying on restart.
"""

import json
import os
import time
import pandas as pd
import requests
from pathlib import Path
from tqdm import tqdm
from utils import DATA_RAW, DATA_PROCESSED, FILMS_PARQUET, TMDB_MOVIES


# Load API key from .env file in project root
ENV_FILE = Path(__file__).parent.parent / ".env"


def load_api_key():
    """Load TMDB API key from .env file or environment."""
    # Try environment first
    key = os.environ.get("TMDB_API_KEY")
    if key:
        return key

    # Try .env file
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text().splitlines():
            if line.startswith("TMDB_API_KEY="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")

    raise ValueError(
        "TMDB API key not found. Either:\n"
        "  1. Set TMDB_API_KEY environment variable, or\n"
        f"  2. Create {ENV_FILE} with: TMDB_API_KEY=your_key_here\n"
        "  Get a free key at: https://www.themoviedb.org/settings/api"
    )


TMDB_BASE = "https://api.themoviedb.org/3"
CACHE_FILE = DATA_RAW / "tmdb_cache.json"
RATE_LIMIT_DELAY = 0.05  # 50ms between requests (well under 40 req/sec limit)


def load_cache():
    """Load cached TMDB results."""
    if CACHE_FILE.exists():
        with open(CACHE_FILE) as f:
            return json.load(f)
    return {}


def save_cache(cache):
    """Save TMDB results to cache."""
    with open(CACHE_FILE, "w") as f:
        json.dump(cache, f)


def fetch_tmdb_movie(imdb_id, api_key):
    """Fetch movie details from TMDB by IMDb ID.

    Uses /find to locate the TMDB ID, then /movie/{id} for financial data.
    """
    # Step 1: Find TMDB ID from IMDb ID
    find_url = f"{TMDB_BASE}/find/{imdb_id}"
    resp = requests.get(find_url, params={
        "api_key": api_key,
        "external_source": "imdb_id",
    })
    if resp.status_code == 429:
        # Rate limited — wait and retry
        time.sleep(2)
        resp = requests.get(find_url, params={
            "api_key": api_key,
            "external_source": "imdb_id",
        })

    if resp.status_code != 200:
        return None

    data = resp.json()
    movies = data.get("movie_results", [])
    if not movies:
        return None

    tmdb_id = movies[0]["id"]

    # Step 2: Get full movie details (includes budget/revenue)
    movie_url = f"{TMDB_BASE}/movie/{tmdb_id}"
    resp = requests.get(movie_url, params={"api_key": api_key})
    if resp.status_code != 200:
        return None

    movie = resp.json()
    return {
        "tconst": imdb_id,
        "tmdb_id": tmdb_id,
        "budget": movie.get("budget", 0),
        "revenue": movie.get("revenue", 0),
        "production_countries": [c["iso_3166_1"] for c in movie.get("production_countries", [])],
        "original_language": movie.get("original_language"),
        "popularity": movie.get("popularity"),
    }


def main():
    api_key = load_api_key()
    print(f"TMDB API key loaded ({api_key[:8]}...)")

    # Get list of IMDb IDs to query
    # Try parquet first (from step 02), fall back to raw ratings
    if FILMS_PARQUET.exists():
        films = pd.read_parquet(FILMS_PARQUET)
        imdb_ids = films["tconst"].tolist()
    else:
        # Use raw data to get top films
        from utils import load_imdb_tsv, TITLE_RATINGS, TITLE_BASICS, MIN_VOTES
        ratings = load_imdb_tsv(TITLE_RATINGS)
        basics = load_imdb_tsv(TITLE_BASICS)
        top = ratings[ratings["numVotes"] >= MIN_VOTES]
        merged = top.merge(basics, on="tconst")
        movies = merged[merged["titleType"] == "movie"]
        imdb_ids = movies["tconst"].tolist()

    print(f"Films to query: {len(imdb_ids)}")

    # Load cache
    cache = load_cache()
    cached_ids = set(cache.keys())
    remaining = [id for id in imdb_ids if id not in cached_ids]
    print(f"Already cached: {len(cached_ids)}, remaining: {len(remaining)}")

    # Fetch remaining
    for imdb_id in tqdm(remaining, desc="Fetching TMDB data"):
        result = fetch_tmdb_movie(imdb_id, api_key)
        if result:
            cache[imdb_id] = result
        else:
            cache[imdb_id] = {"tconst": imdb_id, "budget": 0, "revenue": 0}
        time.sleep(RATE_LIMIT_DELAY)

        # Save cache periodically
        if len(cache) % 100 == 0:
            save_cache(cache)

    save_cache(cache)

    # Build output CSV
    rows = [cache[id] for id in imdb_ids if id in cache]
    df = pd.DataFrame(rows)

    # Flatten production_countries to comma-separated string
    if "production_countries" in df.columns:
        df["production_countries"] = df["production_countries"].apply(
            lambda x: ",".join(x) if isinstance(x, list) else ""
        )

    df.to_csv(TMDB_MOVIES, index=False)

    # Report
    has_budget = (df["budget"] > 0).sum()
    has_revenue = (df["revenue"] > 0).sum()
    has_both = ((df["budget"] > 0) & (df["revenue"] > 0)).sum()
    print(f"\nTMDB data saved to {TMDB_MOVIES}")
    print(f"  Total films: {len(df)}")
    print(f"  With budget: {has_budget} ({has_budget/len(df)*100:.0f}%)")
    print(f"  With revenue: {has_revenue} ({has_revenue/len(df)*100:.0f}%)")
    print(f"  With both: {has_both} ({has_both/len(df)*100:.0f}%)")


if __name__ == "__main__":
    main()
