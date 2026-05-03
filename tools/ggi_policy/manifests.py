"""Structural validation for the deploy/ kustomize tree.

Scope: every YAML doc under deploy/ must have apiVersion + kind. Image
references in policy-docs Deployments must point at the canonical GHCR
repo. Ingress hostnames must match the canonical public hostname.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterator

import yaml


CANONICAL_IMAGE_REPO = "ghcr.io/ggenomics/ggi-policy-site"
CANONICAL_HOSTNAME = "policy.ggenomics.internal"


def iter_documents(deploy_root: Path) -> Iterator[tuple[Path, dict]]:
    """Yield (file_path, doc_dict) for every YAML document under deploy/."""
    for yaml_file in sorted(deploy_root.rglob("*.yaml")):
        with yaml_file.open() as f:
            for doc in yaml.safe_load_all(f):
                if doc is None:
                    continue
                yield yaml_file, doc


def validate(deploy_root: Path) -> list[str]:
    """Return a list of error messages, empty list if all manifests are valid."""
    errors: list[str] = []
    saw_canonical_image = False
    saw_canonical_host = False

    for path, doc in iter_documents(deploy_root):
        if not isinstance(doc, dict):
            errors.append(f"{path}: top-level YAML document is not a mapping")
            continue
        kind = doc.get("kind")
        if not kind:
            errors.append(f"{path}: missing 'kind'")
        if not doc.get("apiVersion"):
            errors.append(f"{path}: missing 'apiVersion'")

        if kind == "Deployment":
            for container in (
                doc.get("spec", {}).get("template", {}).get("spec", {}).get("containers", [])
            ):
                image = container.get("image", "")
                if image.startswith(CANONICAL_IMAGE_REPO + ":"):
                    saw_canonical_image = True
                elif "ggi-policy-site" in image and not image.startswith(CANONICAL_IMAGE_REPO):
                    errors.append(
                        f"{path}: container image {image!r} should reference {CANONICAL_IMAGE_REPO}"
                    )

        if kind == "Ingress":
            for tls in doc.get("spec", {}).get("tls", []) or []:
                for host in tls.get("hosts", []) or []:
                    if host != CANONICAL_HOSTNAME:
                        errors.append(
                            f"{path}: TLS host {host!r} should be {CANONICAL_HOSTNAME!r}"
                        )
                    else:
                        saw_canonical_host = True
            for rule in doc.get("spec", {}).get("rules", []) or []:
                host = rule.get("host", "")
                if host and host != CANONICAL_HOSTNAME:
                    errors.append(
                        f"{path}: rule host {host!r} should be {CANONICAL_HOSTNAME!r}"
                    )

    if not saw_canonical_image:
        errors.append(
            f"no Deployment references the canonical image {CANONICAL_IMAGE_REPO!r}"
        )
    if not saw_canonical_host:
        errors.append(
            f"no Ingress references the canonical host {CANONICAL_HOSTNAME!r}"
        )

    return errors
