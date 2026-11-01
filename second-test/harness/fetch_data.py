"""Download the authors' replication package (Harvard Dataverse, doi:10.7910/DVN/X2HQXD) into source/dataverse.

The files are public but not kept in git (solutions2.tab alone is 42 MB). The checks in test_core.py and the
findings PDF use them. Usage (from second-test/):
    python3 harness/fetch_data.py
"""

import json
import urllib.request
from pathlib import Path

DOI = "doi:10.7910/DVN/X2HQXD"
API = "https://dataverse.harvard.edu/api"
OUT = Path(__file__).resolve().parent.parent / "source" / "dataverse"
HEADERS = {"User-Agent": "org-science-replication/1.0"}  # Dataverse refuses Python's default user agent


def get(url):
    return urllib.request.urlopen(urllib.request.Request(url, headers=HEADERS), timeout=300)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    with get(f"{API}/datasets/:persistentId/versions/:latest/files?persistentId={DOI}") as r:
        files = json.load(r)["data"]
    for f in files:
        d = f["dataFile"]
        target = OUT / d["filename"]
        if target.exists() and target.stat().st_size == d.get("originalFileSize", d.get("filesize")):
            print(f"present  {d['filename']}")
            continue
        with get(f"{API}/access/datafile/{d['id']}?format=original") as r:
            target.write_bytes(r.read())
        print(f"fetched  {d['filename']} ({target.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
