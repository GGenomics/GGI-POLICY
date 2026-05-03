from datetime import date
from pathlib import Path

from ggi_policy.fetchers import hipaa


def test_fetch_from_text_returns_paragraph_level_controls(fixtures_dir: Path) -> None:
    text = (fixtures_dir / "fetchers/hipaa.ecfr.json").read_text()
    fd = hipaa.fetch_from_text(text, fetched_at=date(2026, 5, 2))
    ids = {c.id for c in fd.controls}
    # We only emit paragraph-level identifiers under §164, not section roots.
    assert "164.308(a)(1)" in ids
    assert "164.308(a)(4)" in ids
    assert "164.312(a)(2)(i)" in ids
    # Section roots like "164.308" are NOT controls in our model.
    assert "164.308" not in ids


def test_titles_come_from_label_field(fixtures_dir: Path) -> None:
    text = (fixtures_dir / "fetchers/hipaa.ecfr.json").read_text()
    fd = hipaa.fetch_from_text(text, fetched_at=date(2026, 5, 2))
    by_id = {c.id: c.title for c in fd.controls}
    assert by_id["164.308(a)(4)"] == "Information access management"


def test_metadata(fixtures_dir: Path) -> None:
    text = (fixtures_dir / "fetchers/hipaa.ecfr.json").read_text()
    fd = hipaa.fetch_from_text(text, fetched_at=date(2026, 5, 2))
    assert fd.metadata.fetcher == "hipaa"
    assert fd.metadata.version == "2026-04-15"


def test_fetch_from_xml_parses_paragraph_ids(fixtures_dir: Path) -> None:
    from ggi_policy.fetchers import hipaa

    text = (fixtures_dir / "fetchers/hipaa.ecfr.xml").read_text()
    fd = hipaa.fetch_from_xml(text, fetched_at=date(2026, 5, 2))
    ids = {c.id for c in fd.controls}
    assert "164.308(a)(1)" in ids
    assert "164.308(a)(4)" in ids
    assert "164.312(a)(2)(i)" in ids


def test_fetch_from_xml_titles_come_from_italic_headers(fixtures_dir: Path) -> None:
    from ggi_policy.fetchers import hipaa

    text = (fixtures_dir / "fetchers/hipaa.ecfr.xml").read_text()
    fd = hipaa.fetch_from_xml(text, fetched_at=date(2026, 5, 2))
    by_id = {c.id: c.title for c in fd.controls}
    assert "Information access management" in by_id["164.308(a)(4)"]


def test_fetch_from_xml_dedups_duplicate_paragraph_ids(fixtures_dir: Path, tmp_path: Path) -> None:
    """Sections that emit the same paragraph id more than once (e.g., parallel
    definitions in §164.501) are dedup'd: first occurrence wins."""
    from ggi_policy.fetchers import hipaa

    xml_with_dup = """<?xml version="1.0" encoding="UTF-8"?>
<DLPSTEXTCLASS>
  <DIV7 TYPE="PART" N="164">
    <DIV8 TYPE="SECTION" N="164.501">
      <HEAD>§ 164.501 Definitions.</HEAD>
      <P>(1) <I>First definition.</I></P>
      <P>(2) <I>Second definition.</I></P>
      <P>(1) <I>Third definition (parallel structure).</I></P>
    </DIV8>
  </DIV7>
</DLPSTEXTCLASS>"""
    fd = hipaa.fetch_from_xml(xml_with_dup, fetched_at=date(2026, 5, 2))
    ids = [c.id for c in fd.controls]
    # First occurrence wins for "164.501(1)"; the second-occurrence "Third
    # definition" is dropped.
    assert ids.count("164.501(1)") == 1
    assert "164.501(2)" in ids
