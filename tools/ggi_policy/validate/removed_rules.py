from pathlib import Path

from ggi_policy.result import ValidationFinding, ValidationReport


def check(path: Path, rules: dict, report: ValidationReport) -> None:
    seen_status: dict[str, set[str]] = {}
    for rule in rules.get("rules", []):
        if not isinstance(rule, dict) or "id" not in rule:
            continue
        rid = rule["id"]
        status = rule.get("status", "active")
        seen_status.setdefault(rid, set()).add(status)
    for rid, statuses in seen_status.items():
        if "removed" in statuses and "active" in statuses:
            report.add(ValidationFinding(
                code="RULE_NUMBER_REUSED",
                path=path,
                message=(
                    f"rule id {rid!r} appears as both 'active' and 'removed' in this sidecar; "
                    f"removed numbers must never be reused"
                ),
                locator=rid,
            ))
