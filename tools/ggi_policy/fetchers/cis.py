"""CIS Controls v8 fetcher.

CIS Workbench requires registration to download the official catalog, so
the canonical control list is maintained as a committed snapshot under
data/cis-v8.json. To refresh, export the latest list from CIS Workbench,
transform it to this file's shape, and commit the change.
"""

import json
from datetime import date
from pathlib import Path

from ggi_policy.fetchers._models import Control, FrameworkData, Metadata


SNAPSHOT_PATH = Path(__file__).parent / "data" / "cis-v8.json"
SOURCE_URL = "https://www.cisecurity.org/controls/v8/"


def fetch(*, fetched_at: date | None = None) -> FrameworkData:
    payload = json.loads(SNAPSHOT_PATH.read_text())
    controls = [Control(id=c["id"], title=c["title"]) for c in payload.get("controls", [])]
    return FrameworkData(
        metadata=Metadata(
            version=payload.get("version", "unknown"),
            fetched_at=fetched_at or date.today(),
            source_url=SOURCE_URL,
            fetcher="cis",
            notes="Maintained as a committed snapshot; refresh via CIS Workbench export.",
        ),
        controls=controls,
    )
