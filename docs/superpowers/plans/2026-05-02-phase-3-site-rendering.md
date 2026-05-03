# Phase 3: Site rendering and image publishing — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Render the policy library to a static MkDocs Material site, package it into a small nginx container, and push versioned images to GHCR on every push to `main`.

**Architecture:** MkDocs builds the existing repo content (`policies/`, `crosswalks/`, `glossary/`, plus a generated home page) into a static site under `site/`. A custom MkDocs hook reads each policy page's YAML frontmatter and appends a "Framework alignment" table at the bottom plus a metadata strip at the top, both with clickable links into the per-framework crosswalk pages. A new `ggi-policy build-site` subcommand wraps `mkdocs build --strict`. A `Dockerfile` produces an `nginx:alpine`-based image that serves `site/`. A new GitHub Actions workflow builds and pushes the image to `ghcr.io/ggenomics/ggi-policy-site` on every push to `main`.

**Tech Stack:** MkDocs 1.5+, MkDocs Material 9.5+, `mkdocs-awesome-pages-plugin` for auto-nav, Python 3.12+ (`uv`-managed), Docker (`nginx:alpine` base), GitHub Container Registry, GitHub Actions. **No** k8s deployment — that is Phase 4.

---

## Prerequisites

- Phase 2 is merged (HEAD on `origin/main` ≥ `0359b6f`). 72 unit tests pass; `framework-controls.json` has 2,344 controls; `crosswalks/*.md` are populated and idempotent.
- Reference: design doc at [docs/superpowers/specs/2026-05-02-policy-doc-framework-design.md](../specs/2026-05-02-policy-doc-framework-design.md) §8.4 (site hosting), §6.5 (reverse direction crosswalk), §3 (decisions table — Publishing).
- No external systems must be live for Phase 3. Phase 4 will require: Entra app registration, DNS for `policy.ggenomics.internal`, ingress/oauth2-proxy in k8s, Flux image automation watching GHCR. Phase 3 stops at "image is in GHCR."
- The Phase 2 final review noted three carry-forward items the Phase 3 work should keep in mind:
  1. HIPAA XML parser is untested. Don't change it in this phase.
  2. Per-policy framework table (§6.5) is the framework-table hook in this plan.
  3. Catalog should be sorted deterministically on save — defer to a later cleanup; Phase 3 doesn't change `controls.save`.

## File structure (locked-in decomposition)

```
GGI-POLICY/
├── pyproject.toml                             # MODIFY: add mkdocs deps to dev group
├── mkdocs.yml                                 # NEW: site config
├── Dockerfile                                 # NEW: FROM nginx:alpine; COPY site/
├── .dockerignore                              # NEW
│
├── docs/
│   ├── index.md                               # NEW: site home; brief orientation
│   ├── _hooks/
│   │   └── policy_page.py                     # NEW: per-policy frontmatter -> meta strip + framework table
│   └── _stylesheets/
│       └── extra.css                          # NEW: small overrides (table density, code block tweaks)
│
├── policies/
│   ├── .pages                                 # NEW: awesome-pages nav title
│   ├── identity-and-access/.pages             # NEW: human-readable section title
│   ├── data/.pages
│   ├── privacy/.pages
│   ├── applications/.pages
│   ├── endpoints/.pages
│   ├── network/.pages
│   ├── incident-response/.pages
│   ├── vendor-and-third-party/.pages
│   ├── security-operations/.pages
│   ├── business-continuity/.pages
│   ├── human-resources/.pages
│   └── meta/.pages
│
├── crosswalks/.pages                          # NEW
├── glossary/.pages                            # NEW
│
├── tools/
│   ├── ggi_policy/
│   │   ├── cli.py                             # MODIFY: add `build-site` subcommand
│   │   └── site.py                            # NEW: thin wrapper around `mkdocs build`
│   └── tests/
│       ├── test_site_hooks.py                 # NEW
│       └── test_cli.py                        # MODIFY: add build-site CLI test
│
└── .github/workflows/
    ├── validate.yml                           # untouched
    └── build-and-push.yml                     # NEW: build site, build image, push to GHCR
```

## Conventions

- **Commits:** Conventional Commits (`feat(site): ...`, `feat(docker): ...`, `ci(image): ...`).
- **TDD:** the policy-page hook gets paired tests against fixture markdown; the `build-site` command gets a smoke test that runs `mkdocs build --strict` against the live tree.
- **Hook placement:** all MkDocs hooks live under `docs/_hooks/`. The leading underscore keeps them out of the navigation while they remain Markdown-or-Python-like to MkDocs.
- **Awesome-pages convention:** every directory we want to appear in the nav has a `.pages` file with at minimum `title:` set; that file is *not* rendered.
- **No new runtime deps in `[project].dependencies`:** mkdocs is a build-time dep, not a runtime one. Add to `[dependency-groups].dev`.

