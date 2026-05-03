import re

from ggi_policy.io import LoadedPolicy
from ggi_policy.result import ValidationFinding, ValidationReport


PATTERNS = {
    "nist_csf":     re.compile(r"^(GV|ID|PR|DE|RS|RC)\.[A-Z]{2}-\d+$"),
    "cis":          re.compile(r"^\d+(\.\d+)?$"),
    "soc2":         re.compile(r"^(CC|A|PI|C|P)\d+\.\d+$"),
    "hipaa":        re.compile(r"^164\.\d{3}\([a-z]\)(\(\d+\))?(\([ivx]+\))?$"),
    "nist_800_53":  re.compile(r"^[A-Z]{2}-\d+(\(\d+\))?$"),
    "nist_800_171": re.compile(r"^\d+\.\d+\.\d+$"),
}


def check(policy: LoadedPolicy, report: ValidationReport) -> None:
    for framework, values in policy.metadata.get("frameworks", {}).items():
        pattern = PATTERNS.get(framework)
        if pattern is None:
            continue  # frontmatter schema covers unknown framework keys
        for value in values or []:
            if not pattern.match(str(value)):
                report.add(ValidationFinding(
                    code="TAG_FORMAT_INVALID",
                    path=policy.path,
                    message=f"frameworks.{framework}: {value!r} does not match expected format",
                    locator=f"frameworks/{framework}",
                ))
