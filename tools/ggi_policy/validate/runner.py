from pathlib import Path

from ggi_policy import codeowners, io, role_team_map
from ggi_policy.result import ValidationReport
from ggi_policy.validate import (
    approvers, consistency, exceptions as exc_validate, frontmatter as fm,
    removed_rules, rules_sidecar, tags,
)

DOMAIN_TO_FOLDER = {
    "IAM": "identity-and-access", "DAT": "data", "PRV": "privacy",
    "APP": "applications", "END": "endpoints", "NET": "network",
    "IR":  "incident-response", "VND": "vendor-and-third-party",
    "SEC": "security-operations", "BCP": "business-continuity",
    "HR":  "human-resources", "META": "meta",
}


def run(repo_root: Path, config_root: Path | None = None) -> ValidationReport:
    """Run all validation checks against the repo at `repo_root`.

    `config_root` is where shared configs live (CODEOWNERS, role-team-mapping,
    schemas). Defaults to `repo_root` — different in tests that build synthetic
    repos but want to reuse the canonical configs.
    """
    config_root = config_root or repo_root
    report = ValidationReport()

    co_rules = codeowners.parse(config_root / ".github" / "CODEOWNERS")
    role_map = role_team_map.load(config_root / "schemas" / "role-team-mapping.yaml")

    policies_root = repo_root / "policies"
    rule_index: dict[str, dict] = {}
    policies = list(io.iter_policies(policies_root)) if policies_root.exists() else []

    for policy in policies:
        fm.check(policy, report)
        consistency.check(policy, policies_root, DOMAIN_TO_FOLDER, report)
        tags.check(policy, report)
        approvers.check(policy, co_rules, role_map, repo_root, report)
        rules = io.load_rules(policy.path)
        if rules:
            sidecar_path = policy.path.parent / f"{policy.path.stem}.rules.yaml"
            rules_sidecar.check(sidecar_path, rules, report)
            removed_rules.check(sidecar_path, rules, report)
            # rules_sidecar.check records a finding if policy_id is missing; we still
            # want validation to continue, so guard the index build defensively rather
            # than crashing the whole run on a malformed sidecar.
            policy_id = rules.get("policy_id")
            if policy_id:
                for rule in rules.get("rules", []):
                    if isinstance(rule, dict) and "id" in rule:
                        rule_index[f"{policy_id}.{rule['id']}"] = rule

    exceptions_root = repo_root / "exceptions"
    if exceptions_root.exists():
        for exc in io.iter_exceptions(exceptions_root):
            exc_validate.check(exc, rule_index, report)

    return report
