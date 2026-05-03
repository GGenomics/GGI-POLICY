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


def test_validate_accepts_valid_catalog(tmp_path: Path) -> None:
    """The committed framework-controls.json must validate against the
    committed framework-controls.schema.json."""
    from ggi_policy.repo import repo_root

    schemas = repo_root() / "schemas"
    catalog = controls.load(schemas / "framework-controls.json")
    errors = controls.validate(catalog, schemas / "framework-controls.schema.json")
    assert errors == [], f"committed catalog fails its own schema: {errors}"


def test_validate_rejects_invalid_catalog(tmp_path: Path) -> None:
    """Catalog missing the required `metadata.fetcher` field is reported."""
    from ggi_policy.repo import repo_root

    schemas = repo_root() / "schemas"
    bad_catalog = {
        "frameworks": {
            "cis": {
                "metadata": {"version": "8", "fetched_at": "2026-05-02", "source_url": "https://x"},
                "controls": [{"id": "1", "title": "x"}],
            }
        }
    }
    errors = controls.validate(bad_catalog, schemas / "framework-controls.schema.json")
    assert errors, "expected at least one validation error for catalog missing fetcher"


def test_load_with_validate_schema_raises_on_invalid(tmp_path: Path) -> None:
    target = tmp_path / "fc.json"
    target.write_text('{"frameworks": {"cis": {}}}')
    # Without schema_path co-located, load() falls back to the repo's schemas dir.
    from ggi_policy.repo import repo_root

    schema_src = repo_root() / "schemas" / "framework-controls.schema.json"
    (tmp_path / "framework-controls.schema.json").write_text(schema_src.read_text())

    import pytest

    with pytest.raises(ValueError, match="failed schema validation"):
        controls.load(target, validate_schema=True)
