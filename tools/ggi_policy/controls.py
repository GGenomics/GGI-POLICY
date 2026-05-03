"""Read/write the canonical framework-controls catalog."""

import json
from functools import cache
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

from ggi_policy.fetchers._models import FrameworkData


@cache
def _catalog_validator(schema_path: Path) -> Draft202012Validator:
    return Draft202012Validator(json.loads(schema_path.read_text()), format_checker=FormatChecker())


def validate(catalog: dict, schema_path: Path) -> list[str]:
    """Return a list of human-readable validation error messages, empty if valid."""
    return [
        f"{'/'.join(str(p) for p in err.absolute_path) or '(root)'}: {err.message}"
        for err in _catalog_validator(schema_path).iter_errors(catalog)
    ]


def save(per_framework: dict[str, FrameworkData], path: Path) -> None:
    """Write the merged catalog to `path`. Overwrites existing content.

    Frameworks appear in REGISTRY order (insertion-stable for Python 3.7+).
    Within each framework, controls are sorted by id so refresh PRs produce
    reviewable diffs even when an upstream fetcher re-orders entries.
    """
    out_frameworks: dict[str, dict] = {}
    for name, fd in per_framework.items():
        framework_json = fd.to_json()
        framework_json["controls"] = sorted(framework_json["controls"], key=lambda c: c["id"])
        out_frameworks[name] = framework_json
    payload = {"frameworks": out_frameworks}
    path.write_text(json.dumps(payload, indent=2, sort_keys=False) + "\n")


def load(path: Path, *, validate_schema: bool = False) -> dict:
    """Read and return the catalog as a dict.

    When `validate_schema` is True, the catalog is validated against
    `<sibling>/framework-controls.schema.json` and a ValueError is raised
    on any failure. The runner's hot path leaves this off for speed.
    """
    catalog = json.loads(path.read_text())
    if validate_schema:
        schema_path = path.parent / "framework-controls.schema.json"
        errors = validate(catalog, schema_path)
        if errors:
            joined = "\n  ".join(errors[:10])
            raise ValueError(f"framework-controls.json failed schema validation:\n  {joined}")
    return catalog


def ids_for(framework: str, catalog: dict) -> set[str]:
    """Return the set of control IDs known for `framework` in the catalog."""
    framework_data = catalog.get("frameworks", {}).get(framework)
    if not framework_data:
        return set()
    return {c["id"] for c in framework_data.get("controls", [])}
