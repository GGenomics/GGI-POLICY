from pathlib import Path

from ggi_policy import codeowners
from ggi_policy.io import LoadedPolicy
from ggi_policy.result import ValidationFinding, ValidationReport


def check(
    policy: LoadedPolicy,
    codeowner_rules: list[tuple[str, list[str]]],
    role_to_team: dict[str, str],
    repo_root: Path,
    report: ValidationReport,
) -> None:
    approvers = policy.metadata.get("approvers", [])
    rel = policy.path.relative_to(repo_root).as_posix()
    expected_owners = set(codeowners.owners_for(rel, codeowner_rules))
    if not expected_owners:
        report.add(ValidationFinding(
            code="APPROVER_NO_CODEOWNERS_RULE",
            path=policy.path,
            message=f"no CODEOWNERS rule covers path {rel!r}",
            locator="approvers",
        ))
        return

    for role in approvers:
        team = role_to_team.get(role)
        if team is None:
            report.add(ValidationFinding(
                code="APPROVER_UNKNOWN_ROLE",
                path=policy.path,
                message=f"approver role {role!r} is not declared in role-team-mapping.yaml",
                locator=f"approvers/{role}",
            ))
            continue
        if team not in expected_owners:
            report.add(ValidationFinding(
                code="APPROVER_NOT_IN_CODEOWNERS",
                path=policy.path,
                message=(
                    f"approver {role!r} → {team!r} is not in the CODEOWNERS owners "
                    f"({sorted(expected_owners)}) for path {rel!r}"
                ),
                locator=f"approvers/{role}",
            ))
