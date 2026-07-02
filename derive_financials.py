"""
Build data/financials.csv from two sources:

  Primary:   sources/table-14-2.csv  (HESA KFI table, long format, 2015/16-2024/25)
  Supplement: data/raw/kfi.csv       (ukhe-finances GitHub, wide format, 2016/17-2022/23)
                                      provides salary and VC pay columns not in HESA table-14

Output columns:
  ukprn, provider_name, academic_year, country, region,
  surplus_vs_income, staff_vs_income, unrestricted_vs_income,
  net_liquidity_days, external_borrowing_vs_income, current_ratio, debt_service_ratio,
  avg_salary, academic_salary, vc_avg_salary, vc_avg_remunerate,
  data_source
"""
import csv
from pathlib import Path

HESA_CSV  = Path(__file__).parent / "sources" / "table-14-2.csv"
GITHUB_CSV = Path(__file__).parent / "data" / "raw" / "kfi.csv"
OUT       = Path(__file__).parent / "data" / "financials.csv"

OUT_COLS = [
    "ukprn", "provider_name", "academic_year", "country", "region",
    "surplus_vs_income", "staff_vs_income", "unrestricted_vs_income",
    "net_liquidity_days", "external_borrowing_vs_income", "current_ratio", "debt_service_ratio",
    "avg_salary", "academic_salary", "vc_avg_salary", "vc_avg_remunerate",
    "data_source",
]

# Map HESA long-format metric names → output column names
HESA_METRIC_MAP = {
    "Surplus/(deficit) as a % of total income":         "surplus_vs_income",
    "Staff costs as a % of total income":               "staff_vs_income",
    "Unrestricted reserves as a % of total income":     "unrestricted_vs_income",
    "Net liquidity days":                               "net_liquidity_days",
    "External borrowing as a % of total income":        "external_borrowing_vs_income",
    "Ratio of current assets to current liabilities":   "current_ratio",
    "Debt service ratio":                               "debt_service_ratio",
}

# Map GitHub wide-format column names → output column names (salary only)
GITHUB_SALARY_MAP = {
    "avg_salary":       "avg_salary",
    "academic_salary":  "academic_salary",
    "vc_avg_salary":    "vc_avg_salary",
    "vc_avg_remunerate": "vc_avg_remunerate",
}


def clean_ukprn(v: str) -> str:
    try:
        return str(int(float(v)))
    except (ValueError, TypeError):
        return v.strip()


def clean_val(v: str) -> str:
    """Normalise empty/missing values; strip parentheses used for negatives."""
    v = v.strip()
    if v in ("", "nan", "None", "N/A", "-"):
        return ""
    # HESA uses (2.0) for negative numbers
    if v.startswith("(") and v.endswith(")"):
        v = "-" + v[1:-1]
    return v


def load_hesa() -> dict[tuple, dict]:
    """Load HESA table-14 long format → {(ukprn, year): {col: value}}."""
    if not HESA_CSV.exists():
        print(f"ERROR: {HESA_CSV} not found")
        return {}

    records: dict[tuple, dict] = {}
    with open(HESA_CSV, newline="", encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        for _ in range(10):
            next(reader)  # skip metadata rows
        for row in csv.DictReader(f):
            ukprn = row["UKPRN"].strip()
            year  = row["Academic Year"].strip()
            if not ukprn or not year:
                continue
            key = (ukprn, year)
            if key not in records:
                records[key] = {
                    "ukprn":         ukprn,
                    "provider_name": row["HE provider"].strip(),
                    "academic_year": year,
                    "country":       row["Country of HE provider"].strip(),
                    "region":        row["Region of HE provider"].strip(),
                    "surplus_vs_income": "", "staff_vs_income": "",
                    "unrestricted_vs_income": "", "net_liquidity_days": "",
                    "external_borrowing_vs_income": "", "current_ratio": "",
                    "debt_service_ratio": "",
                    "avg_salary": "", "academic_salary": "",
                    "vc_avg_salary": "", "vc_avg_remunerate": "",
                    "data_source": "HESA table-14",
                }
            metric = row["KFI ratio title"].strip()
            if metric in HESA_METRIC_MAP:
                records[key][HESA_METRIC_MAP[metric]] = clean_val(row["Value (Ratio)"])
    return records


def load_github_salary() -> dict[tuple, dict]:
    """Load salary columns from GitHub KFI CSV → {(ukprn, year): {salary_col: value}}."""
    if not GITHUB_CSV.exists():
        print("WARNING: data/raw/kfi.csv not found — salary data will be missing for 2016/17-2022/23")
        return {}

    out = {}
    with open(GITHUB_CSV, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            ukprn = clean_ukprn(row["ukprn"])
            year  = row["academic year"].strip()
            key   = (ukprn, year)
            out[key] = {dst: clean_val(row.get(src, "")) for src, dst in GITHUB_SALARY_MAP.items()}
    return out


def main():
    hesa    = load_hesa()
    salaries = load_github_salary()

    if not hesa:
        return

    # Merge salary data into HESA records
    for key, sal in salaries.items():
        if key in hesa:
            for col, val in sal.items():
                if val:
                    hesa[key][col] = val

    rows_out = sorted(hesa.values(), key=lambda r: (r["ukprn"], r["academic_year"]))

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=OUT_COLS)
        w.writeheader()
        w.writerows(rows_out)

    providers = len(set(r["ukprn"] for r in rows_out))
    years = sorted(set(r["academic_year"] for r in rows_out))
    salary_rows = sum(1 for r in rows_out if r["avg_salary"])
    print(f"Wrote {len(rows_out)} rows to {OUT}")
    print(f"  {providers} providers, {years[0]}–{years[-1]}")
    print(f"  {salary_rows} rows with salary data")


if __name__ == "__main__":
    main()
