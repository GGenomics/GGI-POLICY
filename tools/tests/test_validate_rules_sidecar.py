from pathlib import Path

import yaml

from ggi_policy.result import ValidationReport
from ggi_policy.validate import rules_sidecar


def test_valid_rules_yield_no_findings(fixtures_dir: Path) -> None:
    path = fixtures_dir / "valid/policies/identity-and-access/group-naming.rules.yaml"
    rules = yaml.safe_load(path.read_text())
    report = ValidationReport()
    rules_sidecar.check(path, rules, report)
    assert report.ok, [f.message for f in report.findings]


def test_duplicate_rule_id_is_reported(fixtures_dir: Path) -> None:
    path = fixtures_dir / "invalid/rules/duplicate-rule-id.yaml"
    rules = yaml.safe_load(path.read_text())
    report = ValidationReport()
    rules_sidecar.check(path, rules, report)
    codes = {f.code for f in report.findings}
    assert "RULE_ID_DUPLICATE" in codes


def test_missing_pattern_for_pattern_type_is_reported(fixtures_dir: Path) -> None:
    path = fixtures_dir / "invalid/rules/missing-pattern-for-pattern-type.yaml"
    rules = yaml.safe_load(path.read_text())
    report = ValidationReport()
    rules_sidecar.check(path, rules, report)
    codes = {f.code for f in report.findings}
    assert "RULES_INVALID" in codes
