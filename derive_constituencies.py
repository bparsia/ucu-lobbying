"""
Build data/constituencies.csv from raw MPs data + ONS constituency centroids.

Output columns:
  pcon_code, constituency_name, mp_id, mp_name, mp_party, mp_party_abbr,
  mp_membership_start, latitude, longitude
"""
import csv
import json
from pathlib import Path

RAW_MPS       = Path(__file__).parent / "data" / "raw" / "mps.json"
RAW_CENTROIDS = Path(__file__).parent / "data" / "raw" / "constituency_centroids.json"
OUT           = Path(__file__).parent / "data" / "constituencies.csv"

FIELDS = ["pcon_code", "constituency_name", "mp_id", "mp_name",
          "mp_party", "mp_party_abbr", "mp_membership_start",
          "latitude", "longitude"]


def main():
    if not RAW_MPS.exists():
        print("ERROR: data/raw/mps.json not found — run fetch/fetch_mps.py first")
        return

    # Build centroid lookup by PCON code and by name
    centroids_by_code = {}
    centroids_by_name = {}
    if RAW_CENTROIDS.exists():
        for c in json.loads(RAW_CENTROIDS.read_text()):
            centroids_by_code[c["PCON24CD"]] = c
            centroids_by_name[c["PCON24NM"].lower()] = c
    else:
        print("WARNING: constituency_centroids.json not found — run fetch/fetch_constituency_centroids.py")

    members = json.loads(RAW_MPS.read_text())
    rows = []
    for m in members:
        v  = m["value"]
        hm = v["latestHouseMembership"]
        party = v.get("latestParty") or {}
        con_name = hm.get("membershipFrom", "")

        # Match centroid by name (Parliament API doesn't return PCON24CD directly)
        c = centroids_by_name.get(con_name.lower(), {})
        rows.append({
            "pcon_code":           str(hm.get("membershipFromId", "")),
            "constituency_name":   con_name,
            "mp_id":               str(v["id"]),
            "mp_name":             v.get("nameDisplayAs", ""),
            "mp_party":            party.get("name", ""),
            "mp_party_abbr":       party.get("abbreviation", ""),
            "mp_membership_start": (hm.get("membershipStatus") or {}).get("statusStartDate", ""),
            "latitude":            c.get("LAT", ""),
            "longitude":           c.get("LONG", ""),
        })

    rows.sort(key=lambda r: r["constituency_name"])

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)

    n_with_latlon = sum(1 for r in rows if r["latitude"])
    print(f"Wrote {len(rows)} constituencies to {OUT}")
    print(f"  {n_with_latlon} with centroid, {len(rows) - n_with_latlon} missing")


if __name__ == "__main__":
    main()
