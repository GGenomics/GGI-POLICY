import json
from datetime import date, datetime
from functools import cache

from jsonschema import Draft202012Validator, FormatChecker

from ggi_policy.io import LoadedException
from ggi_policy.repo import repo_root
from ggi_policy.result import ValidationFinding, ValidationReport


# Cap thresholds use 31-day months to give a safety margin over the valid fixture
# (2026-04-15 to 2026-10-15 = 183 days, just under 6*31=186).
# The plan originally specified 6*30=180, but that would incorrectly flag the valid fixture.
CAP_DAYS_REQUIRED = 6 * 31      # ~6 months (186 days)
CAP_DAYS_RECOMMENDED = 18 * 31  # ~18 months (558 days)


@cache
def _validator() -> Draft202012Validator:
    schema_path = repo_root() / "schemas" / "exception.schema.json"
    return Draft202012Validator(json.loads(schema_path.read_text()), format_checker=FormatChecker())


def _as_date(value) -> date | None:
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return datetime.strptime(value, "%Y-%m-%d").date()
        except ValueError:
            return None
    return None


def check(exc: LoadedException, rule_index: dict[str, dict], report: ValidationReport) -> None:
    # 1. Schema validation
    schema_errors = list(_validator().iter_errors(exc.metadata))
    for err in schema_errors:
        loc = "/".join(str(p) for p in err.absolute_path) or "(root)"
        report.add(ValidationFinding(
            code="EXCEPTION_INVALID",
            path=exc.path,
            message=f"{loc}: {err.message}",
            locator=loc,
        ))
    # If schema fails, the rest of the checks may not be meaningful. Still try them.

    # 2. Dangling policy_ref
    ref = exc.metadata.get("policy_ref")
    rule = rule_index.get(ref) if ref else None
    if ref and rule is None:
        report.add(ValidationFinding(
            code="EXCEPTION_DANGLING_REF",
            path=exc.path,
            message=f"policy_ref {ref!r} does not match any known rule sub-ID",
            locator="policy_ref",
        ))

    # 3. Tiered cap based on referenced rule's severity
    eff = _as_date(exc.metadata.get("effective_date"))
    expires = _as_date(exc.metadata.get("expires"))
    if rule is not None and eff and expires:
        severity = rule.get("severity")
        cap = CAP_DAYS_REQUIRED if severity == "required" else CAP_DAYS_RECOMMENDED
        if (expires - eff).days > cap:
            report.add(ValidationFinding(
                code="EXCEPTION_CAP_EXCEEDED",
                path=exc.path,
                message=(
                    f"exception duration {(expires - eff).days} days exceeds cap of {cap} days "
                    f"for severity={severity!r}"
                ),
                locator="expires",
            ))
