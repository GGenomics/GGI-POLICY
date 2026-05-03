from pathlib import Path

from ggi_policy.io import LoadedPolicy
from ggi_policy.result import ValidationFinding, ValidationReport


def _id_to_slug(policy_id: str) -> str:
    """POL-IAM-GROUP-NAMING -> group-naming"""
    parts = policy_id.split("-", 2)
    return parts[2].lower() if len(parts) == 3 else ""


def check(
    policy: LoadedPolicy,
    policies_root: Path,
    domain_to_folder: dict[str, str],
    report: ValidationReport,
) -> None:
    metadata = policy.metadata
    pid = metadata.get("id", "")
    domain = metadata.get("domain", "")
    expected_folder_name = domain_to_folder.get(domain)
    expected_slug = _id_to_slug(pid)

    rel = policy.path.relative_to(policies_root)
    actual_folder = rel.parts[0] if len(rel.parts) >= 2 else ""
    actual_filename_stem = policy.path.stem

    if expected_folder_name and actual_folder != expected_folder_name:
        report.add(ValidationFinding(
            code="POLICY_WRONG_FOLDER",
            path=policy.path,
            message=(
                f"domain={domain!r} requires folder {expected_folder_name!r}; "
                f"file is in {actual_folder!r}"
            ),
            locator="domain",
        ))

    if expected_slug and actual_filename_stem != expected_slug:
        report.add(ValidationFinding(
            code="POLICY_FILENAME_MISMATCH",
            path=policy.path,
            message=(
                f"id={pid!r} requires filename {expected_slug!r}.md; "
                f"actual stem is {actual_filename_stem!r}"
            ),
            locator="id",
        ))
