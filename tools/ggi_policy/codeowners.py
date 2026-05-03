from pathlib import Path
from typing import Iterable


def parse(path: Path) -> list[tuple[str, list[str]]]:
    rules: list[tuple[str, list[str]]] = []
    for raw in path.read_text().splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        parts = line.split()
        if len(parts) < 2:
            continue
        rules.append((parts[0], parts[1:]))
    return rules


def owners_for(repo_relative_path: str, rules: Iterable[tuple[str, list[str]]]) -> list[str]:
    """Return the owners for the longest matching path-prefix rule, or [] if none matches."""
    best: tuple[int, list[str]] = (-1, [])
    for pattern, owners in rules:
        prefix = pattern.lstrip("/")
        if repo_relative_path.startswith(prefix) and len(prefix) > best[0]:
            best = (len(prefix), owners)
    return best[1]
