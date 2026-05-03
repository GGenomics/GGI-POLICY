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
