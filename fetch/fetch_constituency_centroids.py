"""
Fetch 2024 Westminster constituency centroids from ONS ArcGIS API.

Writes: data/raw/constituency_centroids.json
"""
import json
import time
import urllib.request
import urllib.parse
from pathlib import Path

OUT = Path(__file__).parent.parent / "data" / "raw" / "constituency_centroids.json"

BASE = (
    "https://services1.arcgis.com/ESMARspQHYMw9BZ9/arcgis/rest/services"
    "/Westminster_Parliamentary_Constituencies_July_2024_Boundaries_UK_BUC"
    "/FeatureServer/0/query"
)
PAGE = 200


def fetch_all() -> list[dict]:
    results = []
    offset = 0
    while True:
        params = urllib.parse.urlencode({
            "where": "1=1",
            "outFields": "PCON24CD,PCON24NM,LONG,LAT",
            "returnGeometry": "false",
            "resultOffset": offset,
            "resultRecordCount": PAGE,
            "f": "json",
        })
        with urllib.request.urlopen(f"{BASE}?{params}") as r:
            data = json.load(r)
        batch = [f["attributes"] for f in data.get("features", [])]
        if not batch:
            break
        results.extend(batch)
        print(f"  fetched {len(results)} constituencies")
        if not data.get("exceededTransferLimit"):
            break
        offset += PAGE
        time.sleep(0.2)
    return results


def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    print("Fetching constituency centroids from ONS ArcGIS ...")
    centroids = fetch_all()
    OUT.write_text(json.dumps(centroids, indent=2))
    print(f"Saved {OUT} ({len(centroids)} constituencies)")


if __name__ == "__main__":
    main()
