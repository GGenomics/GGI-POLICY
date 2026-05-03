"""HIPAA Privacy + Security Rules fetcher via the eCFR API.

Pulls 45 CFR Part 164 and emits one Control per paragraph-level identifier
matching the citation form policies use (e.g., `164.308(a)(4)`).

The eCFR versioner v1 JSON ``/full`` endpoint was deprecated; the fetcher now
uses the XML ``/full`` endpoint and parses paragraph identifiers from the
``<P>`` element leading text.  The legacy ``fetch_from_text`` function still
accepts the old JSON shape (used by offline unit tests that supply a fixture).
"""

import json
import re
import xml.etree.ElementTree as ET
from datetime import date
from typing import Iterator

from ggi_policy.fetchers import _http
from ggi_policy.fetchers._models import Control, FrameworkData, Metadata


SOURCE_URL = "https://www.ecfr.gov/api/versioner/v1/full/2024-06-25/title-45.xml?part=164"


# ---------------------------------------------------------------------------
# Legacy JSON parser (kept for offline unit tests that supply a JSON fixture)
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# XML parser (used by the live fetch)
# ---------------------------------------------------------------------------

_ROMAN = frozenset(
    "i ii iii iv v vi vii viii ix x xi xii xiii xiv xv xvi xvii xviii xix xx".split()
)
_LEADING_IDS_RE = re.compile(r"^\(([a-z0-9]+)\)")


def _extract_leading_ids(p_text: str) -> list[str]:
    """Extract the run of parenthesized identifiers at the start of a <P> text."""
    ids: list[str] = []
    pos = 0
    while pos < len(p_text):
        m = _LEADING_IDS_RE.match(p_text[pos:])
        if m:
            ids.append(m.group(1))
            pos += len(m.group(0))
        else:
            break
    return ids


def _id_depth(first: str) -> int:
    """Infer the nesting depth (0-based) from the first identifier in a compound."""
    if first.isdigit():
        return 1          # (1), (2) → second level
    if first in _ROMAN:
        return 2          # (i), (ii) → third level
    if first.isupper():
        return 3          # (A), (B) → fourth level
    return 0              # (a), (b) → first level


def _parse_section_xml(section_num: str, section_elem: ET.Element) -> list[Control]:
    """Walk a DIV8/SECTION element and return Controls for paragraph-level identifiers."""
    controls: list[Control] = []
    # stack[depth] = current identifier at that depth; None means unset.
    stack: list[str | None] = [None, None, None, None]

    for child in section_elem:
        if child.tag != "P":
            continue
        p_text = (child.text or "").strip()
        if not p_text:
            continue
        leading = _extract_leading_ids(p_text)
        if not leading:
            continue

        depth = _id_depth(leading[0])
        # Clear all deeper levels when we step up or sideways.
        for d in range(depth + len(leading), 4):
            stack[d] = None
        # Populate stack at this depth and any compound depth.
        for i, lid in enumerate(leading):
            if depth + i < 4:
                stack[depth + i] = lid

        full_id = section_num + "".join(f"({x})" for x in stack if x is not None)

        # Title comes from the first <I> (italic) child, which eCFR uses for
        # standard/implementation-specification names.
        title_parts = [
            sub.text.strip().rstrip(".").rstrip(",")
            for sub in child
            if sub.tag == "I" and sub.text
        ]
        title = " ".join(title_parts)

        controls.append(Control(id=full_id, title=title))

    return controls


def fetch_from_xml(text: str, *, fetched_at: date) -> FrameworkData:
    """Parse the eCFR XML full-document response for Title 45 Part 164."""
    root = ET.fromstring(text)
    raw_controls: list[Control] = []
    for div8 in root.iter("DIV8"):
        if div8.get("TYPE") != "SECTION":
            continue
        section_num = div8.get("N", "")
        if not (section_num.startswith("164.") and len(section_num) > 4):
            continue
        raw_controls.extend(_parse_section_xml(section_num, div8))

    # Sections like §164.501 reuse identifiers like (1)/(2) under multiple
    # parallel definitions, producing duplicate full_ids from the parser.
    # Citations always disambiguate by section + paragraph, so first-wins
    # dedup keeps the catalog clean and the crosswalk readable.
    seen: set[str] = set()
    controls: list[Control] = []
    for c in raw_controls:
        if c.id in seen:
            continue
        seen.add(c.id)
        controls.append(c)

    return FrameworkData(
        metadata=Metadata(
            version="2024-06-25",
            fetched_at=fetched_at,
            source_url=SOURCE_URL,
            fetcher="hipaa",
        ),
        controls=controls,
    )


def fetch(*, fetched_at: date | None = None) -> FrameworkData:
    text = _http.fetch_text(SOURCE_URL)
    return fetch_from_xml(text, fetched_at=fetched_at or date.today())
