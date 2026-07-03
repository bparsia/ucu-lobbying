"""
Refresh all data. Run this to update raw data and rebuild derived CSVs.

Usage:
    uv run python refresh.py [--skip-fetch]

--skip-fetch: rebuild derived CSVs from existing raw data without re-fetching.

Manual sources (not fetched automatically — download and place in sources/):
  sources/table-14-2.csv   HESA KFI table-14, downloaded from:
                           https://www.hesa.ac.uk/data-and-analysis/finances/table-14
                           Update annually after HESA finance release (usually May).
"""
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).parent
FETCH = [
    "fetch/fetch_institutions.py",
    "fetch/fetch_mps.py",
    "fetch/fetch_postcodes.py",
    "fetch/fetch_kfi.py",
    "fetch/fetch_hepi.py",
    "fetch/fetch_constituency_centroids.py",
]
DERIVE = [
    "derive_institutions.py",
    "derive_constituencies.py",
    "derive_financials.py",
    "derive_hepi.py",
]

skip_fetch = "--skip-fetch" in sys.argv


def run(script: str):
    print(f"\n--- {script} ---", flush=True)
    result = subprocess.run([sys.executable, HERE / script], check=False)
    if result.returncode != 0:
        print(f"WARNING: {script} exited with code {result.returncode}")


if not skip_fetch:
    for s in FETCH:
        run(s)

for s in DERIVE:
    run(s)

print("\nDone.")
