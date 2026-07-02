"""
Build data/hepi_constituency.csv from raw HEPI Excel.

Data uses pre-2024 constituency boundaries — noted in output as a caveat column.

Output columns:
  constituency_name, region, intl_students_firstyear, gross_benefit,
  costs, net_benefit, net_benefit_per_resident, region_impact, boundary_note
"""
import csv
import openpyxl
from pathlib import Path

RAW = Path(__file__).parent / "data" / "raw" / "hepi_constituency.xlsx"
OUT = Path(__file__).parent / "data" / "hepi_constituency.csv"

FIELDS = [
    "constituency_name", "region", "intl_students_firstyear",
    "gross_benefit", "costs", "net_benefit", "net_benefit_per_resident",
    "region_impact", "boundary_note",
]


def main():
    if not RAW.exists():
        print("ERROR: data/raw/hepi_constituency.xlsx not found — run fetch/fetch_hepi.py first")
        return

    wb = openpyxl.load_workbook(RAW, data_only=True)
    ws = wb["Results"]

    rows_out = []
    # Row 3 is header, data starts row 4
    for row in ws.iter_rows(min_row=4, values_only=True):
        _, name, region, students, gross, costs, net, net_per_res, region_impact = row[:9]
        if not name:
            continue
        rows_out.append({
            "constituency_name":      str(name).strip(),
            "region":                 str(region).strip() if region else "",
            "intl_students_firstyear": int(students) if students else "",
            "gross_benefit":          round(float(gross), 2) if gross else "",
            "costs":                  round(float(costs), 2) if costs else "",
            "net_benefit":            round(float(net), 2) if net else "",
            "net_benefit_per_resident": int(net_per_res) if net_per_res else "",
            "region_impact":          round(float(region_impact), 2) if region_impact else "",
            "boundary_note":          "pre-2024 boundaries",
        })

    rows_out.sort(key=lambda r: r["constituency_name"])

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows_out)

    print(f"Wrote {len(rows_out)} constituencies to {OUT}")


if __name__ == "__main__":
    main()
