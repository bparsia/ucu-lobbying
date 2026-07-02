"""
Build data/institutions.csv from raw learning providers data.

Output columns:
  ukprn, name, postcode, town, website, constituency_2024, constituency_pcon_code
"""
import csv
import json
from pathlib import Path

RAW_PROVIDERS = Path(__file__).parent / "data" / "raw" / "learning_providers.csv"
RAW_POSTCODES = Path(__file__).parent / "data" / "raw" / "postcode_lookup.json"
OUT = Path(__file__).parent / "data" / "institutions.csv"

FIELDS = ["ukprn", "name", "postcode", "town", "website",
          "latitude", "longitude", "constituency_2024", "constituency_pcon_code"]


def main():
    postcode_lookup: dict[str, dict] = {}
    if RAW_POSTCODES.exists():
        postcode_lookup = json.loads(RAW_POSTCODES.read_text())
    else:
        print("WARNING: postcode_lookup.json not found — run fetch/fetch_postcodes.py first")

    rows = []
    with open(RAW_PROVIDERS, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            pc_raw = r.get("POSTCODE", "").strip()
            pc_key = pc_raw.replace(" ", "").upper()
            pc_data = postcode_lookup.get(pc_key) or {}

            rows.append({
                "ukprn": r["UKPRN"].strip(),
                "name": r["PROVIDER_NAME"].strip().title(),
                "postcode": pc_raw,
                "town": r.get("TOWN", "").strip().title(),
                "website": r.get("WEBSITE_ADDRESS", "").strip(),
                "latitude":  pc_data.get("latitude", ""),
                "longitude": pc_data.get("longitude", ""),
                "constituency_2024": (pc_data.get("parliamentary_constituency_2024") or ""),
                "constituency_pcon_code": (
                    (pc_data.get("codes") or {}).get("parliamentary_constituency_2024") or ""
                ),
            })

    rows.sort(key=lambda r: r["name"])

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)

    n_with_constituency = sum(1 for r in rows if r["constituency_2024"])
    print(f"Wrote {len(rows)} institutions to {OUT}")
    print(f"  {n_with_constituency} have constituency data, "
          f"{len(rows) - n_with_constituency} missing")


if __name__ == "__main__":
    main()