---

## Task 1: MkDocs scaffold + first local build

**Files:**
- Modify: `pyproject.toml` (add mkdocs deps to dev group)
- Create: `mkdocs.yml`
- Create: `docs/index.md`

- [ ] **Step 1: Add MkDocs deps to `pyproject.toml`**

In `[dependency-groups].dev`, append:

```toml
dev = [
  "pytest>=8.0",
  "pytest-cov>=5.0",
  "mkdocs>=1.5",
  "mkdocs-material>=9.5",
  "mkdocs-awesome-pages-plugin>=2.9",
]
```

Run `uv sync` to refresh the lockfile. `uv.lock` will be updated.

- [ ] **Step 2: Create `mkdocs.yml`**

```yaml
site_name: GGI Policy
site_description: GGenomics policy library — data and application governance, cybersecurity.
site_url: https://policy.ggenomics.internal/
repo_url: https://github.com/GGenomics/GGI-POLICY
edit_uri: edit/main/

docs_dir: .

# Everything in this list is excluded from the rendered site.
# Use gitignore-style patterns.
exclude_docs: |
  /tools/
  /schemas/
  /exceptions/
  /templates/
  /docs/superpowers/
  /docs/_hooks/
  /docs/_stylesheets/
  /.github/
  /.venv/
  /.claude/
  /Dockerfile
  /.dockerignore
  /pyproject.toml
  /uv.lock
  /CLAUDE.md
  /AGENTS.md
  /mkdocs.yml
  /site/

theme:
  name: material
  features:
    - navigation.tabs
    - navigation.sections
    - navigation.expand
    - navigation.top
    - search.highlight
    - search.suggest
    - content.code.copy
    - toc.follow
  palette:
    - scheme: default
      primary: indigo
      accent: indigo

plugins:
  - search
  - awesome-pages

markdown_extensions:
  - admonition
  - attr_list
  - md_in_html
  - tables
  - toc:
      permalink: true
  - pymdownx.details
  - pymdownx.highlight:
      anchor_linenums: true
  - pymdownx.superfences

extra_css:
  - docs/_stylesheets/extra.css

hooks:
  - docs/_hooks/policy_page.py
```

- [ ] **Step 3: Create `docs/index.md`**

```markdown
---
title: Home
---

# GGI Policy Library

Welcome. This site is the canonical home for GGenomics company policies
covering data and application governance and cybersecurity.

## What's here

- **Policies** — domain-organized policy documents. Each policy declares its
  framework alignment and links to the relevant crosswalks.
- **Crosswalks** — control-by-control coverage tables for NIST CSF 2.0,
  CIS Controls v8, SOC 2 Trust Services Criteria, HIPAA 45 CFR Part 164,
  NIST SP 800-53 Rev 5, and NIST SP 800-171 Rev 3. Auto-regenerated from
  policy frontmatter on every PR.
- **Glossary** — controlled vocabulary referenced throughout the policies.

## How to read this site

Most readers will navigate by domain (Policies → Identity & Access, Data, …)
or by framework (Crosswalks). The crosswalks include a "Coverage gaps"
section that lists controls with no policy coverage yet — those are the
backlog of policies still to be authored.

## How to contribute

Policies live in the [GGI-POLICY](https://github.com/GGenomics/GGI-POLICY) repo.
Open a PR following the templates in `templates/`. CI runs schema validation,
crosswalk regeneration, and CODEOWNERS-gated review.
```

- [ ] **Step 4: Create the placeholder hook and CSS to satisfy the config**

Create `docs/_hooks/policy_page.py` with a minimal pass-through (Task 4 will fill it in):

```python
"""MkDocs hook: per-policy frontmatter rendering. See Task 4."""


def on_page_markdown(markdown: str, **kwargs) -> str:
    return markdown
```

Create `docs/_stylesheets/extra.css` with a minimal stub:

```css
/* GGI Policy site overrides. Filled in over later phases. */
.md-typeset table:not([class]) { font-size: 0.85rem; }
```

- [ ] **Step 5: Run a first build**

```bash
uv run mkdocs build --strict
```

Expected: site builds successfully. `--strict` makes warnings fatal so we don't accumulate broken-link debt. The output goes to `site/` (already in `.gitignore` from Phase 1).

If the build fails with broken-link warnings, investigate. Common cause: an internal Markdown link points at a moved file. Fix by updating the link.

If the build fails because `awesome-pages` complains about missing `.pages` files, that's expected — Task 3 adds them. For now, run with `--strict` *off* if needed:

