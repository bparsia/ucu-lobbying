"""
Fetch HEPI constituency-level international student economic impact data.

Writes: data/raw/hepi_constituency.xlsx
"""
import urllib.request
from pathlib import Path

URL = "https://www.hepi.ac.uk/wp-content/uploads/2024/06/Constituency-data.xlsx"
OUT = Path(__file__).parent.parent / "data" / "raw" / "hepi_constituency.xlsx"


def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    print(f"Fetching {URL} ...")
    urllib.request.urlretrieve(URL, OUT)
    print(f"Saved {OUT} ({OUT.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
