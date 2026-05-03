"""Tests for tools/ggi_policy/enforce.py — is_enforceable + evaluate.

Synthetic repo trees are constructed under tmp_path so we can vary policy
status / effective_date / exception state without touching the live repo.
"""

from datetime import date
from pathlib import Path

from ggi_policy import enforce


_BASE_FRONTMATTER = """\
---
id: {policy_id}
title: Test
summary: Test fixture for enforce.py.
domain: IAM
status: {status}
version: 1.0.0
effective_date: {effective_date}
last_reviewed: 2026-05-01
review_cycle: annual
owner: IT Director
approvers: [CISO, IT Director]
applies_to: [test]
supersedes: []
related: []
frameworks: {{}}
external_references: []
---

## Purpose
Test fixture body.
"""

_BASE_RULES = """\
policy_id: {policy_id}
rules:
  - id: R1
    statement: Names match the prescribed pattern.
    type: pattern
    severity: required
    pattern: "^sg-[a-z]+-[a-z0-9-]+$"
  - id: R2
    statement: Type is allowed.
    type: allowed_values
    severity: recommended
    allowed: [security, distribution, m365]
  - id: R3
    statement: Name does not contain banned terms.
    type: forbidden_values
    severity: required
    forbidden: ["temp", "test123"]
  - id: R4
    statement: PIM is required (custom evaluation needed).
    type: flag
    severity: required
"""


def _make_repo(
    tmp_path: Path,
    *,
    status: str = "effective",
    effective_date: str = "2026-01-01",
    policy_id: str = "POL-IAM-TEST",
) -> Path:
    """Build a minimal repo tree under tmp_path with one policy + rules."""
    p = tmp_path / "policies/identity-and-access"
    p.mkdir(parents=True)
    (p / "test.md").write_text(
        _BASE_FRONTMATTER.format(
            policy_id=policy_id, status=status, effective_date=effective_date
        )
    )
    (p / "test.rules.yaml").write_text(_BASE_RULES.format(policy_id=policy_id))
    return tmp_path


def _add_exception(
    tmp_path: Path,
    *,
    policy_ref: str = "POL-IAM-TEST.R1",
    status: str = "active",
    expires: str = "2026-12-31",
) -> None:
    e = tmp_path / "exceptions"
    e.mkdir(exist_ok=True)
    (e / "EXC-2026-001-test.md").write_text(f"""\
---
id: EXC-2026-001-TEST
policy_ref: {policy_ref}
requested_by: jane@ggenomics.com
approver: CISO
approved_date: 2026-04-15
effective_date: 2026-04-15
expires: {expires}
status: {status}
compensating_control: n/a
risk_acceptance: documented
---

## Justification
Test.
""")


# is_enforceable -------------------------------------------------------------

def test_is_enforceable_true_for_effective_policy(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path, status="effective", effective_date="2026-01-01")
    assert enforce.is_enforceable(repo, "POL-IAM-TEST", "R1", today=date(2026, 5, 3))


def test_is_enforceable_false_for_draft(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path, status="draft")
    assert not enforce.is_enforceable(repo, "POL-IAM-TEST", "R1", today=date(2026, 5, 3))


def test_is_enforceable_false_for_future_effective_date(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path, effective_date="2027-01-01")
    assert not enforce.is_enforceable(repo, "POL-IAM-TEST", "R1", today=date(2026, 5, 3))


def test_is_enforceable_false_when_active_exception_covers_rule(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)
    _add_exception(tmp_path, policy_ref="POL-IAM-TEST.R1", status="active",
                   expires="2026-12-31")
    assert not enforce.is_enforceable(repo, "POL-IAM-TEST", "R1", today=date(2026, 5, 3))


def test_is_enforceable_true_when_exception_is_revoked(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)
    _add_exception(tmp_path, status="revoked")
    assert enforce.is_enforceable(repo, "POL-IAM-TEST", "R1", today=date(2026, 5, 3))