```bash
uv run mkdocs build
```

…and confirm the build at least produces `site/index.html`. Tighten back to `--strict` after Task 3.

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml uv.lock mkdocs.yml docs/index.md \
        docs/_hooks/policy_page.py docs/_stylesheets/extra.css
git commit -m "$(cat <<'EOF'
feat(site): MkDocs Material scaffold + home page

Adds mkdocs, mkdocs-material, and awesome-pages as dev deps; wires
mkdocs.yml at the repo root with `docs_dir: .` and a comprehensive
exclude_docs list. Lands a placeholder policy_page hook (Task 4 fills
it in) and a small extra.css. The home page describes how the site
is laid out and how contributors author policies.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 2: Awesome-pages nav titles

**Files:**
- Create: 12 `policies/<domain>/.pages` files
- Create: `policies/.pages`
- Create: `crosswalks/.pages`
- Create: `glossary/.pages`

`awesome-pages` reads `.pages` files in each directory to control the nav title and ordering. Without these, the nav uses raw folder names (`identity-and-access` instead of `Identity & Access`).

- [ ] **Step 1: Create `policies/.pages`**

```yaml
title: Policies
nav:
  - identity-and-access
  - data
  - privacy
  - applications
  - endpoints
  - network
  - incident-response
  - vendor-and-third-party
  - security-operations
  - business-continuity
  - human-resources
  - meta
```

- [ ] **Step 2: Create per-domain `.pages` files**

For each domain, create `policies/<domain>/.pages` with a matching title:

`policies/identity-and-access/.pages`:
```yaml
title: Identity & Access (IAM)
```

`policies/data/.pages`:
```yaml
title: Data (DAT)
```

`policies/privacy/.pages`:
```yaml
title: Privacy (PRV)
```

`policies/applications/.pages`:
```yaml
title: Applications (APP)
```

`policies/endpoints/.pages`:
```yaml
title: Endpoints (END)
```

`policies/network/.pages`:
```yaml
title: Network (NET)
```

`policies/incident-response/.pages`:
```yaml
title: Incident Response (IR)
```

`policies/vendor-and-third-party/.pages`:
```yaml
title: Vendor & Third-Party (VND)
```

`policies/security-operations/.pages`:
```yaml
title: Security Operations (SEC)
```

`policies/business-continuity/.pages`:
```yaml
title: Business Continuity (BCP)
```

`policies/human-resources/.pages`:
```yaml
title: Human Resources (HR)
```

`policies/meta/.pages`:
```yaml
title: Meta (META)
```

- [ ] **Step 3: Create `crosswalks/.pages`**

```yaml
title: Crosswalks
nav:
  - NIST CSF 2.0: nist-csf.md
  - CIS Controls v8: cis.md
  - SOC 2 TSC: soc2.md
  - HIPAA 45 CFR Part 164: hipaa.md
  - NIST 800-53 Rev 5: nist-800-53.md
  - NIST 800-171 Rev 3: nist-800-171.md
```

- [ ] **Step 4: Create `glossary/.pages`**

```yaml
title: Glossary
```

- [ ] **Step 5: Build with `--strict`**

```bash
uv run mkdocs build --strict
```

Expected: success. The nav now shows human-readable section titles.

If awesome-pages complains about empty domain folders (each currently has only `.gitkeep`), the build may emit a warning. Domains with no markdown content besides `.gitkeep` should not produce nav entries. If they do (`identity-and-access` shows up empty), that's an awesome-pages quirk — confirm by inspecting `site/sitemap.xml`. The Phase 6 meta-policies and any first real policy will populate these sections; for now, an empty Identity & Access section is acceptable and harmless.

- [ ] **Step 6: Commit**

```bash
git add policies/.pages policies/*/.pages crosswalks/.pages glossary/.pages
git commit -m "$(cat <<'EOF'
feat(site): awesome-pages nav titles for all domain folders

Each policy domain folder + crosswalks + glossary gets a .pages file
declaring its human-readable nav title. policies/.pages also fixes the
domain order to match the design's reading order rather than alphabetic.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 3: Policy-page hook — frontmatter to metadata strip + framework table

**Files:**
- Modify: `docs/_hooks/policy_page.py` (replace placeholder)
- Create: `tools/tests/test_site_hooks.py`
- Create: `tools/tests/fixtures/site/policy-input.md`
- Create: `tools/tests/fixtures/site/policy-expected.md`

The hook reads each rendered page's source markdown. If the page has a YAML frontmatter block whose `id` starts with `POL-`, it:
1. Strips the frontmatter (so MkDocs doesn't try to render the raw YAML).
2. Prepends a metadata strip showing status, version, owner, effective_date, last_reviewed, review_cycle.
3. Appends a "Framework alignment" table at the bottom listing each framework block with clickable links to the crosswalk page.

Non-policy pages (no frontmatter, or frontmatter without a `POL-` id) pass through unmodified.

- [ ] **Step 1: Create test fixtures**

`tools/tests/fixtures/site/policy-input.md`:

```markdown
---
id: POL-IAM-GROUP-NAMING
title: Entra Group Naming Conventions
summary: >
  Defines naming conventions and type-selection rules for all groups
  in Entra ID.
