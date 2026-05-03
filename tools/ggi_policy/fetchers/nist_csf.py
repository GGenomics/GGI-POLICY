"""NIST Cybersecurity Framework 2.0 fetcher (OSCAL JSON catalog)."""

import json
from datetime import date

from ggi_policy.fetchers import _http
from ggi_policy.fetchers._models import Control, FrameworkData, Metadata
from ggi_policy.fetchers._oscal import parse_catalog


SOURCE_URL = "https://raw.githubusercontent.com/usnistgov/oscal-content/main/nist.gov/CSF/v2.0/json/NIST_CSF_v2.0_catalog.json"


def _csf_title(control: dict) -> str:
    """Subcategories in NIST OSCAL CSF carry the prose statement under
    parts[].prose; the `title` field is just the ID. Prefer prose when present."""
    title = control.get("title", "")
    cid = control.get("id", "")
    if title and title != cid:
        return title
    for part in control.get("parts", []) or []:
        prose = part.get("prose")
        if prose:
            return prose
    return title


def fetch_from_text(text: str, *, fetched_at: date) -> FrameworkData:
    payload = json.loads(text)
    _title, version, raw_controls = parse_catalog(payload)
    controls = [Control(id=c["id"], title=_csf_title(c)) for c in raw_controls]
    return FrameworkData(
        metadata=Metadata(
            version=version,
            fetched_at=fetched_at,
            source_url=SOURCE_URL,
            fetcher="nist_csf",
        ),
        controls=controls,
    )


def fetch(*, fetched_at: date | None = None) -> FrameworkData:
    text = _http.fetch_text(SOURCE_URL)
    return fetch_from_text(text, fetched_at=fetched_at or date.today())
