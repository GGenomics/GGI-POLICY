"""Thin wrapper around `mkdocs build`."""

import subprocess
from pathlib import Path


def build(repo_root: Path, *, strict: bool = True) -> int:
    """Run `mkdocs build` from `repo_root`. Returns the subprocess exit code.

    `strict=True` makes warnings (broken links, unrecognized config) fatal.
    """
    cmd = ["uv", "run", "mkdocs", "build"]
    if strict:
        cmd.append("--strict")
    return subprocess.call(cmd, cwd=repo_root)
