"""
Resolve institution postcodes to 2024 parliamentary constituencies via postcodes.io.

Reads:  data/raw/learning_providers.csv
Writes: data/raw/postcode_lookup.json

postcodes.io bulk endpoint accepts up to 100 postcodes per request.
Caches results so re-runs only fetch missing postcodes.
"""
import json
import time
import urllib.request
import urllib.parse
import csv
from pathlib import Path

PROVIDERS_CSV = Path(__file__).parent.parent / "data" / "raw" / "learning_providers.csv"
OUT = Path(__file__).parent.parent / "data" / "raw" / "postcode_lookup.json"
BULK_URL = "https://api.postcodes.io/postcodes"
CHUNK = 100


def load_postcodes() -> list[str]:
    with open(PROVIDERS_CSV, newline="", encoding="utf-8") as f:
        return [row["POSTCODE"].replace(" ", "").upper()
                for row in csv.DictReader(f)
                if row.get("POSTCODE", "").strip()]


def bulk_lookup(postcodes: list[str]) -> dict[str, dict]:
    """Return {postcode: result_dict} for a batch (max 100)."""
    body = json.dumps({"postcodes": postcodes}).encode()
    req = urllib.request.Request(
        BULK_URL,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req) as r:
        data = json.load(r)
    out = {}
    for item in data["result"]:
        pc = item["query"].replace(" ", "").upper()
        out[pc] = item["result"]  # may be None if invalid
    return out


def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)

    # Load any existing cache
    cache: dict[str, dict] = {}
    if OUT.exists():
        cache = json.loads(OUT.read_text())
        print(f"Loaded {len(cache)} cached postcode lookups")

    postcodes = load_postcodes()
    missing = [p for p in postcodes if p not in cache]
    print(f"{len(postcodes)} postcodes total, {len(missing)} to fetch")

    for i in range(0, len(missing), CHUNK):
        chunk = missing[i:i + CHUNK]
        print(f"  fetching {i}–{i + len(chunk)} ...")
        results = bulk_lookup(chunk)
        cache.update(results)
        time.sleep(0.2)

    OUT.write_text(json.dumps(cache, indent=2))
    print(f"Saved {OUT} ({len(cache)} entries)")


if __name__ == "__main__":
    main()
