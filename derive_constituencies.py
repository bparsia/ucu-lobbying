"""
Build data/constituencies.csv from raw MPs data + institutions constituency mapping.

Output columns:
  pcon_code, constituency_name, mp_id, mp_name, mp_party, mp_party_abbr,
  mp_membership_start
"""
import csv
import json
from pathlib import Path

RAW_MPS = Path(__file__).parent / "data" / "raw" / "mps.json"
OUT = Path(__file__).parent / "data" / "constituencies.csv"

FIELDS = ["pcon_code", "constituency_name", "mp_id", "mp_name",
          "mp_party", "mp_party_abbr", "mp_membership_start"]


def main():
    if not RAW_MPS.exists():
        print("ERROR: data/raw/mps.json not found — run fetch/fetch_mps.py first")
        return

    members = json.loads(RAW_MPS.read_text())
    rows = []
    for m in members:
        v = m["value"]
        hm = v["latestHouseMembership"]
        party = v.get("latestParty") or {}
        rows.append({
            "pcon_code": str(hm.get("membershipFromId", "")),
            "constituency_name": hm.get("membershipFrom", ""),
            "mp_id": str(v["id"]),
            "mp_name": v.get("nameDisplayAs", ""),
            "mp_party": party.get("name", ""),
            "mp_party_abbr": party.get("abbreviation", ""),
            "mp_membership_start": (hm.get("membershipStatus") or {}).get("statusStartDate", ""),
        })

    rows.sort(key=lambda r: r["constituency_name"])

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)

    print(f"Wrote {len(rows)} constituencies to {OUT}")


if __name__ == "__main__":
    main()
