from pathlib import Path

import yaml


def load(path: Path) -> dict[str, str]:
    data = yaml.safe_load(path.read_text())
    return dict(data.get("roles", {}))
