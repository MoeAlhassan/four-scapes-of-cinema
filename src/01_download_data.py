"""Download and decompress IMDb datasets needed for the analysis."""

import gzip
import shutil
import urllib.request
from pathlib import Path

from utils import DATA_RAW

IMDB_BASE = "https://datasets.imdbws.com"
FILES = [
    "title.principals.tsv.gz",
    "title.crew.tsv.gz",
    "name.basics.tsv.gz",
]


def download_file(url, dest):
    """Download a file, skipping if it already exists."""
    if dest.exists():
        print(f"  Skipping {dest.name} (already exists)")
        return
    print(f"  Downloading {url}...")
    urllib.request.urlretrieve(url, dest)
    print(f"  Done ({dest.stat().st_size / 1e6:.1f} MB)")


def decompress_gz(gz_path):
    """Decompress .gz to .tsv, remove .gz after."""
    tsv_path = gz_path.with_suffix("")  # strip .gz
    if tsv_path.exists():
        print(f"  Skipping decompress {tsv_path.name} (already exists)")
        return
    print(f"  Decompressing {gz_path.name}...")
    with gzip.open(gz_path, "rb") as f_in, open(tsv_path, "wb") as f_out:
        shutil.copyfileobj(f_in, f_out)
    gz_path.unlink()
    print(f"  Done ({tsv_path.stat().st_size / 1e6:.1f} MB)")


def main():
    for fname in FILES:
        print(f"\n--- {fname} ---")
        gz_path = DATA_RAW / fname
        download_file(f"{IMDB_BASE}/{fname}", gz_path)
        decompress_gz(gz_path)
    print("\nDone. All IMDb datasets ready.")


if __name__ == "__main__":
    main()
