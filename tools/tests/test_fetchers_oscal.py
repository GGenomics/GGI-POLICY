import json
from pathlib import Path

from ggi_policy.fetchers._oscal import iter_controls, parse_catalog


def test_parse_catalog_returns_metadata_and_controls(fixtures_dir: Path) -> None:
    payload = json.loads((fixtures_dir / "fetchers/nist_csf.oscal.json").read_text())
    title, version, controls = parse_catalog(payload)
    assert title == "NIST Cybersecurity Framework"
    assert version == "2.0"
    assert len(controls) == 5
    ids = [c["id"] for c in controls]
    assert "GV.OC-01" in ids and "PR.AC-04" in ids


def test_iter_controls_walks_nested_groups(fixtures_dir: Path) -> None:
    payload = json.loads((fixtures_dir / "fetchers/nist_csf.oscal.json").read_text())
    titles = {c["id"]: c["title"] for c in iter_controls(payload["catalog"]["groups"])}
    assert titles["PR.AC-01"].startswith("Identities")
