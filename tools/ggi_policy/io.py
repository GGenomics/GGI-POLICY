from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

import frontmatter
import yaml


@dataclass(frozen=True)
class LoadedPolicy:
    path: Path
    metadata: dict
    body: str


@dataclass(frozen=True)
class LoadedException:
    path: Path
    metadata: dict
    body: str


def load_policy(path: Path) -> LoadedPolicy:
    post = frontmatter.load(path)
    return LoadedPolicy(path=path, metadata=dict(post.metadata), body=post.content)


def load_rules(policy_path: Path) -> dict | None:
    sidecar = policy_path.with_suffix("").with_suffix(".rules.yaml")
    # Above only strips one suffix on .md; do it explicitly:
    sidecar = policy_path.parent / f"{policy_path.stem}.rules.yaml"
    if not sidecar.exists():
        return None
    with sidecar.open() as f:
        return yaml.safe_load(f)


def load_exception(path: Path) -> LoadedException:
    post = frontmatter.load(path)
    return LoadedException(path=path, metadata=dict(post.metadata), body=post.content)


def iter_policies(root: Path) -> Iterator[LoadedPolicy]:
    for md in sorted(root.rglob("*.md")):
        if md.name.endswith(".rules.yaml"):
            continue
        yield load_policy(md)


def iter_exceptions(root: Path) -> Iterator[LoadedException]:
    for md in sorted(root.glob("EXC-*.md")):
        yield load_exception(md)
