import json
from collections import Counter
from functools import cache
from pathlib import Path

from jsonschema import Draft202012Validator

from ggi_policy.repo import repo_root
from ggi_policy.result import ValidationFinding, ValidationReport


@cache
def _validator() -> Draft202012Validator:
    schema_path = repo_root() / "schemas" / "policy-rules.schema.json"
    return Draft202012Validator(json.loads(schema_path.read_text()))


def check(path: Path, rules: dict, report: ValidationReport) -> None:
    for err in _validator().iter_errors(rules):
        loc = "/".join(str(p) for p in err.absolute_path) or "(root)"
        report.add(ValidationFinding(
            code="RULES_INVALID",
            path=path,
            message=f"{loc}: {err.message}",
            locator=loc,
        ))

    counts = Counter(r["id"] for r in rules.get("rules", []) if isinstance(r, dict) and "id" in r)
    for rule_id, n in counts.items():
        if n > 1:
            report.add(ValidationFinding(
                code="RULE_ID_DUPLICATE",
                path=path,
                message=f"rule id {rule_id!r} appears {n} times; sub-IDs must be unique within a sidecar",
                locator=rule_id,
            ))