domain: IAM
status: effective
version: 1.0.0
effective_date: 2026-06-01
last_reviewed: 2026-05-01
review_cycle: annual
owner: IT Director
approvers: [CISO, IT Director]
applies_to:
  - All Entra ID groups (cloud and synced)
supersedes: []
related: []
frameworks:
  nist_csf:     [PR.AC-01, PR.AC-03]
  cis:          ["5.4", "6.1"]
  soc2:         [CC6.1]
  hipaa:        ["164.308(a)(4)(i)"]
  nist_800_53:  [AC-2]
  nist_800_171: ["3.1.1"]
external_references: []
---

## Purpose
Establish a uniform naming and typing convention for Entra ID groups.
```

`tools/tests/fixtures/site/policy-expected.md`:

```markdown
!!! info "POL-IAM-GROUP-NAMING · v1.0.0 · effective"
    **Owner:** IT Director  · **Effective:** 2026-06-01  · **Last reviewed:** 2026-05-01  · **Review cycle:** annual

## Purpose
Establish a uniform naming and typing convention for Entra ID groups.

## Framework alignment

| Framework | Controls |
|---|---|
| NIST CSF 2.0 | [`PR.AC-01`](../../crosswalks/nist-csf.md), [`PR.AC-03`](../../crosswalks/nist-csf.md) |
| CIS Controls v8 | [`5.4`](../../crosswalks/cis.md), [`6.1`](../../crosswalks/cis.md) |
| SOC 2 TSC | [`CC6.1`](../../crosswalks/soc2.md) |
| HIPAA 45 CFR Part 164 | [`164.308(a)(4)(i)`](../../crosswalks/hipaa.md) |
| NIST 800-53 Rev 5 | [`AC-2`](../../crosswalks/nist-800-53.md) |
| NIST 800-171 Rev 3 | [`3.1.1`](../../crosswalks/nist-800-171.md) |
```

The relative-path depth (`../../`) is correct for a policy page at `policies/identity-and-access/group-naming.md` — MkDocs resolves Markdown links relative to the source file's directory, so two steps up reach the repo root, then `crosswalks/<framework>.md`. (`_depth_to_root` in the hook returns `len(parts) - 1` `../` segments; for a 3-segment path that's 2.)

- [ ] **Step 2: Write failing tests**

`tools/tests/test_site_hooks.py`:

```python
from pathlib import Path

from docs._hooks import policy_page


def test_policy_page_renders_metadata_strip_and_framework_table(fixtures_dir: Path) -> None:
    src = (fixtures_dir / "site/policy-input.md").read_text()
    expected = (fixtures_dir / "site/policy-expected.md").read_text()
    out = policy_page.transform(src, page_path="policies/identity-and-access/group-naming.md")
    assert out.strip() == expected.strip()


def test_non_policy_page_passes_through(fixtures_dir: Path) -> None:
    plain = "# Plain page\n\nNo frontmatter here.\n"
    out = policy_page.transform(plain, page_path="some/page.md")
    assert out == plain


def test_page_with_frontmatter_but_no_pol_id_passes_through() -> None:
    src = "---\ntitle: Crosswalks\n---\n\n# Crosswalks index\n"
    out = policy_page.transform(src, page_path="crosswalks/index.md")
    assert out == src


def test_relative_crosswalk_path_depth_for_top_level_meta_policy() -> None:
    src = (
        "---\n"
        "id: POL-META-DOC-FRAMEWORK\n"
        "title: t\nsummary: s\ndomain: META\nstatus: effective\nversion: 1.0.0\n"
        "effective_date: 2026-01-01\nlast_reviewed: 2026-01-01\nreview_cycle: annual\n"
        "owner: x\napprovers: [x]\napplies_to: [x]\nsupersedes: []\nrelated: []\n"
        "frameworks:\n  nist_csf: [GV.OC-01]\n"
        "external_references: []\n"
        "---\n# Body\n"
    )
    out = policy_page.transform(src, page_path="policies/meta/doc-framework.md")
    assert "(../../crosswalks/nist-csf.md)" in out


