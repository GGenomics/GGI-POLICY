import json
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


def test_fetch_controls_writes_catalog(fixtures_dir: Path, tmp_path: Path, monkeypatch) -> None:
    """The fetch-controls subcommand writes a framework-controls.json that
    validates against the schema. We monkeypatch the network-bound fetchers to
    return their canned fixtures so the test stays offline."""
    from datetime import date

    from ggi_policy.fetchers import nist_csf, hipaa, nist_800_53, nist_800_171

    real = fixtures_dir.parent.parent.parent

    def _make_patch(module, fixture_name):
        text = (fixtures_dir / "fetchers" / fixture_name).read_text()
        return lambda *, fetched_at=None: module.fetch_from_text(
            text, fetched_at=fetched_at or date(2026, 5, 2)
        )

    monkeypatch.setattr(nist_csf, "fetch", _make_patch(nist_csf, "nist_csf.oscal.json"))
    monkeypatch.setattr(nist_800_53, "fetch", _make_patch(nist_800_53, "nist_800_53.oscal.json"))
    monkeypatch.setattr(nist_800_171, "fetch", _make_patch(nist_800_171, "nist_800_171.oscal.json"))
    monkeypatch.setattr(hipaa, "fetch", _make_patch(hipaa, "hipaa.ecfr.json"))

    out = tmp_path / "fc.json"

    runner = CliRunner()
    result = runner.invoke(main, ["fetch-controls", "--output", str(out)])
    assert result.exit_code == 0, result.output

    payload = json.loads(out.read_text())
    assert set(payload["frameworks"].keys()) == {
        "nist_csf", "cis", "soc2", "hipaa", "nist_800_53", "nist_800_171"
    }
    assert any(c["id"] == "PR.AC-01" for c in payload["frameworks"]["nist_csf"]["controls"])
    assert any(c["id"] == "5.4" for c in payload["frameworks"]["cis"]["controls"])


def test_build_site_invokes_mkdocs(monkeypatch, tmp_path: Path) -> None:
    """The build-site subcommand calls site.build with the right args; it does
    not actually invoke mkdocs in tests (we monkeypatch site.build)."""
    from ggi_policy import site

    captured = {}

    def fake_build(repo_root, *, strict):
        captured["repo_root"] = repo_root
        captured["strict"] = strict
        return 0

    monkeypatch.setattr(site, "build", fake_build)
    runner = CliRunner()
    result = runner.invoke(main, ["build-site", "--repo-root", str(tmp_path)])
    assert result.exit_code == 0, result.output
    assert "OK" in result.output
    assert captured["repo_root"] == tmp_path.resolve()
    assert captured["strict"] is True


def test_build_site_propagates_failure(monkeypatch, tmp_path: Path) -> None:
    from ggi_policy import site

    monkeypatch.setattr(site, "build", lambda repo_root, *, strict: 1)
    runner = CliRunner()
    result = runner.invoke(main, ["build-site", "--repo-root", str(tmp_path)])
    assert result.exit_code == 1
    assert "FAIL" in result.output


def test_check_reviews_dry_run_outputs_titles(fixtures_dir: Path) -> None:
    """The fixture's sample.md is overdue on 2026-05-15. --dry-run prints a
    'would create issue' line and exits 0."""
    runner = CliRunner()
    result = runner.invoke(main, [
        "check-reviews",
        "--repo-root", str(fixtures_dir / "lifecycle"),
        "--today", "2026-05-15",
        "--dry-run",
    ])
    assert result.exit_code == 0, result.output
    assert "[dry-run] would create issue: Review Due: POL-IAM-SAMPLE" in result.output


def test_check_reviews_clean_when_nothing_overdue(fixtures_dir: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(main, [
        "check-reviews",
        "--repo-root", str(fixtures_dir / "lifecycle"),
        "--today", "2026-04-30",
        "--dry-run",
    ])
    assert result.exit_code == 0
    assert "OK: no overdue reviews" in result.output


def test_notify_effective_dry_run(fixtures_dir: Path) -> None:
    """Sample fixture has effective_date 2026-06-01."""
    runner = CliRunner()
    result = runner.invoke(main, [
        "notify-effective",
        "--repo-root", str(fixtures_dir / "lifecycle"),
        "--today", "2026-06-01",
        "--dry-run",
    ])
    assert result.exit_code == 0, result.output
    assert "[dry-run] would post" in result.output
    assert "POL-IAM-SAMPLE" in result.output


def test_notify_effective_skipped_without_webhook(fixtures_dir: Path) -> None:
    """No webhook URL, not dry-run: log and exit 0 (no traceback)."""
    runner = CliRunner()
    result = runner.invoke(main, [
        "notify-effective",
        "--repo-root", str(fixtures_dir / "lifecycle"),
        "--today", "2026-06-01",
    ], env={"TEAMS_POLICY_WEBHOOK": ""})
    assert result.exit_code == 0
    assert "skipped" in result.output


def test_notify_effective_clean_when_no_match(fixtures_dir: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(main, [
        "notify-effective",
        "--repo-root", str(fixtures_dir / "lifecycle"),
        "--today", "2026-06-02",
        "--dry-run",
    ])
    assert result.exit_code == 0
    assert "no policies become effective" in result.output


def test_check_exceptions_at_30_day_milestone(fixtures_dir: Path) -> None:
    """Sample exception expires 2026-10-15. On 2026-09-15 it's the 30-day milestone."""
    runner = CliRunner()
    result = runner.invoke(main, [
        "check-exceptions",
        "--repo-root", str(fixtures_dir / "lifecycle"),
        "--today", "2026-09-15",
        "--dry-run",
    ])
    assert result.exit_code == 0, result.output
    assert "expiring in 30 day(s)" in result.output
    assert "EXC-2026-001-SAMPLE" in result.output


def test_check_exceptions_after_expiry(fixtures_dir: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(main, [
        "check-exceptions",
        "--repo-root", str(fixtures_dir / "lifecycle"),
        "--today", "2026-10-16",
        "--dry-run",
    ])
    assert result.exit_code == 0, result.output
    assert "EXPIRED" in result.output


def test_check_exceptions_silent_on_non_milestone_day(fixtures_dir: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(main, [
        "check-exceptions",
        "--repo-root", str(fixtures_dir / "lifecycle"),
        "--today", "2026-09-16",
        "--dry-run",
    ])
    assert result.exit_code == 0
    assert "no exception notifications" in result.output
