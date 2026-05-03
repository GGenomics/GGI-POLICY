"""Per-framework tag membership validation.

Phase 1 used regex format checks; Phase 2 upgrades to membership lookups against
schemas/framework-controls.json so that `PR.AC-99` (correct format, doesn't
exist) is caught.
"""

from ggi_policy.io import LoadedPolicy
from ggi_policy.result import ValidationFinding, ValidationReport


def check(policy: LoadedPolicy, catalog: dict, report: ValidationReport) -> None:
    """`catalog` is the parsed schemas/framework-controls.json document."""
    framework_index: dict[str, set[str]] = {
        framework: {c["id"] for c in fw.get("controls", [])}
        for framework, fw in catalog.get("frameworks", {}).items()
    }

    for framework, values in policy.metadata.get("frameworks", {}).items():
        known = framework_index.get(framework)
        if known is None:
            # Unknown framework key — covered by the frontmatter schema's
            # additionalProperties: false; no extra finding here.
            continue
        for value in values or []:
            if str(value) not in known:
                report.add(ValidationFinding(
                    code="TAG_UNKNOWN",
                    path=policy.path,
                    message=(
                        f"frameworks.{framework}: {value!r} is not in the "
                        f"canonical {framework} catalog"
                    ),
                    locator=f"frameworks/{framework}",
                ))
