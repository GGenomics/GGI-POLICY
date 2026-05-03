from pathlib import Path

from ggi_policy import io
from ggi_policy.result import ValidationReport
from ggi_policy.validate import exceptions as exc_validate


def _build_rule_index(fixtures_dir: Path) -> dict[str, dict]:
    """Walk valid fixtures + the auxiliary recommended-rule policy to build a sub-id -> rule map."""
    index: dict[str, dict] = {}
    for policy in io.iter_policies(fixtures_dir / "valid/policies"):
        rules = io.load_rules(policy.path)
        if not rules:
            continue
        for rule in rules["rules"]:
            index[f"{rules['policy_id']}.{rule['id']}"] = rule
    aux_policy = fixtures_dir / "invalid/exceptions/_recommended-rule-policy.md"
    aux_rules = io.load_rules(aux_policy)
    if aux_rules:
        for rule in aux_rules["rules"]:
            index[f"{aux_rules['policy_id']}.{rule['id']}"] = rule
    return index


def test_valid_exception_yields_no_findings(fixtures_dir: Path) -> None:
    rule_index = _build_rule_index(fixtures_dir)
    exc = io.load_exception(fixtures_dir / "valid/exceptions/EXC-2026-001-finance-legacy-group.md")
    report = ValidationReport()
    exc_validate.check(exc, rule_index, report)
    assert report.ok, [f.message for f in report.findings]


def test_cap_exceeded_for_required_rule(fixtures_dir: Path) -> None:
    rule_index = _build_rule_index(fixtures_dir)
    exc = io.load_exception(fixtures_dir / "invalid/exceptions/cap-exceeded-required.md")
    report = ValidationReport()
    exc_validate.check(exc, rule_index, report)
    codes = {f.code for f in report.findings}
    assert "EXCEPTION_CAP_EXCEEDED" in codes


def test_cap_exceeded_for_recommended_rule(fixtures_dir: Path) -> None:
    rule_index = _build_rule_index(fixtures_dir)
    exc = io.load_exception(fixtures_dir / "invalid/exceptions/cap-exceeded-recommended.md")
    report = ValidationReport()
    exc_validate.check(exc, rule_index, report)
    codes = {f.code for f in report.findings}
    assert "EXCEPTION_CAP_EXCEEDED" in codes


def test_dangling_policy_ref_is_reported(fixtures_dir: Path) -> None:
    rule_index = _build_rule_index(fixtures_dir)
    exc = io.load_exception(fixtures_dir / "invalid/exceptions/dangling-policy-ref.md")
    report = ValidationReport()
    exc_validate.check(exc, rule_index, report)
    codes = {f.code for f in report.findings}
    assert "EXCEPTION_DANGLING_REF" in codes
