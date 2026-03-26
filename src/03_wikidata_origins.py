"""Query Wikidata SPARQL for geographic origins of film professionals.

For each person (identified by IMDb nconst), queries Wikidata for:
  1. Country of citizenship (P27) — preferred
  2. Place of birth (P19) mapped to country (P17) — fallback

Caches results to avoid re-querying. Rate-limits to respect Wikidata API.
"""

import time
import pandas as pd
from SPARQLWrapper import SPARQLWrapper, JSON
from tqdm import tqdm
from utils import PEOPLE_PARQUET, WIKIDATA_PARQUET, DATA_PROCESSED


WIKIDATA_ENDPOINT = "https://query.wikidata.org/sparql"
BATCH_SIZE = 50  # IMDb IDs per SPARQL query
SLEEP_BETWEEN = 2.0  # seconds between queries (Wikidata asks for politeness)


def build_sparql_query(imdb_ids):
    """Build SPARQL query for a batch of IMDb IDs.

    Returns country of citizenship and birth country for each person.
    """
    values = " ".join(f'"{id}"' for id in imdb_ids)
    return f"""
    SELECT ?imdbId ?countryLabel ?birthCountryLabel WHERE {{
      ?person wdt:P345 ?imdbId .
      VALUES ?imdbId {{ {values} }}
      OPTIONAL {{
        ?person wdt:P27 ?country .
        ?country rdfs:label ?countryLabel .
        FILTER(LANG(?countryLabel) = "en")
      }}
      OPTIONAL {{
        ?person wdt:P19 ?birthPlace .
        ?birthPlace wdt:P17 ?birthCountry .
        ?birthCountry rdfs:label ?birthCountryLabel .
        FILTER(LANG(?birthCountryLabel) = "en")
      }}
    }}
    """


def query_batch(sparql, imdb_ids, max_retries=3):
    """Execute a single SPARQL query for a batch of IDs, with retry."""
    query = build_sparql_query(imdb_ids)
    sparql.setQuery(query)
    sparql.setReturnFormat(JSON)

    for attempt in range(max_retries):
        try:
            results = sparql.query().convert()
            rows = []
            for r in results["results"]["bindings"]:
                row = {"nconst": r["imdbId"]["value"]}
                if "countryLabel" in r:
                    row["country_citizenship"] = r["countryLabel"]["value"]
                if "birthCountryLabel" in r:
                    row["country_birth"] = r["birthCountryLabel"]["value"]
                rows.append(row)
            return rows
        except Exception as e:
            if attempt < max_retries - 1:
                wait = (attempt + 1) * 10  # backoff: 10s, 20s, 30s
                print(f"  Query failed ({e}), retrying in {wait}s...")
                time.sleep(wait)
            else:
                print(f"  Query failed after {max_retries} attempts: {e}")
                return []


def main():
    people = pd.read_parquet(PEOPLE_PARQUET)
    all_nconsts = people["nconst"].unique().tolist()
    print(f"Total people to query: {len(all_nconsts)}")

    # Check for existing cache
    if WIKIDATA_PARQUET.exists():
        cached = pd.read_parquet(WIKIDATA_PARQUET)
        already_queried = set(cached["nconst"].unique())
        remaining = [n for n in all_nconsts if n not in already_queried]
        print(f"  Already cached: {len(already_queried)}, remaining: {len(remaining)}")
    else:
        cached = pd.DataFrame()
        remaining = all_nconsts

    if not remaining:
        print("All people already queried. Done.")
        return

    sparql = SPARQLWrapper(WIKIDATA_ENDPOINT)
    sparql.addCustomHttpHeader(
        "User-Agent",
        "FilmNetworkAnalysis/1.0 (INFO230 academic research; Python SPARQLWrapper)"
    )

    all_rows = []
    batches = [remaining[i:i + BATCH_SIZE] for i in range(0, len(remaining), BATCH_SIZE)]

    for batch in tqdm(batches, desc="Wikidata batches"):
        rows = query_batch(sparql, batch)
        all_rows.extend(rows)

        # Save intermediate results every 50 batches
        if len(all_rows) % (BATCH_SIZE * 50) == 0 and all_rows:
            _save_intermediate(cached, all_rows, all_nconsts)

        time.sleep(SLEEP_BETWEEN)

    _save_final(cached, all_rows, all_nconsts)


def _save_intermediate(cached, new_rows, all_nconsts):
    """Save intermediate results in case of interruption."""
    new_data = pd.DataFrame(new_rows)
    if not cached.empty:
        combined = pd.concat([cached, new_data], ignore_index=True)
    else:
        combined = new_data
    combined = combined.drop_duplicates(subset=["nconst"], keep="first")
    combined.to_parquet(WIKIDATA_PARQUET, index=False)
    found = combined["country_citizenship"].notna().sum() + combined["country_birth"].notna().sum()
    print(f"  [checkpoint] {len(combined)} records saved, ~{found} with some country data")


def _save_final(cached, new_rows, all_nconsts):
    """Save final results with country resolution."""
    new_data = pd.DataFrame(new_rows)

    if not cached.empty:
        combined = pd.concat([cached, new_data], ignore_index=True)
    else:
        combined = new_data

    # Resolve: prefer country_citizenship, fall back to country_birth
    if "country_citizenship" not in combined.columns:
        combined["country_citizenship"] = None
    if "country_birth" not in combined.columns:
        combined["country_birth"] = None

    combined["country"] = combined["country_citizenship"].fillna(combined["country_birth"])

    # Deduplicate (some people have multiple citizenships — take first)
    combined = combined.drop_duplicates(subset=["nconst"], keep="first")

    combined.to_parquet(WIKIDATA_PARQUET, index=False)

    # Report coverage
    total = len(all_nconsts)
    in_wikidata = len(combined)
    with_country = combined["country"].notna().sum()
    print(f"\nWikidata results:")
    print(f"  People queried: {total}")
    print(f"  Found in Wikidata: {in_wikidata} ({in_wikidata/total*100:.1f}%)")
    print(f"  With country data: {with_country} ({with_country/total*100:.1f}%)")
    print(f"\nTop 15 countries:")
    print(combined["country"].value_counts().head(15).to_string())


if __name__ == "__main__":
    main()
