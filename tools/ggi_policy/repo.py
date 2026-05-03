from functools import cache
from pathlib import Path
import subprocess


@cache
def repo_root() -> Path:
    """Return the absolute path to the repo's git root."""
    out = subprocess.check_output(["git", "rev-parse", "--show-toplevel"], text=True)
    return Path(out.strip()).resolve()
