from pathlib import Path

from ggi_policy import io
from ggi_policy.result import ValidationReport
from ggi_policy.validate import consistency

DOMAIN_TO_FOLDER = {
    "IAM": "identity-and-access",
    "DAT": "data",
    "PRV": "privacy",
    "APP": "applications",
    "END": "endpoints",
    "NET": "network",
    "IR":  "incident-response",
    "VND": "vendor-and-third-party",
    "SEC": "security-operations",
    "BCP": "business-continuity",
    "HR":  "human-resources",
    "META":"meta",
}


def test_valid_policy_passes(fixtures_dir: Path) -> None:
    policy = io.load_policy(fixtures_dir / "valid/policies/identity-and-access/group-naming.md")
    report = ValidationReport()
    consistency.check(policy, fixtures_dir / "valid/policies", DOMAIN_TO_FOLDER, report)
    assert report.ok


def test_wrong_folder_for_domain_is_reported(fixtures_dir: Path) -> None:
    policy = io.load_policy(fixtures_dir / "invalid/consistency/policies/data/group-naming.md")
    report = ValidationReport()
    consistency.check(policy, fixtures_dir / "invalid/consistency/policies", DOMAIN_TO_FOLDER, report)
    codes = {f.code for f in report.findings}
    assert "POLICY_WRONG_FOLDER" in codes


def test_filename_mismatch_is_reported(fixtures_dir: Path) -> None:
    policy = io.load_policy(fixtures_dir / "invalid/consistency/policies/identity-and-access/wrong-name.md")
    report = ValidationReport()
    consistency.check(policy, fixtures_dir / "invalid/consistency/policies", DOMAIN_TO_FOLDER, report)
    codes = {f.code for f in report.findings}
    assert "POLICY_FILENAME_MISMATCH" in codes
