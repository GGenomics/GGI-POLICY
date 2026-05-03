from datetime import date

from ggi_policy.fetchers import soc2


def test_fetch_loads_snapshot() -> None:
    fd = soc2.fetch(fetched_at=date(2026, 5, 2))
    ids = {c.id for c in fd.controls}
    assert "CC6.1" in ids
    assert "A1.1" in ids
    assert "PI1.1" in ids


def test_metadata() -> None:
    fd = soc2.fetch(fetched_at=date(2026, 5, 2))
    assert fd.metadata.fetcher == "soc2"
    assert fd.metadata.version.startswith("TSC-2017")
    assert fd.metadata.notes  # disclaimer about manual maintenance