def test_is_enforceable_true_when_exception_has_expired(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)
    _add_exception(tmp_path, expires="2026-04-01")  # before today
    assert enforce.is_enforceable(repo, "POL-IAM-TEST", "R1", today=date(2026, 5, 3))


def test_is_enforceable_unaffected_by_exception_for_different_rule(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)
    _add_exception(tmp_path, policy_ref="POL-IAM-TEST.R2")  # exception covers R2, not R1
    assert enforce.is_enforceable(repo, "POL-IAM-TEST", "R1", today=date(2026, 5, 3))


def test_is_enforceable_false_for_unknown_rule(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)
    assert not enforce.is_enforceable(repo, "POL-IAM-NOPE", "R1", today=date(2026, 5, 3))


# evaluate -------------------------------------------------------------------

def test_evaluate_pattern_compliant(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)
    result = enforce.evaluate(repo, "POL-IAM-TEST.R1", "sg-az-prod-finance", today=date(2026, 5, 3))
    assert result.verdict == "compliant"
    assert result.severity == "required"
    assert result.citation.startswith("[POL-IAM-TEST.R1]")


def test_evaluate_pattern_non_compliant(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)
    result = enforce.evaluate(repo, "POL-IAM-TEST.R1", "Marketing-2024", today=date(2026, 5, 3))
    assert result.verdict == "non_compliant"
    assert "does not match" in result.citation


def test_evaluate_allowed_values(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)
    assert enforce.evaluate(repo, "POL-IAM-TEST.R2", "security",
                            today=date(2026, 5, 3)).verdict == "compliant"
    assert enforce.evaluate(repo, "POL-IAM-TEST.R2", "shared_mailbox",
                            today=date(2026, 5, 3)).verdict == "non_compliant"


def test_evaluate_forbidden_values(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)
    assert enforce.evaluate(repo, "POL-IAM-TEST.R3", "temp",
                            today=date(2026, 5, 3)).verdict == "non_compliant"
    assert enforce.evaluate(repo, "POL-IAM-TEST.R3", "production",
                            today=date(2026, 5, 3)).verdict == "compliant"


def test_evaluate_skipped_for_draft_policy(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path, status="draft")
    result = enforce.evaluate(repo, "POL-IAM-TEST.R1", "sg-az-prod-finance",
                              today=date(2026, 5, 3))
    assert result.verdict == "skipped"
    assert "not enforceable" in result.citation


def test_evaluate_skipped_with_active_exception(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)
    _add_exception(tmp_path)
    result = enforce.evaluate(repo, "POL-IAM-TEST.R1", "Marketing-2024",
                              today=date(2026, 5, 3))
    assert result.verdict == "skipped"
    assert result.exceptions == ("EXC-2026-001-TEST",)


def test_evaluate_unknown_rule(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)
    result = enforce.evaluate(repo, "POL-IAM-TEST.R99", "anything", today=date(2026, 5, 3))
    assert result.verdict == "unknown_rule"


def test_evaluate_unknown_policy(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)
    result = enforce.evaluate(repo, "POL-IAM-NOPE.R1", "anything", today=date(2026, 5, 3))
    assert result.verdict == "unknown_rule"


def test_evaluate_skipped_for_flag_type(tmp_path: Path) -> None:
    """flag / setting / decision_table rules require a domain-specific evaluator;
    evaluate() returns skipped rather than guessing."""
    repo = _make_repo(tmp_path)
    result = enforce.evaluate(repo, "POL-IAM-TEST.R4", True, today=date(2026, 5, 3))
    assert result.verdict == "skipped"
    assert "domain-specific evaluator" in result.citation


def test_evaluate_malformed_full_rule_id(tmp_path: Path) -> None:
    """Missing the .Rn portion."""
    repo = _make_repo(tmp_path)
    result = enforce.evaluate(repo, "POL-IAM-TEST", "x", today=date(2026, 5, 3))
    assert result.verdict == "unknown_rule"
