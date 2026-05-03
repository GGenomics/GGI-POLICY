import sys

import click


@click.group()
@click.version_option()
def main() -> None:
    """GGI policy documentation framework tooling."""


@main.command()
def validate() -> None:
    """Validate every policy, sidecar, and exception in the repo."""
    click.echo("validate: not yet implemented")
    sys.exit(0)


if __name__ == "__main__":
    main()
