"""
Fetch institution list from learning-provider.data.ac.uk.

Writes: data/raw/learning_providers.csv
"""
import urllib.request
from pathlib import Path

URL = "https://learning-provider.data.ac.uk/data/learning-providers.csv"
OUT = Path(__file__).parent.parent / "data" / "raw" / "learning_providers.csv"

def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    print(f"Fetching {URL} ...")
    urllib.request.urlretrieve(URL, OUT)
    print(f"Saved {OUT} ({OUT.stat().st_size:,} bytes)")

if __name__ == "__main__":
    main()
