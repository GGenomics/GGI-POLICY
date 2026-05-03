"""Per-rule enforceability and evaluation helpers.

These are the canonical helpers cited by POL-META-AI-AGENT-CONTRACT.R2 and
POL-META-DOC-FRAMEWORK.R7. Consumers MUST use ``is_enforceable`` and
``evaluate`` rather than re-implementing the predicate so the framework
keeps a single source of truth.

Design references: design spec §7.1 (lifecycle states), §9.2 (enforceability rule).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any

from ggi_policy import io


def _as_date(value) -> date | None:
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return datetime.strptime(value, "%Y-%m-%d").date()
        except ValueError:
            return None
    return None


@dataclass(frozen=True)
class EvaluationResult:
    rule_id: str            # full sub-id, e.g., "POL-IAM-GROUP-NAMING.R1"
    verdict: str            # "compliant" | "non_compliant" | "skipped" | "unknown_rule"
    severity: str           # "required" | "recommended" | ""
    citation: str           # square-bracketed citation per §9.3
    exceptions: tuple[str, ...]


def _find_rule(
    repo_root: Path, full_rule_id: str
) -> tuple[dict | None, dict | None]:
    """Locate (policy_metadata, rule_dict) for ``POL-...Rn``."""
    if "." not in full_rule_id:
        return None, None
    policy_id, rule_short = full_rule_id.split(".", 1)
    for policy in io.iter_policies(repo_root / "policies"):
        if policy.metadata.get("id") != policy_id:
            continue
        rules = io.load_rules(policy.path)
        if not rules:
            return policy.metadata, None
        for r in rules.get("rules", []):
            if r.get("id") == rule_short:
                return policy.metadata, r
        return policy.metadata, None
    return None, None


def _active_exception_for(
    repo_root: Path, full_rule_id: str, today: date
) -> str | None:
    """Return the EXC ID of an active exception covering ``full_rule_id``, if any."""
    exc_root = repo_root / "exceptions"
    if not exc_root.exists():
        return None
    for exc in io.iter_exceptions(exc_root):
        meta = exc.metadata
        if meta.get("status") != "active":
            continue
        if meta.get("policy_ref") != full_rule_id:
            continue
        expires = _as_date(meta.get("expires"))
        if expires is None or expires < today:
            continue
        return meta.get("id", "")
    return None


def is_enforceable(
    repo_root: Path,
    policy_id: str,
    rule_id: str,
    *,
    today: date | None = None,
) -> bool:
    """Return True iff the rule {policy_id}.{rule_id} is enforceable today.

    Per design §9.2:
      1. Parent policy has status: effective, AND
      2. Parent policy's effective_date <= today, AND
      3. No active exception cites the full rule sub-id.
    """
    today = today or date.today()
    full_rule_id = f"{policy_id}.{rule_id}"
    policy_meta, rule = _find_rule(repo_root, full_rule_id)
    if policy_meta is None or rule is None:
        return False
    if policy_meta.get("status") != "effective":
        return False
    eff = _as_date(policy_meta.get("effective_date"))
    if eff is None or eff > today:
        return False
    if _active_exception_for(repo_root, full_rule_id, today):
        return False
    return True


def evaluate(
    repo_root: Path,
    full_rule_id: str,
    candidate: Any,
    *,
    today: date | None = None,
) -> EvaluationResult:
    """Evaluate `candidate` against the rule identified by `full_rule_id`.

    Returns one of four verdicts:
      - ``compliant``     — candidate satisfies the rule
      - ``non_compliant`` — candidate violates the rule
      - ``skipped``       — rule is not enforceable (draft / future date / active exception)
                            OR rule type requires custom evaluation (flag, setting, decision_table)
      - ``unknown_rule``  — full_rule_id doesn't resolve to a known rule

    Type-specific evaluation supported here: ``pattern``, ``allowed_values``,
    ``forbidden_values``. ``flag``/``setting``/``decision_table`` rules return
    ``skipped`` because they require domain-specific evaluators (e.g., a live
    Entra group's PIM-eligibility status).
    """
    today = today or date.today()
    if "." not in full_rule_id:
        return EvaluationResult(
            rule_id=full_rule_id,
            verdict="unknown_rule",
            severity="",
            citation=f"[{full_rule_id}] not a valid full rule sub-id",
            exceptions=(),
        )
    policy_id, _ = full_rule_id.split(".", 1)
    policy_meta, rule = _find_rule(repo_root, full_rule_id)
    if rule is None:
        return EvaluationResult(
            rule_id=full_rule_id,
            verdict="unknown_rule",
            severity="",
            citation=f"[{full_rule_id}] no such rule",
            exceptions=(),
        )

    severity = rule.get("severity", "")
    exc_id = _active_exception_for(repo_root, full_rule_id, today)
    exceptions = (exc_id,) if exc_id else ()

    if not is_enforceable(
        repo_root, policy_id, rule["id"], today=today
    ):
        status = policy_meta.get("status", "missing") if policy_meta else "missing"
        eff = policy_meta.get("effective_date", "missing") if policy_meta else "missing"
        return EvaluationResult(
            rule_id=full_rule_id,
            verdict="skipped",
            severity=severity,
            citation=(
                f"[{full_rule_id}] rule not enforceable "
                f"(status={status!r}, effective_date={eff!r}, active_exception={exc_id!r})"
            ),
            exceptions=exceptions,
        )

    rtype = rule.get("type")
    if rtype == "pattern":
        pattern = rule.get("pattern", "")
        if not pattern:
            return EvaluationResult(
                rule_id=full_rule_id, verdict="unknown_rule", severity=severity,
                citation=f"[{full_rule_id}] rule has no pattern field",
                exceptions=exceptions,
            )
        if re.match(pattern, str(candidate)):
            verdict, msg = "compliant", f"{candidate!r} matches required pattern"
        else:
            verdict, msg = "non_compliant", f"{candidate!r} does not match {pattern!r}"
    elif rtype == "allowed_values":
        allowed = rule.get("allowed", [])
        if candidate in allowed:
            verdict, msg = "compliant", f"{candidate!r} is in allowed values"
        else:
            verdict, msg = "non_compliant", f"{candidate!r} is not in allowed values"
    elif rtype == "forbidden_values":
        forbidden = rule.get("forbidden", [])
        if candidate in forbidden:
            verdict, msg = "non_compliant", f"{candidate!r} is forbidden"
        else:
            verdict, msg = "compliant", f"{candidate!r} is not forbidden"
    else:
        return EvaluationResult(
            rule_id=full_rule_id, verdict="skipped", severity=severity,
            citation=f"[{full_rule_id}] rule type {rtype!r} requires a domain-specific evaluator",
            exceptions=exceptions,
        )

    return EvaluationResult(
        rule_id=full_rule_id,
        verdict=verdict,
        severity=severity,
        citation=f"[{full_rule_id}] {msg}",
        exceptions=exceptions,
    )
