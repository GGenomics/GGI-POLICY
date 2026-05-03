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
    """Return the owners for the longest matching path-prefix rule, or [] if none matches.

    A rule pattern matches a path if the pattern (with leading '/' stripped) is a prefix
    of the path AND the prefix ends at a path boundary — either because the pattern itself
    ends with '/', the path equals the prefix exactly, or the next character in the path
    is '/'. This prevents `/policies/data` from spuriously matching `/policies/data-governance/...`.
    """
    best: tuple[int, list[str]] = (-1, [])
    for pattern, owners in rules:
        prefix = pattern.lstrip("/")
        if not repo_relative_path.startswith(prefix):
            continue
        if not prefix.endswith("/"):
            tail = repo_relative_path[len(prefix):len(prefix) + 1]
            if tail not in ("", "/"):
                continue
        if len(prefix) > best[0]:
            best = (len(prefix), owners)
    return best[1]
