from pathlib import Path

import yaml


def load(path: Path) -> dict[str, str]:
    # yaml.safe_load returns None for an empty / comments-only document; coalesce to {}
    # so callers reading a placeholder file don't see an AttributeError.
    data = yaml.safe_load(path.read_text()) or {}
    return dict(data.get("roles", {}))
