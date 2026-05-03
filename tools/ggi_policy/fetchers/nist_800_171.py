"""NIST 800-171 Rev 3 fetcher (OSCAL JSON catalog).

OSCAL IDs already use the dotted citation form (`3.1.1`, `3.13.11`), so
no normalization is needed.
"""

import json
from datetime import date

from ggi_policy.fetchers import _http
from ggi_policy.fetchers._models import Control, FrameworkData, Metadata
from ggi_policy.fetchers._oscal import parse_catalog


SOURCE_URL = "https://raw.githubusercontent.com/usnistgov/oscal-content/main/nist.gov/SP800-171/rev3/json/NIST_SP800-171_rev3_catalog.json"


def fetch_from_text(text: str, *, fetched_at: date) -> FrameworkData:
    payload = json.loads(text)
    _title, version, raw_controls = parse_catalog(payload)
    controls = [Control(id=c["id"], title=c.get("title", "")) for c in raw_controls]
    return FrameworkData(
        metadata=Metadata(
            version=version,
            fetched_at=fetched_at,
            source_url=SOURCE_URL,
            fetcher="nist_800_171",
        ),
        controls=controls,
    )


def fetch(*, fetched_at: date | None = None) -> FrameworkData:
    text = _http.fetch_text(SOURCE_URL)
    return fetch_from_text(text, fetched_at=fetched_at or date.today())
