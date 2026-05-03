from datetime import date
from pathlib import Path

from ggi_policy import controls
from ggi_policy.fetchers._models import Control, FrameworkData, Metadata


def _sample_fd(name: str) -> FrameworkData:
    return FrameworkData(
        metadata=Metadata(
            version="1", fetched_at=date(2026, 5, 2),
            source_url="https://x", fetcher=name,
        ),
        controls=[Control(id="A", title="t")],
    )


def test_save_and_load_round_trips(tmp_path: Path) -> None:
    target = tmp_path / "fc.json"
    controls.save({"nist_csf": _sample_fd("nist_csf")}, target)
    loaded = controls.load(target)
    assert "nist_csf" in loaded["frameworks"]
    assert loaded["frameworks"]["nist_csf"]["controls"] == [{"id": "A", "title": "t"}]


def test_ids_for_returns_only_existing_framework(tmp_path: Path) -> None:
    target = tmp_path / "fc.json"
    controls.save({"cis": _sample_fd("cis")}, target)
    loaded = controls.load(target)
    assert controls.ids_for("cis", loaded) == {"A"}
    assert controls.ids_for("nist_csf", loaded) == set()
