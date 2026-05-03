"""HIPAA Privacy + Security Rules fetcher via the eCFR API.

Pulls 45 CFR Part 164 and emits one Control per paragraph-level identifier
matching the citation form policies use (e.g., `164.308(a)(4)`).
"""

import json
from datetime import date
from typing import Iterator

from ggi_policy.fetchers import _http
from ggi_policy.fetchers._models import Control, FrameworkData, Metadata


SOURCE_URL = "https://www.ecfr.gov/api/versioner/v1/full/latest/title-45.json?part=164"


def _walk(node: dict) -> Iterator[dict]:
    yield node
    for child in node.get("children", []) or []:
        yield from _walk(child)


def fetch_from_text(text: str, *, fetched_at: date) -> FrameworkData:
    payload = json.loads(text)
    structure = payload.get("structure", {})
    catalog_date = payload.get("meta", {}).get("date", fetched_at.isoformat())
    controls: list[Control] = []
    for node in _walk(structure):
        if node.get("type") != "paragraph":
            continue
        identifier = node.get("identifier", "")
        # Only paragraph-level identifiers under §164 with at least one parenthesized component.
        if not identifier.startswith("164.") or "(" not in identifier:
            continue
        controls.append(Control(id=identifier, title=node.get("label", "")))
    return FrameworkData(
        metadata=Metadata(
            version=catalog_date,
            fetched_at=fetched_at,
            source_url=SOURCE_URL,
            fetcher="hipaa",
        ),
        controls=controls,
    )


def fetch(*, fetched_at: date | None = None) -> FrameworkData:
    text = _http.fetch_text(SOURCE_URL)
    return fetch_from_text(text, fetched_at=fetched_at or date.today())
