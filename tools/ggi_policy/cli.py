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
    root = repo_root_opt or repo_root()
    report = run(repo_root=root, config_root=root)
    if report.ok:
        click.echo(f"OK: validated {root}")
        sys.exit(0)
    for finding in report.findings:
        rel = finding.path.relative_to(root) if finding.path.is_absolute() else finding.path
        click.echo(f"{rel}: [{finding.code}] {finding.message}", err=True)
    click.echo(f"\nFAIL: {len(report.findings)} finding(s)", err=True)
    sys.exit(1)


if __name__ == "__main__":
    main()
