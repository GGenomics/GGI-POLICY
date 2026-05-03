from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class ValidationFinding:
    code: str           # short stable code, e.g., "FRONTMATTER_INVALID"
    path: Path
    message: str
    locator: str = ""   # JSON-pointer or rule sub-id, optional


@dataclass
class ValidationReport:
    findings: list[ValidationFinding] = field(default_factory=list)

    def add(self, finding: ValidationFinding) -> None:
        self.findings.append(finding)

    @property
    def ok(self) -> bool:
        return not self.findings
