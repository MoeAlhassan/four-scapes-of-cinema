"""Filter top films by vote count and join all data sources.

Produces three parquet files:
  - films.parquet:       One row per film with ratings, financials, genres
  - people.parquet:      One row per person with name, birth year, professions
  - film_people.parquet: One row per film-person edge with role category
"""

import pandas as pd
from utils import (
    load_imdb_tsv, TITLE_BASICS, TITLE_RATINGS, TITLE_PRINCIPALS,
    TITLE_CREW, NAME_BASICS, TMDB_MOVIES,
    FILMS_PARQUET, PEOPLE_PARQUET, FILM_PEOPLE_PARQUET,
    MIN_VOTES, DATA_PROCESSED,
)


def main():
    print("Loading IMDb datasets...")
    ratings = load_imdb_tsv(TITLE_RATINGS)
    basics = load_imdb_tsv(TITLE_BASICS)
    principals = load_imdb_tsv(TITLE_PRINCIPALS)
    crew = load_imdb_tsv(TITLE_CREW)
    names = load_imdb_tsv(NAME_BASICS)

    # Step 1: Filter to top films by vote count
    top_ratings = ratings[ratings["numVotes"] >= MIN_VOTES].copy()
    print(f"Films with {MIN_VOTES:,}+ votes: {len(top_ratings)}")

    # Step 2: Keep only movies
    films = top_ratings.merge(basics, on="tconst", how="inner")
    films = films[films["titleType"] == "movie"].copy()
    print(f"Movies in scope: {len(films)}")

    # Step 3: Add director/writer IDs from crew table
    films = films.merge(crew, on="tconst", how="left")

    # Step 4: Get cast/crew edges from principals
    film_people = principals[principals["tconst"].isin(films["tconst"])].copy()
    print(f"Film-person edges: {len(film_people)}")

    # Step 5: Get unique people
    unique_nconsts = film_people["nconst"].unique()
    people = names[names["nconst"].isin(unique_nconsts)].copy()
    print(f"Unique people: {len(people)}")

    # Step 6: Join TMDB financials (if available)
    if TMDB_MOVIES.exists():
        tmdb = pd.read_csv(TMDB_MOVIES)
        # Ensure tconst column exists
        if "tconst" in tmdb.columns:
            tmdb_slim = tmdb[["tconst", "budget", "revenue"]].copy()
            tmdb_slim = tmdb_slim.rename(columns={
                "budget": "budget",
                "revenue": "revenue",
            })
            # Keep only rows with actual financial data
            tmdb_with_data = tmdb_slim[
                (tmdb_slim["budget"] > 0) & (tmdb_slim["revenue"] > 0)
            ].copy()
            tmdb_with_data["roi"] = (
                (tmdb_with_data["revenue"] - tmdb_with_data["budget"])
                / tmdb_with_data["budget"]
            )
            films = films.merge(tmdb_with_data, on="tconst", how="left")
            n_financial = films["budget"].notna().sum()
            print(f"Films with financial data: {n_financial} ({n_financial/len(films)*100:.0f}%)")
        else:
            print("WARNING: TMDB file missing 'tconst' column")
            films["budget"] = None
            films["revenue"] = None
            films["roi"] = None
    else:
        print("TMDB file not found — skipping financial data. Run 01b_download_tmdb.py first.")
        films["budget"] = None
        films["revenue"] = None
        films["roi"] = None

    # Step 7: Explode genres into list column
    films["genre_list"] = films["genres"].str.split(",")

    # Step 8: Save
    DATA_PROCESSED.mkdir(parents=True, exist_ok=True)
    films.to_parquet(FILMS_PARQUET, index=False)
    people.to_parquet(PEOPLE_PARQUET, index=False)
    film_people.to_parquet(FILM_PEOPLE_PARQUET, index=False)

    print(f"\nSaved:")
    print(f"  {FILMS_PARQUET} ({len(films)} films)")
    print(f"  {PEOPLE_PARQUET} ({len(people)} people)")
    print(f"  {FILM_PEOPLE_PARQUET} ({len(film_people)} edges)")

    # Summary stats
    years = films["startYear"].dropna()
    print(f"\nYear range: {years.astype(int).min()} - {years.astype(int).max()}")
    print(f"Rating range: {films['averageRating'].min():.1f} - {films['averageRating'].max():.1f}")
    print(f"Vote range: {films['numVotes'].min():,} - {films['numVotes'].max():,}")
    print(f"\nTop genres:")
    genre_counts = films["genre_list"].explode().value_counts().head(10)
    for genre, count in genre_counts.items():
        print(f"  {genre}: {count}")

    # Role breakdown
    print(f"\nRole breakdown in principals:")
    role_counts = film_people["category"].value_counts()
    for role, count in role_counts.items():
        print(f"  {role}: {count:,}")


if __name__ == "__main__":
    main()
