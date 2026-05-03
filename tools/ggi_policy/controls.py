"""Read/write the canonical framework-controls catalog."""

import json
from pathlib import Path

from ggi_policy.fetchers._models import FrameworkData


def save(per_framework: dict[str, FrameworkData], path: Path) -> None:
    """Write the merged catalog to `path`. Overwrites existing content."""
    payload = {"frameworks": {name: fd.to_json() for name, fd in per_framework.items()}}
    path.write_text(json.dumps(payload, indent=2, sort_keys=False) + "\n")


def load(path: Path) -> dict:
    """Read and return the catalog as a dict (validate against the schema upstream)."""
    return json.loads(path.read_text())


def ids_for(framework: str, catalog: dict) -> set[str]:
    """Return the set of control IDs known for `framework` in the catalog."""
    framework_data = catalog.get("frameworks", {}).get(framework)
    if not framework_data:
        return set()
    return {c["id"] for c in framework_data.get("controls", [])}
