from datetime import date
from pathlib import Path

from ggi_policy.fetchers import nist_800_171


def test_fetch_from_text_returns_three_dot_ids(fixtures_dir: Path) -> None:
    text = (fixtures_dir / "fetchers/nist_800_171.oscal.json").read_text()
    fd = nist_800_171.fetch_from_text(text, fetched_at=date(2026, 5, 2))
    ids = [c.id for c in fd.controls]
    assert "3.1.1" in ids
    assert "3.13.11" in ids
    assert len(fd.controls) == 4


def test_metadata(fixtures_dir: Path) -> None:
    text = (fixtures_dir / "fetchers/nist_800_171.oscal.json").read_text()
    fd = nist_800_171.fetch_from_text(text, fetched_at=date(2026, 5, 2))
    assert fd.metadata.fetcher == "nist_800_171"
    assert fd.metadata.version == "3.0.0"
