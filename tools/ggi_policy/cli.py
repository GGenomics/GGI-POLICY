import sys
from pathlib import Path

import click

from ggi_policy.repo import repo_root
from ggi_policy.validate.runner import run


@click.group()
@click.version_option()
def main() -> None:
    """GGI policy documentation framework tooling."""


@main.command()
@click.option(
    "--repo-root", "repo_root_opt",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=None,
    help="Override the repo root (defaults to git rev-parse).",
)
def validate(repo_root_opt: Path | None) -> None:
    """Validate every policy, sidecar, and exception in the repo."""
    # Resolve to an absolute path so relative_to() in finding output behaves
    # predictably regardless of where the CLI was invoked from.
    root = (repo_root_opt or repo_root()).resolve()
    report = run(repo_root=root, config_root=root)
    if report.ok:
        click.echo(f"OK: validated {root}")
        sys.exit(0)
    for finding in report.findings:
        try:
            rel = finding.path.relative_to(root) if finding.path.is_absolute() else finding.path
        except ValueError:
            # Path is absolute but lives outside root (e.g., a programmatic call
            # passed an external reference). Fall back to the absolute path so
            # the rest of the findings still render.
            rel = finding.path
        click.echo(f"{rel}: [{finding.code}] {finding.message}", err=True)
    click.echo(f"\nFAIL: {len(report.findings)} finding(s)", err=True)
    sys.exit(1)


@main.command("fetch-controls")
@click.option("--framework", "framework_filter", default=None,
              help="Refresh only the named framework (default: all).")
@click.option("--output", "output_opt", type=click.Path(path_type=Path), default=None,
              help="Write to this path (default: <repo>/schemas/framework-controls.json).")
def fetch_controls(framework_filter: str | None, output_opt: Path | None) -> None:
    """Fetch the latest framework control catalogs and write framework-controls.json."""
    from datetime import date

    from ggi_policy import controls
    from ggi_policy.fetchers import REGISTRY

    today = date.today()
    target_path = output_opt or (repo_root() / "schemas" / "framework-controls.json")

    if target_path.exists():
        existing = controls.load(target_path)
    else:
        existing = {"frameworks": {}}

    selected = ([framework_filter] if framework_filter else list(REGISTRY.keys()))
    out_per_framework = {}

    # Preserve frameworks we aren't refreshing this run.
    for name, raw in existing.get("frameworks", {}).items():
        if name not in selected:
            out_per_framework[name] = _frameworkdata_from_dict(name, raw)

    for name in selected:
        if name not in REGISTRY:
            raise click.ClickException(f"unknown framework: {name!r}")
        click.echo(f"fetching {name}...", err=True)
        out_per_framework[name] = REGISTRY[name].fetch(fetched_at=today)

    controls.save(out_per_framework, target_path)
    click.echo(f"wrote {len(out_per_framework)} framework(s) to {target_path}")


def _frameworkdata_from_dict(name: str, raw: dict):
    """Rehydrate a FrameworkData from the on-disk JSON shape (used to preserve frameworks
    we aren't refreshing this run)."""
    from datetime import date as _date

    from ggi_policy.fetchers._models import Control, FrameworkData, Metadata

    md = raw.get("metadata", {})
    return FrameworkData(
        metadata=Metadata(
            version=md.get("version", ""),
            fetched_at=_date.fromisoformat(md.get("fetched_at", _date.today().isoformat())),
            source_url=md.get("source_url", ""),
            fetcher=md.get("fetcher", name),
            notes=md.get("notes", ""),
        ),
        controls=[Control(id=c["id"], title=c["title"], description=c.get("description", ""))
                  for c in raw.get("controls", [])],
    )


@main.command("build-crosswalks")
@click.option("--check", "check_mode", is_flag=True, default=False,
              help="Exit non-zero if regeneration would change any file.")
@click.option("--repo-root", "repo_root_opt",
              type=click.Path(exists=True, file_okay=False, path_type=Path),
              default=None)
