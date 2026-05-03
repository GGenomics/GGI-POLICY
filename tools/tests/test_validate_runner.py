from pathlib import Path

from ggi_policy.validate import runner


def test_runner_on_valid_fixture_tree_yields_no_findings(fixtures_dir: Path) -> None:
    report = runner.run(repo_root=fixtures_dir / "valid", config_root=fixtures_dir.parent.parent.parent)
    # config_root points at the actual repo so CODEOWNERS / role-team-mapping are real.
    assert report.ok, [f.message for f in report.findings]


def test_runner_collects_findings_from_invalid_subset(fixtures_dir: Path, tmp_path: Path) -> None:
    # Build a small synthetic repo combining valid policies + one invalid frontmatter.
    repo = tmp_path / "synth"
    (repo / "policies/identity-and-access").mkdir(parents=True)
    (repo / "exceptions").mkdir()
    (repo / "schemas").mkdir()
    (repo / ".github").mkdir()

    valid_policy = (fixtures_dir / "valid/policies/identity-and-access/group-naming.md").read_text()
    invalid_policy = (fixtures_dir / "invalid/frontmatter/missing-id.md").read_text()
    (repo / "policies/identity-and-access/group-naming.md").write_text(valid_policy)
    (repo / "policies/identity-and-access/missing-id.md").write_text(invalid_policy)

    # Copy through the repo's real schemas + CODEOWNERS + role-team-mapping
    real = fixtures_dir.parent.parent.parent
    for name in ["policy-frontmatter.schema.json", "policy-rules.schema.json",
                 "exception.schema.json", "role-team-mapping.schema.json",
                 "role-team-mapping.yaml"]:
        (repo / "schemas" / name).write_text((real / "schemas" / name).read_text())
    (repo / ".github/CODEOWNERS").write_text((real / ".github/CODEOWNERS").read_text())

    report = runner.run(repo_root=repo, config_root=real)
    assert not report.ok
    codes = {f.code for f in report.findings}
    assert "FRONTMATTER_INVALID" in codes
