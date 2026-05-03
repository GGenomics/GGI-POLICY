from pathlib import Path

from click.testing import CliRunner

from ggi_policy.cli import main


def test_validate_succeeds_on_valid_fixture(fixtures_dir: Path, tmp_path: Path) -> None:
    # Build a synthetic repo that bundles the valid policy + all required config files.
    # The plan's original test passed `--repo-root fixtures_dir/"valid"` directly, but
    # that tree has no .github/CODEOWNERS or schemas/role-team-mapping.yaml, which the
    # runner requires (config_root defaults to repo_root in the CLI).  The fix is to
    # mirror the pattern used by the second CLI test: copy configs alongside the policy.
    repo = tmp_path / "synth"
    (repo / "policies/identity-and-access").mkdir(parents=True)
    (repo / "schemas").mkdir()
    (repo / ".github").mkdir()

    real = fixtures_dir.parent.parent.parent
    for name in ["policy-frontmatter.schema.json", "policy-rules.schema.json",
                 "exception.schema.json", "role-team-mapping.schema.json",
                 "role-team-mapping.yaml"]:
        (repo / "schemas" / name).write_text((real / "schemas" / name).read_text())
    (repo / ".github/CODEOWNERS").write_text((real / ".github/CODEOWNERS").read_text())
    (repo / "policies/identity-and-access/group-naming.md").write_text(
        (fixtures_dir / "valid/policies/identity-and-access/group-naming.md").read_text()
    )
    (repo / "policies/identity-and-access/group-naming.rules.yaml").write_text(
        (fixtures_dir / "valid/policies/identity-and-access/group-naming.rules.yaml").read_text()
    )

    runner = CliRunner()
    result = runner.invoke(main, ["validate", "--repo-root", str(repo)])
    assert result.exit_code == 0, result.output
    assert "OK" in result.output


def test_validate_fails_loudly_on_invalid(fixtures_dir: Path, tmp_path: Path) -> None:
    # Build a synthetic repo with one bad policy + necessary configs.
    repo = tmp_path / "synth"
    (repo / "policies/identity-and-access").mkdir(parents=True)
    (repo / "schemas").mkdir()
    (repo / ".github").mkdir()

    real = fixtures_dir.parent.parent.parent
    for name in ["policy-frontmatter.schema.json", "policy-rules.schema.json",
                 "exception.schema.json", "role-team-mapping.schema.json",
                 "role-team-mapping.yaml"]:
        (repo / "schemas" / name).write_text((real / "schemas" / name).read_text())
    (repo / ".github/CODEOWNERS").write_text((real / ".github/CODEOWNERS").read_text())
    (repo / "policies/identity-and-access/missing-id.md").write_text(
        (fixtures_dir / "invalid/frontmatter/missing-id.md").read_text()
    )

    runner = CliRunner()
    result = runner.invoke(main, ["validate", "--repo-root", str(repo)])
    assert result.exit_code == 1
    assert "FAIL" in result.output
