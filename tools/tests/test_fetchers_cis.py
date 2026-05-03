from datetime import date

from ggi_policy.fetchers import cis


def test_fetch_loads_snapshot() -> None:
    fd = cis.fetch(fetched_at=date(2026, 5, 2))
    ids = {c.id for c in fd.controls}
    assert "5.4" in ids
    assert "6.1" in ids


def test_metadata() -> None:
    fd = cis.fetch(fetched_at=date(2026, 5, 2))
    assert fd.metadata.fetcher == "cis"
    assert fd.metadata.version == "8.0"
    assert fd.metadata.source_url.startswith("https://www.cisecurity.org")
    assert fd.metadata.notes  # snapshot disclaimer
