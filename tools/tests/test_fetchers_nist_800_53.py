from datetime import date
from pathlib import Path

from ggi_policy.fetchers import nist_800_53


def test_fetch_from_text_normalizes_ids_to_uppercase(fixtures_dir: Path) -> None:
    text = (fixtures_dir / "fetchers/nist_800_53.oscal.json").read_text()
    fd = nist_800_53.fetch_from_text(text, fetched_at=date(2026, 5, 2))
    ids = [c.id for c in fd.controls]
    # OSCAL uses lowercase ids (`ac-2`); we normalize to the citation form (`AC-2`).
    assert "AC-2" in ids
    assert "AC-2(1)" in ids
    assert "AU-3" in ids


def test_enhancement_id_format(fixtures_dir: Path) -> None:
    text = (fixtures_dir / "fetchers/nist_800_53.oscal.json").read_text()
    fd = nist_800_53.fetch_from_text(text, fetched_at=date(2026, 5, 2))
    ids = {c.id for c in fd.controls}
    # AC-2.1 in OSCAL is AC-2(1) in citations
    assert "AC-2(1)" in ids
    assert "AC-2(2)" in ids


def test_metadata_includes_source_url(fixtures_dir: Path) -> None:
    text = (fixtures_dir / "fetchers/nist_800_53.oscal.json").read_text()
    fd = nist_800_53.fetch_from_text(text, fetched_at=date(2026, 5, 2))
    assert fd.metadata.source_url == nist_800_53.SOURCE_URL
    assert fd.metadata.fetcher == "nist_800_53"
    assert fd.metadata.version == "5.1.1"
