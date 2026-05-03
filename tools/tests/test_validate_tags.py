from pathlib import Path

from ggi_policy import io
from ggi_policy.result import ValidationReport
from ggi_policy.validate import tags


SAMPLE_CATALOG = {
    "frameworks": {
        "nist_csf": {"controls": [
            {"id": "PR.AC-1", "title": "x"},
            {"id": "PR.AC-3", "title": "x"},
            {"id": "PR.AC-01", "title": "x"},
            {"id": "PR.AC-03", "title": "x"},
        ]},
        "cis":          {"controls": [{"id": "5.4", "title": "x"}, {"id": "6.1", "title": "x"}]},
        "soc2":         {"controls": [{"id": "CC6.1", "title": "x"}]},
        "hipaa":        {"controls": [{"id": "164.308(a)(4)(i)", "title": "x"}]},
        "nist_800_53":  {"controls": [{"id": "AC-2", "title": "x"}]},
        "nist_800_171": {"controls": [{"id": "3.1.1", "title": "x"}]},
    }
}


def test_valid_tags_yield_no_findings(fixtures_dir: Path) -> None:
    policy = io.load_policy(fixtures_dir / "valid/policies/identity-and-access/group-naming.md")
    report = ValidationReport()
    tags.check(policy, SAMPLE_CATALOG, report)
    assert report.ok, [f.message for f in report.findings]


def test_unknown_csf_tag_is_reported(fixtures_dir: Path) -> None:
    policy = io.load_policy(fixtures_dir / "invalid/tags/policies/identity-and-access/unknown-csf.md")
    report = ValidationReport()
    tags.check(policy, SAMPLE_CATALOG, report)
    codes = {f.code for f in report.findings}
    assert "TAG_UNKNOWN" in codes
