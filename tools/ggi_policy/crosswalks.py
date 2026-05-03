"""Generate the marker regions in crosswalks/<framework>.md files."""

import re
from pathlib import Path
from typing import Iterable


_TABLE_MARKER = "crosswalk-table"
_GAPS_MARKER = "crosswalk-gaps"


def build_coverage(policies: Iterable[dict], *, framework: str) -> dict[str, list[str]]:
    """Build {control_id: sorted([policy_id, ...])} for one framework, from a sequence of policy
    metadata dicts. Each policy dict must have an `id` key and a `frameworks` mapping."""
    out: dict[str, set[str]] = {}
    for policy in policies:
        ids = (policy.get("frameworks") or {}).get(framework, []) or []
        pid = policy.get("id")
        if not pid:
            continue
        for control_id in ids:
            out.setdefault(control_id, set()).add(pid)
    return {k: sorted(v) for k, v in out.items()}


def _render_table(framework: str, catalog: dict, coverage: dict[str, list[str]]) -> str:
    rows = ["| Control | Title | Policies |", "|---|---|---|"]
    fw = catalog.get("frameworks", {}).get(framework, {})
    for control in fw.get("controls", []):
        cid = control["id"]
        title = control.get("title", "")
        policies = coverage.get(cid, [])
        cell = ", ".join(policies) if policies else "_(no policy)_"
        rows.append(f"| {cid} | {title} | {cell} |")
    return "\n".join(rows)


def _render_gaps(framework: str, catalog: dict, coverage: dict[str, list[str]]) -> str:
    fw = catalog.get("frameworks", {}).get(framework, {})
    lines = []
    for control in fw.get("controls", []):
        if control["id"] not in coverage:
            lines.append(f"- {control['id']} — {control.get('title', '')}")
    return "\n".join(lines)


def _replace_region(text: str, marker_kind: str, framework: str, body: str) -> str:
    pattern = re.compile(
        rf"(<!-- BEGIN: {re.escape(marker_kind)} {re.escape(framework)} -->)"
        rf".*?"
        rf"(<!-- END: {re.escape(marker_kind)} {re.escape(framework)} -->)",
        flags=re.DOTALL,
    )
    replacement = rf"\1\n{body}\n\2" if body else rf"\1\n\2"
    return pattern.sub(replacement, text)


def render(source_text: str, framework: str, catalog: dict, coverage: dict[str, list[str]]) -> str:
    text = _replace_region(source_text, _TABLE_MARKER, framework,
                            _render_table(framework, catalog, coverage))
    text = _replace_region(text, _GAPS_MARKER, framework,
                            _render_gaps(framework, catalog, coverage))
    return text


def build_all(repo_root: Path, *, check: bool = False) -> tuple[bool, list[str]]:
    """Regenerate every crosswalks/<framework>.md file. Returns (ok, list of paths that
    would change). When `check` is True, no files are written."""
    from ggi_policy import controls as controls_io, io as policy_io

    catalog = controls_io.load(repo_root / "schemas" / "framework-controls.json")
    policies_root = repo_root / "policies"
    raw_policies = []
    if policies_root.exists():
        for policy in policy_io.iter_policies(policies_root):
            raw_policies.append(policy.metadata)

    framework_to_file = {
        "nist_csf":     "nist-csf.md",
        "cis":          "cis.md",
        "soc2":         "soc2.md",
        "hipaa":        "hipaa.md",
        "nist_800_53":  "nist-800-53.md",
        "nist_800_171": "nist-800-171.md",
    }

    changed: list[str] = []
    for framework, filename in framework_to_file.items():
        target = repo_root / "crosswalks" / filename
        if not target.exists():
            changed.append(str(target.relative_to(repo_root)))
            continue
        coverage = build_coverage(raw_policies, framework=framework)
        rendered = render(target.read_text(), framework, catalog, coverage)
        if rendered != target.read_text():
            changed.append(str(target.relative_to(repo_root)))
            if not check:
                target.write_text(rendered)
    return (not changed, changed)