def test_skip_frameworks_with_empty_lists() -> None:
    src = (
        "---\n"
        "id: POL-IAM-X\n"
        "title: t\nsummary: s\ndomain: IAM\nstatus: draft\nversion: 0.1.0\n"
        "effective_date: 2026-01-01\nlast_reviewed: 2026-01-01\nreview_cycle: annual\n"
        "owner: x\napprovers: [x]\napplies_to: [x]\nsupersedes: []\nrelated: []\n"
        "frameworks:\n  nist_csf: [PR.AC-01]\n  cis: []\n"
        "external_references: []\n"
        "---\n# Body\n"
    )
    out = policy_page.transform(src, page_path="policies/identity-and-access/x.md")
    assert "NIST CSF 2.0" in out
    assert "CIS Controls v8" not in out
```

The hook is unit-testable by exposing a pure function `transform(markdown, page_path) -> str`. The MkDocs `on_page_markdown` callback in the same module is the thin adapter that calls `transform` with `page.file.src_path`.

Run:
```bash
uv run pytest tools/tests/test_site_hooks.py -v
```

Expected: import errors / `transform` not defined.

You may also need to add an `__init__.py` to `docs/_hooks/` for pytest to import it. Add `docs/_hooks/__init__.py` (empty) and `docs/__init__.py` (empty). And ensure `pythonpath = ["tools", "."]` in `[tool.pytest.ini_options]`. Verify by running pytest after adding the empties.

Actually — `docs/` is the docs root for MkDocs. Adding an `__init__.py` to it could surprise MkDocs. Safer alternative: import the hook in tests via `importlib`:

```python
import importlib.util
from pathlib import Path

_HOOK = Path(__file__).resolve().parent.parent.parent / "docs" / "_hooks" / "policy_page.py"
_spec = importlib.util.spec_from_file_location("policy_page", _HOOK)
policy_page = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(policy_page)
```

Replace `from docs._hooks import policy_page` in `test_site_hooks.py` with this `importlib` form. Update the `transform` calls accordingly.

- [ ] **Step 3: Implement the hook**

Replace `docs/_hooks/policy_page.py`:

```python
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
    """`policies/identity-and-access/group-naming.md` → `../../../`."""
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
    body = markdown[m.end():]
    meta_strip = _render_meta_strip(meta)
    framework_table = _render_framework_table(meta, page_path)
    return f"{meta_strip}\n{body.rstrip()}\n\n{framework_table}".rstrip() + "\n"


def on_page_markdown(markdown: str, *, page=None, **kwargs) -> str:
    if page is None:
        return markdown
    return transform(markdown, page.file.src_path)
```

- [ ] **Step 4: Run tests to verify passing**

```bash
uv run pytest tools/tests/test_site_hooks.py -v
```

Expected: 5 passed.

- [ ] **Step 5: Run full suite**

```bash
uv run pytest -q
```

Expected: 77 passed (72 prior + 5 new).

- [ ] **Step 6: Build site to confirm hook integrates with MkDocs**

```bash
uv run mkdocs build --strict
```

Expected: success. There are no policy files yet so the hook's policy branch isn't exercised at build time, but it must not break the build.

- [ ] **Step 7: Commit**

```bash
git add docs/_hooks/policy_page.py tools/tests/test_site_hooks.py \
        tools/tests/fixtures/site
git commit -m "$(cat <<'EOF'
feat(site): per-policy metadata strip + framework alignment table

MkDocs hook reads each policy page's YAML frontmatter; if id starts
with POL-, the frontmatter is replaced with a Material `info` admonition
showing status/version/owner/effective_date/last_reviewed/review_cycle,
and a Framework alignment table is appended with clickable links to
each framework's crosswalk page.

Non-policy pages (no frontmatter, or frontmatter without a POL- id)
pass through unchanged. Five tests cover the policy/non-policy split,
correct relative path depth, and skipping frameworks with empty lists.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 4: `build-site` CLI subcommand

**Files:**
- Create: `tools/ggi_policy/site.py`
- Modify: `tools/ggi_policy/cli.py`
- Modify: `tools/tests/test_cli.py`

Wraps `mkdocs build` with our usual conventions: `--strict` by default, `--repo-root` override, deterministic output to `<repo>/site/`.

- [ ] **Step 1: Implement `site.py`**

`tools/ggi_policy/site.py`:

```python
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
```

- [ ] **Step 2: Wire into the CLI**

Read `tools/ggi_policy/cli.py` first to find the right insertion point. Add a new command after `build-crosswalks` but before `if __name__ == "__main__":`:

