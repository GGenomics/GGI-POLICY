from pathlib import Path

from ggi_policy import codeowners, io, role_team_map
from ggi_policy.result import ValidationReport
from ggi_policy.validate import approvers as approvers_validate


def test_approvers_subset_of_codeowners_passes(fixtures_dir: Path) -> None:
    policy = io.load_policy(fixtures_dir / "valid/policies/identity-and-access/group-naming.md")
    rules = codeowners.parse(fixtures_dir.parent.parent.parent / ".github" / "CODEOWNERS")
    mapping = role_team_map.load(fixtures_dir.parent.parent.parent / "schemas" / "role-team-mapping.yaml")
    report = ValidationReport()
    approvers_validate.check(policy, rules, mapping, fixtures_dir / "valid", report)
    assert report.ok, [f.message for f in report.findings]


def test_unknown_approver_role_is_reported(fixtures_dir: Path) -> None:
    policy = io.load_policy(fixtures_dir / "invalid/approvers/policies/identity-and-access/bad-approver.md")
    rules = codeowners.parse(fixtures_dir / "invalid/approvers/CODEOWNERS")
    mapping = role_team_map.load(fixtures_dir / "invalid/approvers/role-team-mapping.yaml")
    report = ValidationReport()
    approvers_validate.check(policy, rules, mapping, fixtures_dir / "invalid/approvers", report)
    codes = {f.code for f in report.findings}
    assert "APPROVER_UNKNOWN_ROLE" in codes


def test_no_codeowners_rule_for_path_is_reported(fixtures_dir: Path) -> None:
    """If no CODEOWNERS rule covers the policy's path, surface that explicitly."""
    policy = io.load_policy(fixtures_dir / "valid/policies/identity-and-access/group-naming.md")
    rules: list[tuple[str, list[str]]] = []  # empty — no rules cover any path
    mapping = role_team_map.load(fixtures_dir.parent.parent.parent / "schemas" / "role-team-mapping.yaml")
    report = ValidationReport()
    approvers_validate.check(policy, rules, mapping, fixtures_dir / "valid", report)
    codes = {f.code for f in report.findings}
    assert "APPROVER_NO_CODEOWNERS_RULE" in codes


def test_role_team_not_in_codeowners_is_reported(fixtures_dir: Path) -> None:
    """A known role whose team is not among the path's CODEOWNERS owners must be flagged."""
    policy = io.load_policy(
        fixtures_dir / "invalid/approvers/policies/identity-and-access/wrong-team-approver.md"
    )
    rules = codeowners.parse(fixtures_dir / "invalid/approvers/CODEOWNERS")
    mapping = role_team_map.load(fixtures_dir / "invalid/approvers/role-team-mapping.yaml")
    report = ValidationReport()
    approvers_validate.check(policy, rules, mapping, fixtures_dir / "invalid/approvers", report)
    codes = {f.code for f in report.findings}
    assert "APPROVER_NOT_IN_CODEOWNERS" in codes
