from pathlib import Path

from ggi_policy import io
from ggi_policy.result import ValidationReport
from ggi_policy.validate import tags


def test_valid_tags_yield_no_findings(fixtures_dir: Path) -> None:
    policy = io.load_policy(fixtures_dir / "valid/policies/identity-and-access/group-naming.md")
    report = ValidationReport()
    tags.check(policy, report)
    assert report.ok


def test_bad_csf_tag_is_reported(fixtures_dir: Path) -> None:
    policy = io.load_policy(fixtures_dir / "invalid/tags/policies/identity-and-access/bad-csf.md")
    report = ValidationReport()
    tags.check(policy, report)
    codes = {f.code for f in report.findings}
    assert "TAG_FORMAT_INVALID" in codes