```python
@main.command("build-site")
@click.option("--no-strict", is_flag=True, default=False,
              help="Disable --strict (build will not fail on broken links).")
@click.option("--repo-root", "repo_root_opt",
              type=click.Path(exists=True, file_okay=False, path_type=Path),
              default=None)
def build_site(no_strict: bool, repo_root_opt: Path | None) -> None:
    """Build the static MkDocs site into <repo>/site/."""
    from ggi_policy import site

    root = (repo_root_opt or repo_root()).resolve()
    rc = site.build(root, strict=not no_strict)
    if rc != 0:
        click.echo(f"FAIL: mkdocs build exited {rc}", err=True)
        sys.exit(rc)
    click.echo(f"OK: site built at {root / 'site'}")
```

- [ ] **Step 3: Add CLI test**

Append to `tools/tests/test_cli.py`:

```python
def test_build_site_invokes_mkdocs(monkeypatch, tmp_path: Path) -> None:
    """The build-site subcommand calls site.build with the right args; it does
    not actually invoke mkdocs in tests (we monkeypatch site.build)."""
    from ggi_policy import site

    captured = {}

    def fake_build(repo_root, *, strict):
        captured["repo_root"] = repo_root
        captured["strict"] = strict
        return 0

    monkeypatch.setattr(site, "build", fake_build)
    runner = CliRunner()
    result = runner.invoke(main, ["build-site", "--repo-root", str(tmp_path)])
    assert result.exit_code == 0, result.output
    assert "OK" in result.output
    assert captured["repo_root"] == tmp_path.resolve()
    assert captured["strict"] is True


def test_build_site_propagates_failure(monkeypatch, tmp_path: Path) -> None:
    from ggi_policy import site

    monkeypatch.setattr(site, "build", lambda repo_root, *, strict: 1)
    runner = CliRunner()
    result = runner.invoke(main, ["build-site", "--repo-root", str(tmp_path)])
    assert result.exit_code == 1
    assert "FAIL" in result.output
```

- [ ] **Step 4: Run tests**

```bash
uv run pytest tools/tests/test_cli.py -v
```

Expected: 5 passed (3 prior + 2 new).

- [ ] **Step 5: Smoke the live build via the CLI**

```bash
uv run ggi-policy build-site
```

Expected: `OK: site built at <repo>/site`. A `site/` directory now contains static HTML.

- [ ] **Step 6: Run full suite**

```bash
uv run pytest -q
```

Expected: 79 passed.

- [ ] **Step 7: Commit**

```bash
git add tools/ggi_policy/site.py tools/ggi_policy/cli.py tools/tests/test_cli.py
git commit -m "$(cat <<'EOF'
feat(cli): build-site subcommand wraps mkdocs build

Adds a `build-site` subcommand that runs `mkdocs build --strict` from
the repo root and exits with mkdocs's return code. --no-strict opt-out
for development. Tests monkeypatch site.build so the suite stays
isolated from the real mkdocs invocation.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 5: Dockerfile + .dockerignore

**Files:**
- Create: `Dockerfile`
- Create: `.dockerignore`

The image is built from a pre-built `site/` directory. Build order in CI:
1. `uv run ggi-policy build-site` → produces `site/`
2. `docker build -t ... .` → copies `site/` into nginx

Locally the same flow works: build the site, then build the image.

- [ ] **Step 1: Create `Dockerfile`**

`Dockerfile`:

```dockerfile
# syntax=docker/dockerfile:1
FROM nginx:alpine

# Copy the pre-built MkDocs site into nginx's default web root.
COPY site/ /usr/share/nginx/html/

# Health check and explicit signal handling are nginx defaults.
EXPOSE 80
```

We deliberately don't run `mkdocs build` inside the image: that would pull every Python build dependency into the runtime layer. Building `site/` first and copying keeps the image small (~30MB).

- [ ] **Step 2: Create `.dockerignore`**

`.dockerignore`:

```
# Everything except site/ and the bare metadata files needed for the COPY.
*
!site/
!.dockerignore

# (No README or LICENSE inside the image — it's just a static-site server.)
```

- [ ] **Step 3: Build locally and smoke-test**

Confirm the build:

```bash
uv run ggi-policy build-site
docker build -t ggi-policy-site:dev .
```

Expected: a working image. Spot-check by running it briefly:

```bash
docker run --rm -d -p 18080:80 --name ggi-smoke ggi-policy-site:dev
sleep 2
curl -s http://localhost:18080/ | head -5
docker stop ggi-smoke
```

Expected: the `curl` returns the rendered HTML of the home page (look for `GGI Policy Library` in the output).

- [ ] **Step 4: Commit**

```bash
git add Dockerfile .dockerignore
git commit -m "$(cat <<'EOF'
feat(docker): nginx:alpine container serving the built site/

