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


if __name__ == "__main__":
    main()