def build_crosswalks(check_mode: bool, repo_root_opt: Path | None) -> None:
    """Regenerate the marker regions inside crosswalks/<framework>.md files."""
    from ggi_policy import crosswalks as crosswalks_mod

    root = (repo_root_opt or repo_root()).resolve()
    ok, changed = crosswalks_mod.build_all(root, check=check_mode)
    if check_mode:
        if ok:
            click.echo("OK: crosswalks up to date")
            sys.exit(0)
        for path in changed:
            click.echo(path, err=True)
        click.echo(f"\nFAIL: {len(changed)} crosswalk file(s) would change. "
                   f"Run `uv run ggi-policy build-crosswalks` and commit.", err=True)
        sys.exit(1)
    if changed:
        for path in changed:
            click.echo(f"updated {path}")
    else:
        click.echo("no changes")


@main.command("build-site")
@click.option("--no-strict", is_flag=True, default=False,
              help="Disable --strict (build will not fail on broken links).")
@click.option("--repo-root", "repo_root_opt",
              type=click.Path(exists=True, file_okay=False, path_type=Path),
              default=None)
def build_site(no_strict: bool, repo_root_opt: Path | None) -> None:
    """Build the static MkDocs site into <repo>/site/."""
    from ggi_policy import site

    root = (repo_root_opt or repo_root()).resolve()
    rc = site.build(root, strict=not no_strict)
    if rc != 0:
        click.echo(f"FAIL: mkdocs build exited {rc}", err=True)
        sys.exit(rc)
    click.echo(f"OK: site built at {root / 'site'}")


@main.command("validate-deploy")
@click.option("--repo-root", "repo_root_opt",
              type=click.Path(exists=True, file_okay=False, path_type=Path),
              default=None)
def validate_deploy(repo_root_opt: Path | None) -> None:
    """Structurally validate the deploy/ kustomize tree."""
    from ggi_policy import manifests

    root = (repo_root_opt or repo_root()).resolve()
    errors = manifests.validate(root / "deploy")
    if errors:
        for e in errors:
            click.echo(e, err=True)
        click.echo(f"\nFAIL: {len(errors)} manifest issue(s)", err=True)
        sys.exit(1)
    click.echo(f"OK: deploy/ manifests valid ({root / 'deploy'})")


@main.command("check-reviews")
@click.option("--today", "today_opt", type=click.DateTime(formats=["%Y-%m-%d"]),
              default=None, help="Override today (default: actual date).")
@click.option("--dry-run", is_flag=True, default=False)
@click.option("--repo-root", "repo_root_opt",
              type=click.Path(exists=True, file_okay=False, path_type=Path),
              default=None)
def check_reviews(today_opt, dry_run: bool, repo_root_opt: Path | None) -> None:
    """List effective policies whose review_cycle has elapsed.

    The CI workflow pipes this output to `gh issue create` to file Issues.
    """
    from datetime import date as _date

    from ggi_policy import lifecycle

    root = (repo_root_opt or repo_root()).resolve()
    today = today_opt.date() if today_opt else _date.today()
    overdue = lifecycle.overdue_reviews(root / "policies", today=today)

    if not overdue:
        click.echo(f"OK: no overdue reviews on {today.isoformat()}")
        return

    for entry in overdue:
        title = f"Review Due: {entry['id']}"
        body = (
            f"Policy {entry['id']} (\"{entry['title']}\") was last reviewed "
            f"on {entry['last_reviewed']} with a {entry['review_cycle']} review cycle. "
            f"Owner: {entry['owner']}. "
            f"Open a PR that bumps last_reviewed (re-attestation)."
        )
        if dry_run:
            click.echo(f"[dry-run] would create issue: {title}")
        else:
            # Tab-separated so the workflow can `awk` cleanly.
            click.echo(f"OVERDUE\t{title}\t{entry['owner']}\t{body}")


@main.command("notify-effective")
@click.option("--today", "today_opt", type=click.DateTime(formats=["%Y-%m-%d"]),
              default=None)
@click.option("--dry-run", is_flag=True, default=False)
@click.option("--repo-root", "repo_root_opt",
              type=click.Path(exists=True, file_okay=False, path_type=Path),
              default=None)
