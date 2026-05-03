from pathlib import Path

from ggi_policy import io
from ggi_policy.result import ValidationReport
from ggi_policy.validate import frontmatter as fm


def test_valid_policy_yields_no_findings(fixtures_dir: Path) -> None:
    policy = io.load_policy(fixtures_dir / "valid/policies/identity-and-access/group-naming.md")
    report = ValidationReport()
    fm.check(policy, report)
    assert report.ok, [f.message for f in report.findings]


def test_missing_id_is_reported(fixtures_dir: Path) -> None:
    policy = io.load_policy(fixtures_dir / "invalid/frontmatter/missing-id.md")
    report = ValidationReport()
    fm.check(policy, report)
    assert not report.ok
    codes = {f.code for f in report.findings}
    assert "FRONTMATTER_INVALID" in codes


def test_bad_status_is_reported(fixtures_dir: Path) -> None:
    policy = io.load_policy(fixtures_dir / "invalid/frontmatter/bad-status.md")
    report = ValidationReport()
    fm.check(policy, report)
    assert any("status" in f.message for f in report.findings)


def test_bad_version_is_reported(fixtures_dir: Path) -> None:
    policy = io.load_policy(fixtures_dir / "invalid/frontmatter/bad-version.md")
    report = ValidationReport()
    fm.check(policy, report)
    assert any("version" in f.message for f in report.findings)
