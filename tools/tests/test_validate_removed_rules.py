from pathlib import Path

import yaml

from ggi_policy.result import ValidationReport
from ggi_policy.validate import removed_rules


def test_no_reuse_passes(fixtures_dir: Path) -> None:
    path = fixtures_dir / "valid/policies/identity-and-access/group-naming.rules.yaml"
    rules = yaml.safe_load(path.read_text())
    report = ValidationReport()
    removed_rules.check(path, rules, report)
    assert report.ok


def test_reused_removed_number_is_reported(fixtures_dir: Path) -> None:
    path = fixtures_dir / "invalid/rules/reused-removed-number.yaml"
    rules = yaml.safe_load(path.read_text())
    report = ValidationReport()
    removed_rules.check(path, rules, report)
    codes = {f.code for f in report.findings}
    assert "RULE_NUMBER_REUSED" in codes