@click.option("--webhook-url", "webhook_url_opt",
              envvar="TEAMS_POLICY_WEBHOOK", default=None,
              help="Teams incoming-webhook URL (defaults to $TEAMS_POLICY_WEBHOOK).")
def notify_effective(today_opt, dry_run: bool, repo_root_opt: Path | None,
                     webhook_url_opt: str | None) -> None:
    """Post a Teams notification for each policy whose effective_date is today."""
    from datetime import date as _date

    from ggi_policy import lifecycle, teams

    root = (repo_root_opt or repo_root()).resolve()
    today = today_opt.date() if today_opt else _date.today()
    arriving = lifecycle.effective_today(root / "policies", today=today)

    if not arriving:
        click.echo(f"OK: no policies become effective on {today.isoformat()}")
        return

    if not webhook_url_opt and not dry_run:
        click.echo("skipped: TEAMS_POLICY_WEBHOOK not set", err=True)
        return

    failures = 0
    for entry in arriving:
        title = f"Policy now effective: {entry['id']}"
        body = (
            f"**{entry['title']}** (v{entry['version']}) is effective as of "
            f"{entry['effective_date']}. Owner: {entry['owner']}."
        )
        if dry_run:
            click.echo(f"[dry-run] would post: {title} | {body}")
            continue
        try:
            teams.post_card(webhook_url_opt, title=title, body=body)
            click.echo(f"posted: {title}")
        except Exception as e:  # network blip, 5xx, etc.
            failures += 1
            click.echo(f"failed-to-post: {entry['id']}: {e}", err=True)
    # Best-effort: only fail if EVERY post failed (signals a config bug,
    # not a transient outage). At-most-once delivery semantics are
    # acceptable for these notifications.
    if failures and failures == len(arriving):
        sys.exit(1)


@main.command("check-exceptions")
@click.option("--today", "today_opt", type=click.DateTime(formats=["%Y-%m-%d"]),
              default=None)
@click.option("--dry-run", is_flag=True, default=False)
@click.option("--repo-root", "repo_root_opt",
              type=click.Path(exists=True, file_okay=False, path_type=Path),
              default=None)
@click.option("--webhook-url", "webhook_url_opt",
              envvar="TEAMS_POLICY_WEBHOOK", default=None)
def check_exceptions(today_opt, dry_run: bool, repo_root_opt: Path | None,
                     webhook_url_opt: str | None) -> None:
    """Post a Teams notification for active exceptions hitting an expiration milestone."""
    from datetime import date as _date

    from ggi_policy import lifecycle, teams

    root = (repo_root_opt or repo_root()).resolve()
    today = today_opt.date() if today_opt else _date.today()
    notices = lifecycle.expiring_exceptions(root / "exceptions", today=today)

    if not notices:
        click.echo(f"OK: no exception notifications for {today.isoformat()}")
        return

    if not webhook_url_opt and not dry_run:
        click.echo("skipped: TEAMS_POLICY_WEBHOOK not set", err=True)
        return

    failures = 0
    for n in notices:
        if n["expired"]:
            title = f"Exception EXPIRED: {n['id']}"
            body = (
                f"Cites {n['policy_ref']}. Approver: {n['approver']}. "
                f"Expired on {n['expires']} ({-n['days_until_expiry']} day(s) ago). "
                f"This exception must be renewed via PR or revoked."
            )
        else:
            title = f"Exception expiring in {n['days_until_expiry']} day(s): {n['id']}"
            body = (
                f"Cites {n['policy_ref']}. Approver: {n['approver']}. "
                f"Expires on {n['expires']}."
            )
        if dry_run:
            click.echo(f"[dry-run] would post: {title} | {body}")
            continue
        try:
            teams.post_card(webhook_url_opt, title=title, body=body)
            click.echo(f"posted: {title}")
        except Exception as e:
            failures += 1
            click.echo(f"failed-to-post: {n['id']}: {e}", err=True)
    if failures and failures == len(notices):
        sys.exit(1)


if __name__ == "__main__":
    main()
