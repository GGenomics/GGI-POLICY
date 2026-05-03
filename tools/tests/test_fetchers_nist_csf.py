from datetime import date
from pathlib import Path

from ggi_policy.fetchers import nist_csf


def test_fetch_from_text_returns_framework_data(fixtures_dir: Path) -> None:
    text = (fixtures_dir / "fetchers/nist_csf.oscal.json").read_text()
    fd = nist_csf.fetch_from_text(text, fetched_at=date(2026, 5, 2))
    assert fd.metadata.fetcher == "nist_csf"
    assert fd.metadata.version == "2.0"
    assert fd.metadata.fetched_at == date(2026, 5, 2)
    ids = [c.id for c in fd.controls]
    assert "PR.AC-01" in ids
    assert len(fd.controls) == 5
    pr_ac_01 = next(c for c in fd.controls if c.id == "PR.AC-01")
    assert pr_ac_01.title.startswith("Identities")


def test_fetch_invokes_http_then_parses(fixtures_dir: Path, monkeypatch) -> None:
    canned = (fixtures_dir / "fetchers/nist_csf.oscal.json").read_text()
    monkeypatch.setattr(
        "ggi_policy.fetchers.nist_csf._http.fetch_text",
        lambda url: canned,
    )
    fd = nist_csf.fetch(fetched_at=date(2026, 5, 2))
    assert fd.metadata.source_url == nist_csf.SOURCE_URL
    assert len(fd.controls) == 5