Dockerfile copies a pre-built site/ directory into nginx's default
web root. The .dockerignore excludes everything but site/ so the
build context stays tiny. The image is ~30MB and serves the static
HTML on port 80.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 6: GitHub Actions workflow — build & push to GHCR

**Files:**
- Create: `.github/workflows/build-and-push.yml`

Triggered on every push to `main`. Builds the site, builds the image, pushes to GHCR with two tags:
- `latest`
- `main-{git-sha}` (so Flux image automation in Phase 4 can pin to a specific build)

Auth uses the built-in `GITHUB_TOKEN` with `packages: write` permission (no PAT, no extra secret).

- [ ] **Step 1: Create the workflow**

`.github/workflows/build-and-push.yml`:

```yaml
name: build-and-push

on:
  push:
    branches: [main]

permissions:
  contents: read
  packages: write

jobs:
  build-and-push:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install uv
        uses: astral-sh/setup-uv@v3
        with:
          version: "latest"

      - name: Set up Python
        run: uv python install 3.12

      - name: Install dependencies
        run: uv sync --frozen

      - name: Build site
        run: uv run ggi-policy build-site

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Log in to GHCR
        uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Build and push
        uses: docker/build-push-action@v6
        with:
          context: .
          file: ./Dockerfile
          push: true
          tags: |
            ghcr.io/ggenomics/ggi-policy-site:latest
            ghcr.io/ggenomics/ggi-policy-site:main-${{ github.sha }}
          cache-from: type=gha
          cache-to: type=gha,mode=max
```

- [ ] **Step 2: Verify the workflow syntax**

GitHub doesn't run Actions on local commits, so the only local validation is YAML syntax. Run:

```bash
python3 -c "import yaml; yaml.safe_load(open('.github/workflows/build-and-push.yml').read())"
```

Expected: silent (no syntax error).

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/build-and-push.yml
git commit -m "$(cat <<'EOF'
ci(image): build site, build container, push to GHCR on main pushes

Workflow runs on every push to main. Builds the MkDocs site, builds an
nginx:alpine image with the site baked in, and pushes to
ghcr.io/ggenomics/ggi-policy-site with `latest` and `main-{sha}` tags.
Auth uses the workflow GITHUB_TOKEN with packages: write — no PAT.

Phase 4 (k8s deployment) will configure Flux image automation to watch
this registry and reconcile new tags into the ggi_internals repo.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

- [ ] **Step 4: After landing — verify GHCR push (optional, post-merge)**

After the PR merges to main, watch the Actions tab. The first run will:
1. Build site (~10s)
2. Build image (~30s)
3. Push to GHCR (~1min depending on the registry)

Confirm by browsing https://github.com/orgs/GGenomics/packages → `ggi-policy-site`.

If the push fails with `denied: installation not allowed to Create organization package`, the org's package settings need to be updated:
- Go to `https://github.com/organizations/GGenomics/settings/packages`
- Set "GitHub Actions" to "Allow GitHub Actions to create and approve pull requests" *or* explicitly grant the repo access via a fine-grained settings page.
- The exact path depends on org-level configuration. If you hit this, escalate to a GGenomics org admin to grant the repo `packages: write` at the org level.

---

## Task 7: End-to-end smoke

**Files:** none — verification only.

- [ ] **Step 1: Confirm the full pipeline runs locally**

```bash
uv run pytest -q
uv run ggi-policy validate
uv run ggi-policy build-crosswalks --check
uv run ggi-policy build-site
ls site/index.html crosswalks/*.md
```

Expected: 79 passed, validate OK, crosswalks up to date, site built, all expected output files present.

- [ ] **Step 2: Author a fake `POL-IAM-GROUP-NAMING` and verify the hook fires**

Copy `tools/tests/fixtures/valid/policies/identity-and-access/group-naming.md` to `policies/identity-and-access/group-naming.md`, copy its sidecar similarly, and run:

```bash
uv run ggi-policy validate
uv run ggi-policy build-crosswalks
uv run ggi-policy build-site
```

Then inspect `site/policies/identity-and-access/group-naming/index.html` (or whatever path mkdocs material produces — check the directory). The page should:
- Show the metadata strip near the top with status/version/owner/etc.
- Show a "Framework alignment" section near the bottom with rows for each framework and clickable links to the crosswalks.
- Have the YAML frontmatter NOT visible as raw text.

Open the `site/index.html` home page and the `site/crosswalks/nist-csf/index.html` page and confirm navigation between them works.

- [ ] **Step 3: Build and run the container with the policy in place**

