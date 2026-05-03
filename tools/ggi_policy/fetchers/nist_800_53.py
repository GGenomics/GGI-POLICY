"""NIST 800-53 Rev 5 fetcher (OSCAL JSON catalog).

OSCAL stores control IDs in lowercase with a dot separator for enhancements
(e.g., `ac-2.1`). The citation form used in policy frontmatter is uppercase
with parenthesized enhancement (e.g., `AC-2(1)`). This fetcher converts.
"""

import json
import re
from datetime import date

from ggi_policy.fetchers import _http
from ggi_policy.fetchers._models import Control, FrameworkData, Metadata
from ggi_policy.fetchers._oscal import parse_catalog


SOURCE_URL = "https://raw.githubusercontent.com/usnistgov/oscal-content/main/nist.gov/SP800-53/rev5/json/NIST_SP-800-53_rev5_catalog.json"

_BASE_RE = re.compile(r"^([a-z]{2})-(\d+)$")
_ENH_RE  = re.compile(r"^([a-z]{2})-(\d+)\.(\d+)$")


def _normalize_id(oscal_id: str) -> str:
    m = _ENH_RE.match(oscal_id)
    if m:
        return f"{m.group(1).upper()}-{m.group(2)}({m.group(3)})"
    m = _BASE_RE.match(oscal_id)
    if m:
        return f"{m.group(1).upper()}-{m.group(2)}"
    return oscal_id  # Pass through anything we don't recognize.


def fetch_from_text(text: str, *, fetched_at: date) -> FrameworkData:
    payload = json.loads(text)
    _title, version, raw_controls = parse_catalog(payload)
    controls = [
        Control(id=_normalize_id(c["id"]), title=c.get("title", ""))
        for c in raw_controls
    ]
    return FrameworkData(
        metadata=Metadata(
            version=version,
            fetched_at=fetched_at,
            source_url=SOURCE_URL,
            fetcher="nist_800_53",
        ),
        controls=controls,
    )


def fetch(*, fetched_at: date | None = None) -> FrameworkData:
    text = _http.fetch_text(SOURCE_URL)
    return fetch_from_text(text, fetched_at=fetched_at or date.today())
