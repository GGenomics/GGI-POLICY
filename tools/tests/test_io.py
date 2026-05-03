from pathlib import Path

import pytest

from ggi_policy import io


def test_load_policy_returns_frontmatter_and_body(fixtures_dir: Path) -> None:
    path = fixtures_dir / "valid/policies/identity-and-access/group-naming.md"
    policy = io.load_policy(path)
    assert policy.path == path
    assert policy.metadata["id"] == "POL-IAM-GROUP-NAMING"
    assert policy.metadata["domain"] == "IAM"
    assert "## Purpose" in policy.body


def test_load_rules_returns_dict_when_sidecar_exists(fixtures_dir: Path) -> None:
    policy_path = fixtures_dir / "valid/policies/identity-and-access/group-naming.md"
    rules = io.load_rules(policy_path)
    assert rules is not None
    assert rules["policy_id"] == "POL-IAM-GROUP-NAMING"
    assert len(rules["rules"]) == 3


def test_load_rules_returns_none_when_no_sidecar(fixtures_dir: Path, tmp_path: Path) -> None:
    orphan = tmp_path / "orphan.md"
    orphan.write_text("---\nid: POL-IAM-X\n---\n")
    assert io.load_rules(orphan) is None


def test_load_exception(fixtures_dir: Path) -> None:
    path = fixtures_dir / "valid/exceptions/EXC-2026-001-finance-legacy-group.md"
    exc = io.load_exception(path)
    assert exc.path == path
    assert exc.metadata["id"] == "EXC-2026-001-FINANCE-LEGACY-GROUP"
    assert exc.metadata["policy_ref"] == "POL-IAM-GROUP-NAMING.R1"


def test_iter_policies_walks_subtree(fixtures_dir: Path) -> None:
    policies = list(io.iter_policies(fixtures_dir / "valid/policies"))
    assert len(policies) == 1
    assert policies[0].metadata["id"] == "POL-IAM-GROUP-NAMING"


def test_iter_exceptions_walks_directory(fixtures_dir: Path) -> None:
    excs = list(io.iter_exceptions(fixtures_dir / "valid/exceptions"))
    assert len(excs) == 1
    assert excs[0].metadata["id"] == "EXC-2026-001-FINANCE-LEGACY-GROUP"