```bash
docker build -t ggi-policy-site:smoke .
docker run --rm -d -p 18080:80 --name ggi-smoke ggi-policy-site:smoke
sleep 2
curl -s http://localhost:18080/policies/identity-and-access/group-naming/ | grep "Framework alignment"
docker stop ggi-smoke
```

Expected: `curl` finds `Framework alignment` in the served HTML.

- [ ] **Step 4: Remove the smoke files**

```bash
rm policies/identity-and-access/group-naming.md
rm policies/identity-and-access/group-naming.rules.yaml
uv run ggi-policy build-crosswalks
```

The crosswalk regen will revert PR.AC-01's `Policies` cell to `_(no policy)_` and put PR.AC-01 back in the gaps list. Verify:

```bash
uv run ggi-policy validate
uv run ggi-policy build-crosswalks --check
```

Expected: validate OK, check OK.

- [ ] **Step 5: Confirm `site/` is gitignored**

```bash
git status -- site/ docs/_hooks/__pycache__
```

Expected: nothing tracked. `site/` and `__pycache__/` are already in `.gitignore`. If anything appears tracked, add it to `.gitignore` before merging.

- [ ] **Step 6: No commit needed for this task** (smoke files removed; tests already cover the hook).

---

## Self-review

**Spec coverage:**

| Spec section | Plan task |
|---|---|
| §3 Decisions: MkDocs Material → static site → containerized | Tasks 1, 5 |
| §6.5 Reverse direction: per-policy frameworks table | Task 3 |
| §8.4 Site hosting (build-and-push to GHCR) | Tasks 5, 6 |
| §8.4 Image tag strategy (`latest` + content-addressed `main-{sha}`) | Task 6 |
| Flux image automation watching GHCR | **Deferred to Phase 4** (called out in plan front matter) |
| Entra-SSO ingress / oauth2-proxy / k8s manifests | **Deferred to Phase 4** |

Phase 4 (k8s) explicitly handles deployment + auth. Phase 3 ends at "image is in GHCR with the right tags."

**Placeholder scan:** no `TBD`/`TODO`/`FIXME` placeholders. Two intentional pieces of explanatory text:

- Task 6 Step 4 calls out a possible org-level GHCR permission failure with a concrete remediation path.
- Task 2 Step 5 notes that empty domain folders may show up in the nav as empty sections — this is acceptable for Phase 3 since policies haven't been authored yet.

**Type / signature consistency:**

- `site.build(repo_root: Path, *, strict: bool = True) -> int` — introduced in Task 4, used in Task 4 CLI and Task 4 tests. Stable.
- `policy_page.transform(markdown: str, page_path: str) -> str` — introduced in Task 3, used by `on_page_markdown` adapter and tests. Stable.
- The `_FRAMEWORK_LABELS` dict in `policy_page.py` uses the same six framework keys as `controls.py` (`nist_csf`, `cis`, `soc2`, `hipaa`, `nist_800_53`, `nist_800_171`) — verified consistent.

**Ambiguity:**

- The hook's `_depth_to_root` uses `page_path.split("/")` and counts segments. `policies/identity-and-access/group-naming.md` is 3 segments; `len(parts) - 1` returns 2, so the prefix is `"../../"`. The fixture and the test were corrected during plan authoring to match. MkDocs resolves Markdown links relative to the source file's directory, not the rendered URL, so `../../crosswalks/nist-csf.md` is correct.

**Carry-forward to Phase 4:**

- Image is in GHCR but unused. Phase 4 wires Flux `ImageRepository` + `ImagePolicy` watching `ghcr.io/ggenomics/ggi-policy-site` to auto-update `apps/policy-docs/kustomization.yaml` in `GGenomics/ggi_internals`.
- The `site_url` in `mkdocs.yml` is `https://policy.ggenomics.internal/`; that DNS doesn't exist yet. Phase 4 owns the DNS + ingress + oauth2-proxy work.
- The Phase 2 carry-forward items (HIPAA XML test coverage, deterministic catalog sort) remain open. Neither blocks Phase 3.

**Carry-forward from this plan into a hypothetical Phase 3.5:**

- Crosswalk anchored rows: clicking `[PR.AC-01]` from a policy page lands on the crosswalk page but doesn't jump to the row. A small enhancement to `crosswalks.py` could emit `<a id="pr-ac-01">` next to each row's first cell, and the hook would emit `(...crosswalks/nist-csf.md#pr-ac-01)`. Out of Phase 3 scope; nice quality-of-life follow-up.
- Per-page edit-on-GitHub link: `mkdocs.yml` already sets `edit_uri: edit/main/`, so Material renders an edit pencil. Validate after first deploy.
