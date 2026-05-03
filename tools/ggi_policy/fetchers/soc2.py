"""SOC 2 Trust Services Criteria fetcher.

The AICPA TSC publication is proprietary and has no machine-readable
distribution. The control list is maintained as a committed snapshot.
"""

import json
from datetime import date
from pathlib import Path

from ggi_policy.fetchers._models import Control, FrameworkData, Metadata


SNAPSHOT_PATH = Path(__file__).parent / "data" / "soc2-tsc-2017.json"
SOURCE_URL = "https://www.aicpa-cima.com/topic/audit-assurance/audit-and-assurance-greater-than-soc-2"


def fetch(*, fetched_at: date | None = None) -> FrameworkData:
    payload = json.loads(SNAPSHOT_PATH.read_text())
    controls = [Control(id=c["id"], title=c["title"]) for c in payload.get("controls", [])]
    return FrameworkData(
        metadata=Metadata(
            version=payload.get("version", "unknown"),
            fetched_at=fetched_at or date.today(),
            source_url=SOURCE_URL,
            fetcher="soc2",
            notes="Maintained manually from the AICPA TSC publication; no machine source.",
        ),
        controls=controls,
    )
