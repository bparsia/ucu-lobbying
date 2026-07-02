"""
Fetch current House of Commons members from the Parliament Members API.

Writes: data/raw/mps.json
"""
import json
import time
import urllib.request
from pathlib import Path

API = "https://members-api.parliament.uk/api/Members/Search"
OUT = Path(__file__).parent.parent / "data" / "raw" / "mps.json"
PAGE = 20  # API caps responses at 20 regardless of take parameter


def fetch_all() -> list[dict]:
    members = []
    skip = 0
    while True:
        url = f"{API}?House=Commons&IsCurrentMember=true&skip={skip}&take={PAGE}"
        with urllib.request.urlopen(url) as r:
            data = json.load(r)
        batch = data["items"]
        if not batch:
            break
        members.extend(batch)
        print(f"  fetched {len(members)} / {data['totalResults']}")
        if len(members) >= data["totalResults"]:
            break
        skip += len(batch)
        time.sleep(0.2)
    return members


def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    print("Fetching MPs from Parliament API ...")
    members = fetch_all()
    OUT.write_text(json.dumps(members, indent=2))
    print(f"Saved {OUT} ({len(members)} members)")


if __name__ == "__main__":
    main()
