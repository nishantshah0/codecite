"""Download the National Building Code of Canada 2020 (PDF, ~24 MB).

The NBC 2020 is published free of charge by the NRC / Government of Canada.
publications.gc.ca serves the file behind an "archived content" interstitial,
so a browser-style Referer header is needed.

The PDF is free to read but not redistributable, which is why it is
downloaded here instead of committed to the repo.
"""

import sys
import urllib.request
from pathlib import Path

URL = "https://publications.gc.ca/collections/collection_2022/cnrc-nrc/NR24-28-2020-eng.pdf"
DEST = Path(__file__).resolve().parents[1] / "data" / "nbc2020.pdf"


def main() -> int:
    DEST.parent.mkdir(parents=True, exist_ok=True)
    if DEST.exists() and DEST.stat().st_size > 20_000_000:
        print(f"already downloaded: {DEST}")
        return 0
    req = urllib.request.Request(
        URL,
        headers={
            "Referer": "https://publications.gc.ca/site/archivee-archived.html",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        },
    )
    print(f"downloading {URL} ...")
    with urllib.request.urlopen(req) as resp, open(DEST, "wb") as f:
        head = resp.read(5)
        if head != b"%PDF-":
            print("got an HTML page instead of the PDF; try again or download manually")
            return 1
        f.write(head)
        while True:
            block = resp.read(1 << 20)
            if not block:
                break
            f.write(block)
    print(f"saved {DEST} ({DEST.stat().st_size / 1e6:.1f} MB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
