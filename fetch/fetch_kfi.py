"""
Fetch KFI financial data from ukhe-finances GitHub repo.

Writes: data/raw/kfi.csv
"""
import urllib.request
from pathlib import Path

URL = "https://raw.githubusercontent.com/mtwest2718/ukhe-finances/trunk/kfi.csv"
OUT = Path(__file__).parent.parent / "data" / "raw" / "kfi.csv"


def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    print(f"Fetching {URL} ...")
    urllib.request.urlretrieve(URL, OUT)
    print(f"Saved {OUT} ({OUT.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
