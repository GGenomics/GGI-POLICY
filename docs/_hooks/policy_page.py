"""MkDocs hook that turns a policy's YAML frontmatter into a top metadata strip
and a bottom 'Framework alignment' table."""

from __future__ import annotations

import re

import yaml


_FRONTMATTER_RE = re.compile(r"\A---\n(.*?)\n---\n", re.DOTALL)

_FRAMEWORK_LABELS = {
    "nist_csf":     ("NIST CSF 2.0",          "crosswalks/nist-csf.md"),
    "cis":          ("CIS Controls v8",       "crosswalks/cis.md"),
    "soc2":         ("SOC 2 TSC",             "crosswalks/soc2.md"),
    "hipaa":        ("HIPAA 45 CFR Part 164", "crosswalks/hipaa.md"),
    "nist_800_53":  ("NIST 800-53 Rev 5",     "crosswalks/nist-800-53.md"),
    "nist_800_171": ("NIST 800-171 Rev 3",    "crosswalks/nist-800-171.md"),
}


def _depth_to_root(page_path: str) -> str:
    """`policies/identity-and-access/group-naming.md` → `../../`."""
    parts = page_path.split("/")
    return "../" * (len(parts) - 1)


def _render_meta_strip(meta: dict) -> str:
    pid = meta.get("id", "")
    version = meta.get("version", "")
    status = meta.get("status", "")
    owner = meta.get("owner", "")
    eff = meta.get("effective_date", "")
    reviewed = meta.get("last_reviewed", "")
    cycle = meta.get("review_cycle", "")
    return (
        f'!!! info "{pid} · v{version} · {status}"\n'
        f"    **Owner:** {owner}  · **Effective:** {eff}  · "
        f"**Last reviewed:** {reviewed}  · **Review cycle:** {cycle}\n"
    )


def _render_framework_table(meta: dict, page_path: str) -> str:
    frameworks = meta.get("frameworks") or {}
    rows = []
    prefix = _depth_to_root(page_path)
    for key, (label, target) in _FRAMEWORK_LABELS.items():
        ids = frameworks.get(key) or []
        if not ids:
            continue
        cell = ", ".join(f"[`{cid}`]({prefix}{target})" for cid in ids)
        rows.append(f"| {label} | {cell} |")
    if not rows:
        return ""
    return (
        "## Framework alignment\n\n"
        "| Framework | Controls |\n"
        "|---|---|\n"
        + "\n".join(rows)
        + "\n"
    )


def transform(markdown: str, page_path: str) -> str:
    """Return the markdown with frontmatter stripped, a metadata strip prepended,
    and a Framework alignment table appended. Non-policy pages pass through."""
    m = _FRONTMATTER_RE.match(markdown)
    if not m:
        return markdown
    try:
        meta = yaml.safe_load(m.group(1)) or {}
    except yaml.YAMLError:
        return markdown
    if not isinstance(meta, dict) or not str(meta.get("id", "")).startswith("POL-"):
        return markdown
    body = markdown[m.end():].lstrip("\n")
    meta_strip = _render_meta_strip(meta)
    framework_table = _render_framework_table(meta, page_path)
    return f"{meta_strip}\n{body.rstrip()}\n\n{framework_table}".rstrip() + "\n"


def on_page_markdown(markdown: str, *, page=None, **kwargs) -> str:
    if page is None:
        return markdown
    return transform(markdown, page.file.src_path)
