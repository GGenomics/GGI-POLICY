"""Shared parser for OSCAL JSON catalogs (NIST CSF, 800-53, 800-171)."""

from typing import Iterator


def iter_controls(groups: list[dict]) -> Iterator[dict]:
    """Yield every control object reachable from a list of OSCAL groups, recursing nested groups."""
    for group in groups or []:
        for control in group.get("controls", []) or []:
            yield control
            # Also recurse into a control's own nested controls (enhancements).
            for sub in control.get("controls", []) or []:
                yield sub
        nested = group.get("groups", [])
        if nested:
            yield from iter_controls(nested)


def parse_catalog(payload: dict) -> tuple[str, str, list[dict]]:
    """Return (title, version, [control...]) extracted from an OSCAL catalog document."""
    catalog = payload.get("catalog", {})
    metadata = catalog.get("metadata", {})
    title = metadata.get("title", "")
    version = metadata.get("version", "")
    controls = list(iter_controls(catalog.get("groups", [])))
    return title, version, controls
