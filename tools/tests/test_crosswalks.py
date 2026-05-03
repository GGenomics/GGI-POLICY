from datetime import date
from pathlib import Path

from ggi_policy import crosswalks


SAMPLE_CATALOG = {
    "frameworks": {
        "nist_csf": {
            "metadata": {
                "version": "2.0", "fetched_at": "2026-05-02",
                "source_url": "https://x", "fetcher": "nist_csf",
            },
            "controls": [
                {"id": "GV.OC-01", "title": "The organizational mission is understood and informs cybersecurity risk management"},
                {"id": "PR.AC-01", "title": "Identities and credentials are issued, managed, verified, revoked, and audited"},
            ],
        }
    }
}


def test_render_replaces_marker_regions(fixtures_dir: Path) -> None:
    empty = (fixtures_dir / "crosswalks/nist-csf-empty.md").read_text()
    expected = (fixtures_dir / "crosswalks/nist-csf-populated.md").read_text()
    coverage = {"PR.AC-01": ["POL-IAM-GROUP-NAMING"]}
    rendered = crosswalks.render(empty, "nist_csf", SAMPLE_CATALOG, coverage)
    assert rendered.strip() == expected.strip()


def test_render_is_idempotent(fixtures_dir: Path) -> None:
    text = (fixtures_dir / "crosswalks/nist-csf-empty.md").read_text()
    coverage = {"PR.AC-01": ["POL-IAM-GROUP-NAMING"]}
    once = crosswalks.render(text, "nist_csf", SAMPLE_CATALOG, coverage)
    twice = crosswalks.render(once, "nist_csf", SAMPLE_CATALOG, coverage)
    assert once == twice


def test_build_coverage_inverts_policy_frameworks_block() -> None:
    policies = [
        {"id": "POL-IAM-GROUP-NAMING", "frameworks": {"nist_csf": ["PR.AC-01", "PR.AC-03"]}},
        {"id": "POL-DAT-CLASSIFICATION", "frameworks": {"nist_csf": ["PR.AC-01"]}},
    ]
    coverage = crosswalks.build_coverage(policies, framework="nist_csf")
    assert coverage["PR.AC-01"] == ["POL-DAT-CLASSIFICATION", "POL-IAM-GROUP-NAMING"]
    assert coverage["PR.AC-03"] == ["POL-IAM-GROUP-NAMING"]
