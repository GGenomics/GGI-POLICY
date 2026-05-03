# Phase 1: Foundation — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Establish the policy-doc framework's foundation — JSON Schemas, repo skeleton, templates, glossary stub, and a fully tested `ggi-policy validate` CLI plus CI workflow — so that real policies can be authored against a deterministic, schema-validated structure.

**Architecture:** Hand-written JSON Schemas under `schemas/` are the public contract for both AI agents and Python tooling. A Python package `ggi_policy` (under `tools/`) implements a single `validate` CLI command that orchestrates pluggable check modules (frontmatter, sidecar rules, exceptions, ID/path consistency, CODEOWNERS reconciliation, framework tag format, removed-rule integrity). Tests are written first against fixture policies (TDD) before each validator is implemented. CI runs `uv run ggi-policy validate` on every PR.

**Tech Stack:** Python 3.12+, `uv` for env/deps, `click` for the CLI, `jsonschema` (Draft 2020-12) for schema validation, `python-frontmatter` for parsing MD frontmatter, `PyYAML` for YAML, `pytest` for tests. GitHub Actions for CI.

---

## Prerequisites

- The repo is currently essentially empty (only `README.md`, `CLAUDE.md` stub, and the design + plan docs under `docs/superpowers/`). All work happens directly on `main` for this fresh-repo phase. Future phases may want a worktree (`superpowers:using-git-worktrees`) but this one doesn't need it.
- No external systems must be live for Phase 1 — no Entra app, no GitHub teams, no DNS. Phase 1 produces local + CI tooling only. (Phase 4/5 will require those external prerequisites.)
- Reference: the design doc this plan implements is [docs/superpowers/specs/2026-05-02-policy-doc-framework-design.md](../specs/2026-05-02-policy-doc-framework-design.md). Sections referenced as **§N** below are sections of the design doc.

## File structure (locked-in decomposition)

```
GGI-POLICY/
├── pyproject.toml                                     # uv-managed project + console-script
├── .gitignore
├── README.md                                          # updated to point at design + plan
├── CLAUDE.md                                          # untouched (stub remains until Phase 6)
│
├── policies/                                          # 12 domain folders (empty + .gitkeep)
│   ├── identity-and-access/.gitkeep
│   ├── data/.gitkeep
│   ├── privacy/.gitkeep
│   ├── applications/.gitkeep
│   ├── endpoints/.gitkeep
│   ├── network/.gitkeep
│   ├── incident-response/.gitkeep
│   ├── vendor-and-third-party/.gitkeep
│   ├── security-operations/.gitkeep
│   ├── business-continuity/.gitkeep
│   ├── human-resources/.gitkeep
│   └── meta/.gitkeep
│
├── exceptions/.gitkeep
├── crosswalks/.gitkeep                                # populated in Phase 2
├── glossary/terms.md                                  # stub: empty section per domain
│
├── templates/
│   ├── policy.md
│   ├── policy.rules.yaml
│   └── exception.md
│
├── schemas/
│   ├── policy-frontmatter.schema.json
│   ├── policy-rules.schema.json
│   ├── exception.schema.json
│   ├── role-team-mapping.schema.json                  # validates role-team-mapping.yaml shape
│   └── role-team-mapping.yaml                         # initial role→team handles
│
├── tools/
│   ├── ggi_policy/                                    # Python package
│   │   ├── __init__.py
│   │   ├── __main__.py
│   │   ├── cli.py                                     # click app, `validate` subcommand
│   │   ├── io.py                                      # load_policy / load_rules / load_exception / iter_*
│   │   ├── repo.py                                    # repo-root detection, path helpers
│   │   ├── codeowners.py                              # parse .github/CODEOWNERS
│   │   ├── role_team_map.py                           # load + lookup role→team mapping
│   │   ├── result.py                                  # ValidationFinding, ValidationReport
│   │   └── validate/
│   │       ├── __init__.py
│   │       ├── runner.py                              # orchestrates all checks; returns ValidationReport
│   │       ├── frontmatter.py                         # JSON-Schema-validate frontmatter
│   │       ├── rules_sidecar.py                       # JSON-Schema-validate *.rules.yaml
│   │       ├── exceptions.py                          # exception schema + tiered cap + policy_ref check
│   │       ├── consistency.py                         # ID ↔ filename ↔ folder
│   │       ├── tags.py                                # framework tag format (Phase 1) — membership deferred to Phase 2
│   │       ├── approvers.py                           # CODEOWNERS ↔ approvers reconciliation
│   │       └── removed_rules.py                       # numbers-never-reused
│   └── tests/
│       ├── __init__.py
│       ├── conftest.py
│       ├── fixtures/
│       │   ├── valid/
│       │   │   ├── policies/identity-and-access/group-naming.md
│       │   │   ├── policies/identity-and-access/group-naming.rules.yaml
│       │   │   └── exceptions/EXC-2026-001-finance-legacy-group.md
│       │   └── invalid/                               # narrow, single-defect fixtures per check
│       │       ├── frontmatter/missing-id.md
│       │       ├── frontmatter/bad-status.md
│       │       ├── frontmatter/bad-version.md
│       │       ├── rules/duplicate-rule-id.yaml
│       │       ├── rules/reused-removed-number.yaml
│       │       ├── exceptions/cap-exceeded-required.md
│       │       ├── exceptions/cap-exceeded-recommended.md
│       │       ├── exceptions/dangling-policy-ref.md
│       │       ├── consistency/wrong-folder.md
│       │       ├── consistency/filename-mismatch.md
│       │       ├── tags/bad-nist-csf.md
│       │       └── approvers/not-in-codeowners.md
│       ├── test_io.py
│       ├── test_codeowners.py
│       ├── test_role_team_map.py
│       ├── test_validate_frontmatter.py
│       ├── test_validate_rules_sidecar.py
│       ├── test_validate_exceptions.py
│       ├── test_validate_consistency.py
│       ├── test_validate_tags.py
│       ├── test_validate_approvers.py
│       ├── test_validate_removed_rules.py
│       ├── test_validate_runner.py
│       └── test_cli.py
│
└── .github/
    ├── CODEOWNERS                                     # full per-domain mapping per §7.3
    └── workflows/
        └── validate.yml                               # runs `uv run ggi-policy validate` on PR
```

## Conventions

- **Commits:** Conventional Commits (`feat(validate): ...`, `chore(scaffold): ...`, `test(io): ...`). One commit per task unless noted.
- **TDD discipline:** every check module has a paired test module. Tests are written *before* the implementation in each task.
- **Fixtures:** each invalid fixture isolates a single defect so tests are unambiguous about what triggered the error.
- **Find by repo root:** all tooling resolves the repo root via `git rev-parse --show-toplevel` (cached) — this lets tools run from any subdirectory.

---

## Task 1: Project scaffold

**Files:**
- Create: `pyproject.toml`
- Create: `.gitignore`
- Create: `tools/ggi_policy/__init__.py`
- Create: `tools/ggi_policy/__main__.py`
- Create: `tools/ggi_policy/cli.py`
- Create: `tools/tests/__init__.py`
- Create: `tools/tests/conftest.py`
- Create: 12 `policies/<domain>/.gitkeep` files
- Create: `exceptions/.gitkeep`, `crosswalks/.gitkeep`
- Modify: `README.md` (point at design and plan)

- [ ] **Step 1: Create `pyproject.toml`**

```toml
[project]
name = "ggi-policy"
version = "0.1.0"
description = "GGI policy documentation framework — validation, crosswalks, and site tooling."
requires-python = ">=3.12"
authors = [{ name = "GGenomics IT" }]
dependencies = [
  "click>=8.1",
  "jsonschema>=4.21",
  "python-frontmatter>=1.1",
  "PyYAML>=6.0",
]

[project.scripts]
ggi-policy = "ggi_policy.cli:main"

[dependency-groups]
dev = [
  "pytest>=8.0",
  "pytest-cov>=5.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["tools/ggi_policy"]

[tool.hatch.build.targets.wheel.sources]
"tools/ggi_policy" = "ggi_policy"

[tool.pytest.ini_options]
testpaths = ["tools/tests"]
pythonpath = ["tools"]
addopts = "-q"
```

- [ ] **Step 2: Create `.gitignore`**

```gitignore
# Python
__pycache__/
*.py[cod]
*.egg-info/
.venv/
.pytest_cache/
.coverage
htmlcov/
dist/
build/

# uv
.python-version

# Site build (Phase 3)
site/

# IDE
.idea/
.vscode/
*.swp

# OS
.DS_Store
```

- [ ] **Step 3: Create the package skeleton**

Create `tools/ggi_policy/__init__.py`:

```python
"""GGI policy documentation framework tooling."""

__version__ = "0.1.0"
```

Create `tools/ggi_policy/__main__.py`:

```python
from ggi_policy.cli import main

if __name__ == "__main__":
    main()
```

Create `tools/ggi_policy/cli.py`:

```python
import sys

import click


@click.group()
@click.version_option()
def main() -> None:
    """GGI policy documentation framework tooling."""


@main.command()
def validate() -> None:
    """Validate every policy, sidecar, and exception in the repo."""
    click.echo("validate: not yet implemented")
    sys.exit(0)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Create test scaffolding**

Create `tools/tests/__init__.py` (empty).

Create `tools/tests/conftest.py`:

```python
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture(scope="session")
def fixtures_dir() -> Path:
    return FIXTURES
```

- [ ] **Step 5: Install deps and verify CLI**

Run:

```bash
uv sync
uv run ggi-policy --help
```

Expected: help text listing the `validate` subcommand. If `uv` is not installed, install per https://docs.astral.sh/uv/ first.

- [ ] **Step 6: Run the (empty) test suite**

```bash
uv run pytest
```

Expected: `no tests ran` (exit 0). Confirms pytest is wired correctly.

- [ ] **Step 7: Create the empty repo skeleton (12 domain folders + supporting dirs)**

```bash
for dir in identity-and-access data privacy applications endpoints network \
           incident-response vendor-and-third-party security-operations \
           business-continuity human-resources meta; do
  mkdir -p "policies/$dir"
  touch "policies/$dir/.gitkeep"
done
mkdir -p exceptions crosswalks
touch exceptions/.gitkeep crosswalks/.gitkeep
```

- [ ] **Step 8: Update `README.md`**

Replace its single-line content with:

```markdown
# GGI Policy

Canonical home for GGenomics company policies covering data and application
governance and cybersecurity.

- **Design:** [docs/superpowers/specs/2026-05-02-policy-doc-framework-design.md](docs/superpowers/specs/2026-05-02-policy-doc-framework-design.md)
- **Phase 1 plan:** [docs/superpowers/plans/2026-05-02-phase-1-foundation.md](docs/superpowers/plans/2026-05-02-phase-1-foundation.md)

This repo is in early bring-up. See `CLAUDE.md` for AI-agent guidance once it
is fleshed out (Phase 6).
```

- [ ] **Step 9: Commit**

```bash
git add pyproject.toml .gitignore tools README.md policies exceptions crosswalks
git commit -m "chore(scaffold): initial Python project, repo skeleton, and CLI stub"
```

---

## Task 2: IO + repo helpers

**Files:**
- Create: `tools/ggi_policy/repo.py`
- Create: `tools/ggi_policy/io.py`
- Create: `tools/tests/test_io.py`
- Create: `tools/tests/fixtures/valid/policies/identity-and-access/group-naming.md`
- Create: `tools/tests/fixtures/valid/policies/identity-and-access/group-naming.rules.yaml`
- Create: `tools/tests/fixtures/valid/exceptions/EXC-2026-001-finance-legacy-group.md`

- [ ] **Step 1: Create the valid policy fixture**

`tools/tests/fixtures/valid/policies/identity-and-access/group-naming.md`:

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
  - All shared mailboxes
supersedes: []
related: []
frameworks:
  nist_csf:     [PR.AC-1, PR.AC-3]
  cis:          ["5.4", "6.1"]
  soc2:         [CC6.1]
  hipaa:        ["164.308(a)(4)"]
  nist_800_53:  [AC-2]
  nist_800_171: ["3.1.1"]
external_references:
  - https://learn.microsoft.com/entra/identity/users/groups-naming-policy
---

## Purpose
Establish a uniform naming and typing convention for Entra ID groups.

## Scope
All Entra ID groups; all shared mailboxes.

## Policy Statements
**R1.** Security group names must match the prescribed pattern.
**R2.** Group type selection follows the decision table.
**R3.** Privileged groups require PIM-eligible assignment.

## Rationale
Inconsistent group naming has historically caused permission drift.

## Examples
Compliant: `sg-az-prod-finance-readers`. Non-compliant: `Marketing-Team-2024`.

## Implementation Guidance
See Microsoft's Entra group-naming-policy docs (linked above).

## Exceptions
See `exceptions/` directory.

## References
- POL-IAM-RBAC-MODEL (related)

## Revision History
- 1.0.0 (2026-06-01): initial release.
```

- [ ] **Step 2: Create the valid sidecar rules fixture**

`tools/tests/fixtures/valid/policies/identity-and-access/group-naming.rules.yaml`:

```yaml
policy_id: POL-IAM-GROUP-NAMING
rules:
  - id: R1
    statement: Security group names must match the prescribed pattern.
    type: pattern
    severity: required
    applies_to:
      object_type: entra_security_group
    pattern: "^sg-(az|m365|ad)-[a-z0-9]+-[a-z0-9-]+$"
    examples:
      compliant: [sg-az-prod-finance-readers]
      non_compliant:
        - { value: "Marketing-Team-2024", reason: "Missing sg- prefix" }
  - id: R2
    statement: Group type must be chosen via the decision table below.
    type: decision_table
    severity: required
    inputs: [needs_email, needs_files, needs_chat, dist_only]
    rows:
      - { needs_email: true,  needs_files: true,  needs_chat: true,  result: m365_group }
      - { needs_email: true,  needs_files: false, needs_chat: false, dist_only: true, result: distribution_group }
      - { needs_email: false, needs_files: false, needs_chat: false, result: security_group }
  - id: R3
    statement: Privileged-access groups require PIM-eligible assignment.
    type: flag
    severity: required
    applies_to:
      object_type: entra_security_group
      where:
        name_matches: "^sg-az-prod-.*-(admin|owner|contributor)$"
    expected: { pim_eligible_only: true }
```

- [ ] **Step 3: Create the valid exception fixture**

`tools/tests/fixtures/valid/exceptions/EXC-2026-001-finance-legacy-group.md`:

```markdown
---
id: EXC-2026-001-FINANCE-LEGACY-GROUP
policy_ref: POL-IAM-GROUP-NAMING.R1
requested_by: jane.doe@ggenomics.com
approver: CISO
approved_date: 2026-04-15
effective_date: 2026-04-15
expires: 2026-10-15
status: active
compensating_control: >
  Conditional Access policy CAP-23 enforces MFA + compliant device.
risk_acceptance: Accepted by CISO; documented in risk register RR-2026-014.
---

## Justification
Legacy group naming pre-dates the policy; rename requires coordinated downstream changes.

## Renewal plan
Migrate by 2026-10-15.
```

- [ ] **Step 4: Write failing tests for `io.py`**

`tools/tests/test_io.py`:

```python
from pathlib import Path

import pytest

from ggi_policy import io


def test_load_policy_returns_frontmatter_and_body(fixtures_dir: Path) -> None:
    path = fixtures_dir / "valid/policies/identity-and-access/group-naming.md"
    policy = io.load_policy(path)
    assert policy.path == path
    assert policy.metadata["id"] == "POL-IAM-GROUP-NAMING"
    assert policy.metadata["domain"] == "IAM"
    assert "## Purpose" in policy.body


def test_load_rules_returns_dict_when_sidecar_exists(fixtures_dir: Path) -> None:
    policy_path = fixtures_dir / "valid/policies/identity-and-access/group-naming.md"
    rules = io.load_rules(policy_path)
    assert rules is not None
    assert rules["policy_id"] == "POL-IAM-GROUP-NAMING"
    assert len(rules["rules"]) == 3


def test_load_rules_returns_none_when_no_sidecar(fixtures_dir: Path, tmp_path: Path) -> None:
    orphan = tmp_path / "orphan.md"
    orphan.write_text("---\nid: POL-IAM-X\n---\n")
    assert io.load_rules(orphan) is None


def test_load_exception(fixtures_dir: Path) -> None:
    path = fixtures_dir / "valid/exceptions/EXC-2026-001-finance-legacy-group.md"
    exc = io.load_exception(path)
    assert exc.path == path
    assert exc.metadata["id"] == "EXC-2026-001-FINANCE-LEGACY-GROUP"
    assert exc.metadata["policy_ref"] == "POL-IAM-GROUP-NAMING.R1"


def test_iter_policies_walks_subtree(fixtures_dir: Path) -> None:
    policies = list(io.iter_policies(fixtures_dir / "valid/policies"))
    assert len(policies) == 1
    assert policies[0].metadata["id"] == "POL-IAM-GROUP-NAMING"


def test_iter_exceptions_walks_directory(fixtures_dir: Path) -> None:
    excs = list(io.iter_exceptions(fixtures_dir / "valid/exceptions"))
    assert len(excs) == 1
    assert excs[0].metadata["id"] == "EXC-2026-001-FINANCE-LEGACY-GROUP"
```

- [ ] **Step 5: Run tests to verify failure**

```bash
uv run pytest tools/tests/test_io.py -v
```

Expected: import errors / module not found for `ggi_policy.io`.

- [ ] **Step 6: Implement `repo.py`**

`tools/ggi_policy/repo.py`:

```python
from functools import cache
from pathlib import Path
import subprocess


@cache
def repo_root() -> Path:
    """Return the absolute path to the repo's git root."""
    out = subprocess.check_output(["git", "rev-parse", "--show-toplevel"], text=True)
    return Path(out.strip()).resolve()
```

- [ ] **Step 7: Implement `io.py`**

`tools/ggi_policy/io.py`:

```python
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
```

- [ ] **Step 8: Run tests to verify passing**

```bash
uv run pytest tools/tests/test_io.py -v
```

Expected: 6 passed.

- [ ] **Step 9: Commit**

```bash
git add tools/ggi_policy/repo.py tools/ggi_policy/io.py tools/tests/test_io.py tools/tests/fixtures/valid
git commit -m "feat(io): policy/rules/exception loaders and repo-root helper"
```

---

## Task 3: Frontmatter JSON Schema + validator

**Files:**
- Create: `schemas/policy-frontmatter.schema.json`
- Create: `tools/ggi_policy/validate/__init__.py`
- Create: `tools/ggi_policy/validate/frontmatter.py`
- Create: `tools/ggi_policy/result.py`
- Create: `tools/tests/test_validate_frontmatter.py`
- Create: `tools/tests/fixtures/invalid/frontmatter/missing-id.md`
- Create: `tools/tests/fixtures/invalid/frontmatter/bad-status.md`
- Create: `tools/tests/fixtures/invalid/frontmatter/bad-version.md`

- [ ] **Step 1: Create the frontmatter JSON Schema**

`schemas/policy-frontmatter.schema.json`:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://ggenomics.com/schemas/policy-frontmatter.schema.json",
  "title": "GGI policy frontmatter",
  "type": "object",
  "additionalProperties": false,
  "required": [
    "id", "title", "summary", "domain", "status", "version",
    "effective_date", "last_reviewed", "review_cycle",
    "owner", "approvers", "applies_to", "frameworks"
  ],
  "properties": {
    "id":             { "type": "string", "pattern": "^POL-[A-Z]+-[A-Z0-9-]+$" },
    "title":          { "type": "string", "minLength": 1 },
    "summary":        { "type": "string", "minLength": 1 },
    "domain":         { "enum": ["IAM","DAT","PRV","APP","END","NET","IR","VND","SEC","BCP","HR","META"] },
    "status":         { "enum": ["draft","effective","superseded","retired"] },
    "version":        { "type": "string", "pattern": "^\\d+\\.\\d+\\.\\d+$" },
    "effective_date": { "type": "string", "format": "date" },
    "last_reviewed":  { "type": "string", "format": "date" },
    "review_cycle":   { "enum": ["annual","biannual","triennial","event-driven"] },
    "owner":          { "type": "string", "minLength": 1 },
    "approvers":      { "type": "array", "items": { "type": "string", "minLength": 1 }, "minItems": 1 },
    "applies_to":     { "type": "array", "items": { "type": "string", "minLength": 1 }, "minItems": 1 },
    "supersedes":     { "type": "array", "items": { "type": "string", "pattern": "^POL-[A-Z]+-[A-Z0-9-]+$" }, "default": [] },
    "superseded_by":  { "type": "array", "items": { "type": "string", "pattern": "^POL-[A-Z]+-[A-Z0-9-]+$" }, "default": [] },
    "related":        { "type": "array", "items": { "type": "string", "pattern": "^POL-[A-Z]+-[A-Z0-9-]+$" }, "default": [] },
    "frameworks": {
      "type": "object",
      "additionalProperties": false,
      "properties": {
        "nist_csf":     { "type": "array", "items": { "type": "string", "pattern": "^(GV|ID|PR|DE|RS|RC)\\.[A-Z]{2}-\\d+$" } },
        "cis":          { "type": "array", "items": { "type": "string", "pattern": "^\\d+(\\.\\d+)?$" } },
        "soc2":         { "type": "array", "items": { "type": "string", "pattern": "^(CC|A|PI|C|P)\\d+\\.\\d+$" } },
        "hipaa":        { "type": "array", "items": { "type": "string", "pattern": "^164\\.\\d{3}\\([a-z]\\)(\\(\\d+\\))?(\\([ivx]+\\))?$" } },
        "nist_800_53":  { "type": "array", "items": { "type": "string", "pattern": "^[A-Z]{2}-\\d+(\\(\\d+\\))?$" } },
        "nist_800_171": { "type": "array", "items": { "type": "string", "pattern": "^\\d+\\.\\d+\\.\\d+$" } }
      }
    },
    "external_references": { "type": "array", "items": { "type": "string", "format": "uri" }, "default": [] }
  }
}
```

- [ ] **Step 2: Create invalid fixtures**

`tools/tests/fixtures/invalid/frontmatter/missing-id.md`:

```markdown
---
title: Missing ID
summary: This policy is missing the required id field.
domain: IAM
status: draft
version: 0.1.0
effective_date: 2026-06-01
last_reviewed: 2026-05-01
review_cycle: annual
owner: IT Director
approvers: [CISO]
applies_to: [test]
frameworks: { nist_csf: [PR.AC-1] }
---
```

`tools/tests/fixtures/invalid/frontmatter/bad-status.md`: same as `missing-id.md` but include `id: POL-IAM-TEST` and set `status: pending`.

`tools/tests/fixtures/invalid/frontmatter/bad-version.md`: same as `missing-id.md` but include `id: POL-IAM-TEST` and set `version: 1.0`.

- [ ] **Step 3: Write failing tests**

`tools/ggi_policy/result.py`:

```python
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class ValidationFinding:
    code: str           # short stable code, e.g., "FRONTMATTER_INVALID"
    path: Path
    message: str
    locator: str = ""   # JSON-pointer or rule sub-id, optional


@dataclass
class ValidationReport:
    findings: list[ValidationFinding] = field(default_factory=list)

    def add(self, finding: ValidationFinding) -> None:
        self.findings.append(finding)

    @property
    def ok(self) -> bool:
        return not self.findings
```

`tools/tests/test_validate_frontmatter.py`:

```python
from pathlib import Path

from ggi_policy import io
from ggi_policy.result import ValidationReport
from ggi_policy.validate import frontmatter as fm


def test_valid_policy_yields_no_findings(fixtures_dir: Path) -> None:
    policy = io.load_policy(fixtures_dir / "valid/policies/identity-and-access/group-naming.md")
    report = ValidationReport()
    fm.check(policy, report)
    assert report.ok, [f.message for f in report.findings]


def test_missing_id_is_reported(fixtures_dir: Path) -> None:
    policy = io.load_policy(fixtures_dir / "invalid/frontmatter/missing-id.md")
    report = ValidationReport()
    fm.check(policy, report)
    assert not report.ok
    codes = {f.code for f in report.findings}
    assert "FRONTMATTER_INVALID" in codes


def test_bad_status_is_reported(fixtures_dir: Path) -> None:
    policy = io.load_policy(fixtures_dir / "invalid/frontmatter/bad-status.md")
    report = ValidationReport()
    fm.check(policy, report)
    assert any("status" in f.message for f in report.findings)


def test_bad_version_is_reported(fixtures_dir: Path) -> None:
    policy = io.load_policy(fixtures_dir / "invalid/frontmatter/bad-version.md")
    report = ValidationReport()
    fm.check(policy, report)
    assert any("version" in f.message for f in report.findings)
```

- [ ] **Step 4: Run tests to verify failure**

```bash
uv run pytest tools/tests/test_validate_frontmatter.py -v
```

Expected: import error for `ggi_policy.validate.frontmatter`.

- [ ] **Step 5: Implement the validator**

Create `tools/ggi_policy/validate/__init__.py` (empty).

Create `tools/ggi_policy/validate/frontmatter.py`:

```python
import json
from functools import cache
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

from ggi_policy.io import LoadedPolicy
from ggi_policy.repo import repo_root
from ggi_policy.result import ValidationFinding, ValidationReport


@cache
def _validator() -> Draft202012Validator:
    schema_path = repo_root() / "schemas" / "policy-frontmatter.schema.json"
    schema = json.loads(schema_path.read_text())
    return Draft202012Validator(schema, format_checker=FormatChecker())


def check(policy: LoadedPolicy, report: ValidationReport) -> None:
    for err in _validator().iter_errors(policy.metadata):
        path = "/".join(str(p) for p in err.absolute_path) or "(root)"
        report.add(ValidationFinding(
            code="FRONTMATTER_INVALID",
            path=policy.path,
            message=f"{path}: {err.message}",
            locator=path,
        ))
```

- [ ] **Step 6: Run tests to verify passing**

```bash
uv run pytest tools/tests/test_validate_frontmatter.py -v
```

Expected: 4 passed.

- [ ] **Step 7: Commit**

```bash
git add schemas/policy-frontmatter.schema.json tools/ggi_policy/result.py \
        tools/ggi_policy/validate tools/tests/test_validate_frontmatter.py \
        tools/tests/fixtures/invalid/frontmatter
git commit -m "feat(validate): policy frontmatter JSON Schema and validator"
```

---

## Task 4: Sidecar rules schema + validator

**Files:**
- Create: `schemas/policy-rules.schema.json`
- Create: `tools/ggi_policy/validate/rules_sidecar.py`
- Create: `tools/tests/test_validate_rules_sidecar.py`
- Create: `tools/tests/fixtures/invalid/rules/duplicate-rule-id.yaml`
- Create: `tools/tests/fixtures/invalid/rules/missing-pattern-for-pattern-type.yaml`

- [ ] **Step 1: Create the rules JSON Schema**

`schemas/policy-rules.schema.json`:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://ggenomics.com/schemas/policy-rules.schema.json",
  "title": "GGI policy sidecar rules",
  "type": "object",
  "additionalProperties": false,
  "required": ["policy_id", "rules"],
  "properties": {
    "policy_id": { "type": "string", "pattern": "^POL-[A-Z]+-[A-Z0-9-]+$" },
    "rules": {
      "type": "array",
      "minItems": 1,
      "items": { "$ref": "#/$defs/rule" }
    }
  },
  "$defs": {
    "rule": {
      "type": "object",
      "required": ["id", "statement", "type", "severity"],
      "properties": {
        "id":        { "type": "string", "pattern": "^R\\d+$" },
        "statement": { "type": "string", "minLength": 1 },
        "severity":  { "enum": ["required", "recommended"] },
        "status":    { "enum": ["active", "removed"], "default": "active" },
        "removed_in":{ "type": "string", "pattern": "^\\d+\\.\\d+\\.\\d+$" },
        "type":      { "enum": ["flag","setting","pattern","decision_table","allowed_values","forbidden_values"] },
        "applies_to":{ "type": "object" },
        "pattern":   { "type": "string" },
        "rows":      { "type": "array" },
        "inputs":    { "type": "array", "items": { "type": "string" } },
        "expected":  { "type": "object" },
        "value":     {},
        "allowed":   { "type": "array" },
        "forbidden": { "type": "array" },
        "examples":  { "type": "object" }
      },
      "allOf": [
        { "if": { "properties": { "type": { "const": "pattern" } } },
          "then": { "required": ["pattern"] } },
        { "if": { "properties": { "type": { "const": "decision_table" } } },
          "then": { "required": ["inputs", "rows"] } },
        { "if": { "properties": { "type": { "const": "allowed_values" } } },
          "then": { "required": ["allowed"] } },
        { "if": { "properties": { "type": { "const": "forbidden_values" } } },
          "then": { "required": ["forbidden"] } },
        { "if": { "properties": { "status": { "const": "removed" } } },
          "then": { "required": ["removed_in"] } }
      ]
    }
  }
}
```

- [ ] **Step 2: Create invalid rule fixtures**

`tools/tests/fixtures/invalid/rules/duplicate-rule-id.yaml`:

```yaml
policy_id: POL-IAM-TEST
rules:
  - { id: R1, statement: "first",  type: flag, severity: required }
  - { id: R1, statement: "second", type: flag, severity: required }
```

`tools/tests/fixtures/invalid/rules/missing-pattern-for-pattern-type.yaml`:

```yaml
policy_id: POL-IAM-TEST
rules:
  - id: R1
    statement: "Names must match pattern."
    type: pattern
    severity: required
    # pattern field missing — should fail conditional schema
```

- [ ] **Step 3: Write failing tests**

`tools/tests/test_validate_rules_sidecar.py`:

```python
from pathlib import Path

import yaml

from ggi_policy.result import ValidationReport
from ggi_policy.validate import rules_sidecar


def test_valid_rules_yield_no_findings(fixtures_dir: Path) -> None:
    path = fixtures_dir / "valid/policies/identity-and-access/group-naming.rules.yaml"
    rules = yaml.safe_load(path.read_text())
    report = ValidationReport()
    rules_sidecar.check(path, rules, report)
    assert report.ok, [f.message for f in report.findings]


def test_duplicate_rule_id_is_reported(fixtures_dir: Path) -> None:
    path = fixtures_dir / "invalid/rules/duplicate-rule-id.yaml"
    rules = yaml.safe_load(path.read_text())
    report = ValidationReport()
    rules_sidecar.check(path, rules, report)
    codes = {f.code for f in report.findings}
    assert "RULE_ID_DUPLICATE" in codes


def test_missing_pattern_for_pattern_type_is_reported(fixtures_dir: Path) -> None:
    path = fixtures_dir / "invalid/rules/missing-pattern-for-pattern-type.yaml"
    rules = yaml.safe_load(path.read_text())
    report = ValidationReport()
    rules_sidecar.check(path, rules, report)
    codes = {f.code for f in report.findings}
    assert "RULES_INVALID" in codes
```

- [ ] **Step 4: Run failing tests**

```bash
uv run pytest tools/tests/test_validate_rules_sidecar.py -v
```

Expected: import error.

- [ ] **Step 5: Implement the validator**

`tools/ggi_policy/validate/rules_sidecar.py`:

```python
import json
from collections import Counter
from functools import cache
from pathlib import Path

from jsonschema import Draft202012Validator

from ggi_policy.repo import repo_root
from ggi_policy.result import ValidationFinding, ValidationReport


@cache
def _validator() -> Draft202012Validator:
    schema_path = repo_root() / "schemas" / "policy-rules.schema.json"
    return Draft202012Validator(json.loads(schema_path.read_text()))


def check(path: Path, rules: dict, report: ValidationReport) -> None:
    for err in _validator().iter_errors(rules):
        loc = "/".join(str(p) for p in err.absolute_path) or "(root)"
        report.add(ValidationFinding(
            code="RULES_INVALID",
            path=path,
            message=f"{loc}: {err.message}",
            locator=loc,
        ))

    counts = Counter(r["id"] for r in rules.get("rules", []) if isinstance(r, dict) and "id" in r)
    for rule_id, n in counts.items():
        if n > 1:
            report.add(ValidationFinding(
                code="RULE_ID_DUPLICATE",
                path=path,
                message=f"rule id {rule_id!r} appears {n} times; sub-IDs must be unique within a sidecar",
                locator=rule_id,
            ))
```

- [ ] **Step 6: Run tests to verify passing**

```bash
uv run pytest tools/tests/test_validate_rules_sidecar.py -v
```

Expected: 3 passed.

- [ ] **Step 7: Commit**

```bash
git add schemas/policy-rules.schema.json tools/ggi_policy/validate/rules_sidecar.py \
        tools/tests/test_validate_rules_sidecar.py tools/tests/fixtures/invalid/rules
git commit -m "feat(validate): sidecar rules JSON Schema and validator with duplicate-id check"
```

---

## Task 5: Exception schema + validator (cap + policy_ref)

**Files:**
- Create: `schemas/exception.schema.json`
- Create: `tools/ggi_policy/validate/exceptions.py`
- Create: `tools/tests/test_validate_exceptions.py`
- Create: `tools/tests/fixtures/invalid/exceptions/cap-exceeded-required.md`
- Create: `tools/tests/fixtures/invalid/exceptions/cap-exceeded-recommended.md`
- Create: `tools/tests/fixtures/invalid/exceptions/dangling-policy-ref.md`

- [ ] **Step 1: Create the exception JSON Schema**

`schemas/exception.schema.json`:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://ggenomics.com/schemas/exception.schema.json",
  "title": "GGI policy exception",
  "type": "object",
  "additionalProperties": false,
  "required": [
    "id", "policy_ref", "requested_by", "approver",
    "approved_date", "effective_date", "expires", "status",
    "compensating_control", "risk_acceptance"
  ],
  "properties": {
    "id":              { "type": "string", "pattern": "^EXC-\\d{4}-\\d{3}-[A-Z0-9-]+$" },
    "policy_ref":      { "type": "string", "pattern": "^POL-[A-Z]+-[A-Z0-9-]+\\.R\\d+$" },
    "requested_by":    { "type": "string", "format": "email" },
    "approver":        { "type": "string", "minLength": 1 },
    "approved_date":   { "type": "string", "format": "date" },
    "effective_date":  { "type": "string", "format": "date" },
    "expires":         { "type": "string", "format": "date" },
    "status":          { "enum": ["active", "expired", "revoked"] },
    "compensating_control": { "type": "string", "minLength": 1 },
    "risk_acceptance":      { "type": "string", "minLength": 1 }
  }
}
```

- [ ] **Step 2: Create invalid exception fixtures**

`tools/tests/fixtures/invalid/exceptions/cap-exceeded-required.md`: copy of the valid exception but with `expires: 2027-01-15` (9 months > 6-month cap for `required` rules — `R1` in the valid sidecar is required).

`tools/tests/fixtures/invalid/exceptions/cap-exceeded-recommended.md`: a fixture referencing a `recommended` rule sub-id with `expires - effective_date > 18 months`.

To support this, add a `recommended` rule to the valid sidecar fixture? No — keep fixtures isolated. Create a tiny dedicated fixture:

`tools/tests/fixtures/invalid/exceptions/_recommended-rule-policy.md`:

```markdown
---
id: POL-DAT-TEST
title: Test
summary: Test policy with one recommended rule.
domain: DAT
status: effective
version: 1.0.0
effective_date: 2026-06-01
last_reviewed: 2026-05-01
review_cycle: annual
owner: Data Steward
approvers: [Data Steward]
applies_to: [test]
frameworks: { nist_csf: [PR.AC-1] }
---
# Test
```

`tools/tests/fixtures/invalid/exceptions/_recommended-rule-policy.rules.yaml`:

```yaml
policy_id: POL-DAT-TEST
rules:
  - { id: R1, statement: "soft rule", type: flag, severity: recommended }
```

`tools/tests/fixtures/invalid/exceptions/cap-exceeded-recommended.md`:

```markdown
---
id: EXC-2026-002-CAP-RECOMMENDED
policy_ref: POL-DAT-TEST.R1
requested_by: jane.doe@ggenomics.com
approver: CISO
approved_date: 2026-04-15
effective_date: 2026-04-15
expires: 2028-01-15
status: active
compensating_control: n/a
risk_acceptance: accepted
---
```

`tools/tests/fixtures/invalid/exceptions/dangling-policy-ref.md`:

```markdown
---
id: EXC-2026-003-DANGLING
policy_ref: POL-IAM-DOES-NOT-EXIST.R1
requested_by: jane.doe@ggenomics.com
approver: CISO
approved_date: 2026-04-15
effective_date: 2026-04-15
expires: 2026-07-15
status: active
compensating_control: n/a
risk_acceptance: accepted
---
```

- [ ] **Step 3: Write failing tests**

`tools/tests/test_validate_exceptions.py`:

```python
from pathlib import Path

from ggi_policy import io
from ggi_policy.result import ValidationReport
from ggi_policy.validate import exceptions as exc_validate


def _build_rule_index(fixtures_dir: Path) -> dict[str, dict]:
    """Walk valid fixtures + the auxiliary recommended-rule policy to build a sub-id -> rule map."""
    index: dict[str, dict] = {}
    for policy in io.iter_policies(fixtures_dir / "valid/policies"):
        rules = io.load_rules(policy.path)
        if not rules:
            continue
        for rule in rules["rules"]:
            index[f"{rules['policy_id']}.{rule['id']}"] = rule
    aux_policy = fixtures_dir / "invalid/exceptions/_recommended-rule-policy.md"
    aux_rules = io.load_rules(aux_policy)
    if aux_rules:
        for rule in aux_rules["rules"]:
            index[f"{aux_rules['policy_id']}.{rule['id']}"] = rule
    return index


def test_valid_exception_yields_no_findings(fixtures_dir: Path) -> None:
    rule_index = _build_rule_index(fixtures_dir)
    exc = io.load_exception(fixtures_dir / "valid/exceptions/EXC-2026-001-finance-legacy-group.md")
    report = ValidationReport()
    exc_validate.check(exc, rule_index, report)
    assert report.ok, [f.message for f in report.findings]


def test_cap_exceeded_for_required_rule(fixtures_dir: Path) -> None:
    rule_index = _build_rule_index(fixtures_dir)
    exc = io.load_exception(fixtures_dir / "invalid/exceptions/cap-exceeded-required.md")
    report = ValidationReport()
    exc_validate.check(exc, rule_index, report)
    codes = {f.code for f in report.findings}
    assert "EXCEPTION_CAP_EXCEEDED" in codes


def test_cap_exceeded_for_recommended_rule(fixtures_dir: Path) -> None:
    rule_index = _build_rule_index(fixtures_dir)
    exc = io.load_exception(fixtures_dir / "invalid/exceptions/cap-exceeded-recommended.md")
    report = ValidationReport()
    exc_validate.check(exc, rule_index, report)
    codes = {f.code for f in report.findings}
    assert "EXCEPTION_CAP_EXCEEDED" in codes


def test_dangling_policy_ref_is_reported(fixtures_dir: Path) -> None:
    rule_index = _build_rule_index(fixtures_dir)
    exc = io.load_exception(fixtures_dir / "invalid/exceptions/dangling-policy-ref.md")
    report = ValidationReport()
    exc_validate.check(exc, rule_index, report)
    codes = {f.code for f in report.findings}
    assert "EXCEPTION_DANGLING_REF" in codes
```

- [ ] **Step 4: Run failing tests**

```bash
uv run pytest tools/tests/test_validate_exceptions.py -v
```

Expected: import error.

- [ ] **Step 5: Implement the validator**

`tools/ggi_policy/validate/exceptions.py`:

```python
import json
from datetime import date, datetime
from functools import cache

from jsonschema import Draft202012Validator, FormatChecker

from ggi_policy.io import LoadedException
from ggi_policy.repo import repo_root
from ggi_policy.result import ValidationFinding, ValidationReport


CAP_DAYS_REQUIRED = 6 * 30      # ~6 months
CAP_DAYS_RECOMMENDED = 18 * 30  # ~18 months


@cache
def _validator() -> Draft202012Validator:
    schema_path = repo_root() / "schemas" / "exception.schema.json"
    return Draft202012Validator(json.loads(schema_path.read_text()), format_checker=FormatChecker())


def _as_date(value) -> date | None:
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return datetime.strptime(value, "%Y-%m-%d").date()
        except ValueError:
            return None
    return None


def check(exc: LoadedException, rule_index: dict[str, dict], report: ValidationReport) -> None:
    # 1. Schema validation
    schema_errors = list(_validator().iter_errors(exc.metadata))
    for err in schema_errors:
        loc = "/".join(str(p) for p in err.absolute_path) or "(root)"
        report.add(ValidationFinding(
            code="EXCEPTION_INVALID",
            path=exc.path,
            message=f"{loc}: {err.message}",
            locator=loc,
        ))
    # If schema fails, the rest of the checks may not be meaningful. Still try them.

    # 2. Dangling policy_ref
    ref = exc.metadata.get("policy_ref")
    rule = rule_index.get(ref) if ref else None
    if ref and rule is None:
        report.add(ValidationFinding(
            code="EXCEPTION_DANGLING_REF",
            path=exc.path,
            message=f"policy_ref {ref!r} does not match any known rule sub-ID",
            locator="policy_ref",
        ))

    # 3. Tiered cap based on referenced rule's severity
    eff = _as_date(exc.metadata.get("effective_date"))
    expires = _as_date(exc.metadata.get("expires"))
    if rule is not None and eff and expires:
        severity = rule.get("severity")
        cap = CAP_DAYS_REQUIRED if severity == "required" else CAP_DAYS_RECOMMENDED
        if (expires - eff).days > cap:
            report.add(ValidationFinding(
                code="EXCEPTION_CAP_EXCEEDED",
                path=exc.path,
                message=(
                    f"exception duration {(expires - eff).days} days exceeds cap of {cap} days "
                    f"for severity={severity!r}"
                ),
                locator="expires",
            ))
```

- [ ] **Step 6: Run tests to verify passing**

```bash
uv run pytest tools/tests/test_validate_exceptions.py -v
```

Expected: 4 passed.

- [ ] **Step 7: Commit**

```bash
git add schemas/exception.schema.json tools/ggi_policy/validate/exceptions.py \
        tools/tests/test_validate_exceptions.py tools/tests/fixtures/invalid/exceptions
git commit -m "feat(validate): exception schema, dangling-ref check, and tiered duration cap"
```

---

## Task 6: ID ↔ filename ↔ folder consistency

**Files:**
- Create: `tools/ggi_policy/validate/consistency.py`
- Create: `tools/tests/test_validate_consistency.py`
- Create: `tools/tests/fixtures/invalid/consistency/policies/data/group-naming.md` (wrong domain folder)
- Create: `tools/tests/fixtures/invalid/consistency/policies/identity-and-access/wrong-name.md` (filename ≠ id slug)

- [ ] **Step 1: Create the wrong-folder fixture**

`tools/tests/fixtures/invalid/consistency/policies/data/group-naming.md`: a copy of the valid policy fixture but placed in `data/`. (Same `id: POL-IAM-GROUP-NAMING` and `domain: IAM` but in `policies/data/`.)

- [ ] **Step 2: Create the filename-mismatch fixture**

`tools/tests/fixtures/invalid/consistency/policies/identity-and-access/wrong-name.md`: a copy of the valid policy fixture (frontmatter says `id: POL-IAM-GROUP-NAMING`) but saved under filename `wrong-name.md`.

- [ ] **Step 3: Write failing tests**

`tools/tests/test_validate_consistency.py`:

```python
from pathlib import Path

from ggi_policy import io
from ggi_policy.result import ValidationReport
from ggi_policy.validate import consistency

DOMAIN_TO_FOLDER = {
    "IAM": "identity-and-access",
    "DAT": "data",
    "PRV": "privacy",
    "APP": "applications",
    "END": "endpoints",
    "NET": "network",
    "IR":  "incident-response",
    "VND": "vendor-and-third-party",
    "SEC": "security-operations",
    "BCP": "business-continuity",
    "HR":  "human-resources",
    "META":"meta",
}


def test_valid_policy_passes(fixtures_dir: Path) -> None:
    policy = io.load_policy(fixtures_dir / "valid/policies/identity-and-access/group-naming.md")
    report = ValidationReport()
    consistency.check(policy, fixtures_dir / "valid/policies", DOMAIN_TO_FOLDER, report)
    assert report.ok


def test_wrong_folder_for_domain_is_reported(fixtures_dir: Path) -> None:
    policy = io.load_policy(fixtures_dir / "invalid/consistency/policies/data/group-naming.md")
    report = ValidationReport()
    consistency.check(policy, fixtures_dir / "invalid/consistency/policies", DOMAIN_TO_FOLDER, report)
    codes = {f.code for f in report.findings}
    assert "POLICY_WRONG_FOLDER" in codes


def test_filename_mismatch_is_reported(fixtures_dir: Path) -> None:
    policy = io.load_policy(fixtures_dir / "invalid/consistency/policies/identity-and-access/wrong-name.md")
    report = ValidationReport()
    consistency.check(policy, fixtures_dir / "invalid/consistency/policies", DOMAIN_TO_FOLDER, report)
    codes = {f.code for f in report.findings}
    assert "POLICY_FILENAME_MISMATCH" in codes
```

- [ ] **Step 4: Run failing tests**

```bash
uv run pytest tools/tests/test_validate_consistency.py -v
```

Expected: import error.

- [ ] **Step 5: Implement the validator**

`tools/ggi_policy/validate/consistency.py`:

```python
from pathlib import Path

from ggi_policy.io import LoadedPolicy
from ggi_policy.result import ValidationFinding, ValidationReport


def _id_to_slug(policy_id: str) -> str:
    """POL-IAM-GROUP-NAMING -> group-naming"""
    parts = policy_id.split("-", 2)
    return parts[2].lower() if len(parts) == 3 else ""


def check(
    policy: LoadedPolicy,
    policies_root: Path,
    domain_to_folder: dict[str, str],
    report: ValidationReport,
) -> None:
    metadata = policy.metadata
    pid = metadata.get("id", "")
    domain = metadata.get("domain", "")
    expected_folder_name = domain_to_folder.get(domain)
    expected_slug = _id_to_slug(pid)

    rel = policy.path.relative_to(policies_root)
    actual_folder = rel.parts[0] if len(rel.parts) >= 2 else ""
    actual_filename_stem = policy.path.stem

    if expected_folder_name and actual_folder != expected_folder_name:
        report.add(ValidationFinding(
            code="POLICY_WRONG_FOLDER",
            path=policy.path,
            message=(
                f"domain={domain!r} requires folder {expected_folder_name!r}; "
                f"file is in {actual_folder!r}"
            ),
            locator="domain",
        ))

    if expected_slug and actual_filename_stem != expected_slug:
        report.add(ValidationFinding(
            code="POLICY_FILENAME_MISMATCH",
            path=policy.path,
            message=(
                f"id={pid!r} requires filename {expected_slug!r}.md; "
                f"actual stem is {actual_filename_stem!r}"
            ),
            locator="id",
        ))
```

- [ ] **Step 6: Run tests to verify passing**

```bash
uv run pytest tools/tests/test_validate_consistency.py -v
```

Expected: 3 passed.

- [ ] **Step 7: Commit**

```bash
git add tools/ggi_policy/validate/consistency.py \
        tools/tests/test_validate_consistency.py \
        tools/tests/fixtures/invalid/consistency
git commit -m "feat(validate): ID ↔ filename ↔ folder consistency check"
```

---

## Task 7: CODEOWNERS + role-team-mapping + approvers reconciliation

**Files:**
- Create: `schemas/role-team-mapping.schema.json`
- Create: `schemas/role-team-mapping.yaml`
- Create: `.github/CODEOWNERS`
- Create: `tools/ggi_policy/codeowners.py`
- Create: `tools/ggi_policy/role_team_map.py`
- Create: `tools/ggi_policy/validate/approvers.py`
- Create: `tools/tests/test_codeowners.py`
- Create: `tools/tests/test_role_team_map.py`
- Create: `tools/tests/test_validate_approvers.py`
- Create: `tools/tests/fixtures/invalid/approvers/policies/identity-and-access/bad-approver.md`

- [ ] **Step 1: Create the role-team-mapping JSON Schema**

`schemas/role-team-mapping.schema.json`:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://ggenomics.com/schemas/role-team-mapping.schema.json",
  "type": "object",
  "additionalProperties": false,
  "required": ["roles"],
  "properties": {
    "roles": {
      "type": "object",
      "additionalProperties": { "type": "string", "pattern": "^@[A-Za-z0-9_-]+/[A-Za-z0-9_-]+$" }
    }
  }
}
```

- [ ] **Step 2: Create the canonical role-team mapping**

`schemas/role-team-mapping.yaml`:

```yaml
roles:
  CISO:             "@ggenomics/ciso"
  IT Director:      "@ggenomics/it-director"
  Data Steward:     "@ggenomics/data-steward"
  HR Director:      "@ggenomics/hr-director"
  Privacy Officer:  "@ggenomics/privacy-officer"
  Policy Stewards:  "@ggenomics/policy-stewards"
```

- [ ] **Step 3: Create CODEOWNERS**

`.github/CODEOWNERS`:

```
# Each policy folder is owned by the teams listed for that domain in §7.3
/policies/identity-and-access/      @ggenomics/ciso @ggenomics/it-director
/policies/data/                     @ggenomics/ciso @ggenomics/data-steward
/policies/privacy/                  @ggenomics/ciso @ggenomics/privacy-officer
/policies/human-resources/          @ggenomics/ciso @ggenomics/hr-director
/policies/applications/             @ggenomics/ciso @ggenomics/it-director
/policies/endpoints/                @ggenomics/ciso @ggenomics/it-director
/policies/network/                  @ggenomics/ciso @ggenomics/it-director
/policies/incident-response/        @ggenomics/ciso
/policies/vendor-and-third-party/   @ggenomics/ciso
/policies/security-operations/      @ggenomics/ciso
/policies/business-continuity/      @ggenomics/ciso @ggenomics/it-director
/policies/meta/                     @ggenomics/ciso @ggenomics/it-director @ggenomics/policy-stewards
/exceptions/                        @ggenomics/ciso
/schemas/                           @ggenomics/ciso @ggenomics/policy-stewards
/tools/                             @ggenomics/policy-stewards
/crosswalks/                        @ggenomics/policy-stewards
```

- [ ] **Step 4: Write CODEOWNERS parser tests**

`tools/tests/test_codeowners.py`:

```python
from pathlib import Path

from ggi_policy import codeowners


def test_parse_simple(tmp_path: Path) -> None:
    f = tmp_path / "CODEOWNERS"
    f.write_text(
        "# comment\n"
        "/policies/data/   @ggenomics/ciso @ggenomics/data-steward\n"
        "/exceptions/      @ggenomics/ciso\n"
    )
    rules = codeowners.parse(f)
    assert rules == [
        ("/policies/data/", ["@ggenomics/ciso", "@ggenomics/data-steward"]),
        ("/exceptions/",    ["@ggenomics/ciso"]),
    ]


def test_owners_for_path_picks_longest_prefix(tmp_path: Path) -> None:
    f = tmp_path / "CODEOWNERS"
    f.write_text(
        "/policies/                    @ggenomics/everyone\n"
        "/policies/identity-and-access/ @ggenomics/ciso @ggenomics/it-director\n"
    )
    rules = codeowners.parse(f)
    owners = codeowners.owners_for("policies/identity-and-access/group-naming.md", rules)
    assert owners == ["@ggenomics/ciso", "@ggenomics/it-director"]
```

- [ ] **Step 5: Implement `codeowners.py`**

`tools/ggi_policy/codeowners.py`:

```python
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
```

Run:

```bash
uv run pytest tools/tests/test_codeowners.py -v
```

Expected: 2 passed.

- [ ] **Step 6: Write role-team-map tests**

`tools/tests/test_role_team_map.py`:

```python
from ggi_policy import role_team_map


def test_load_and_resolve(fixtures_dir, tmp_path):  # type: ignore[no-untyped-def]
    f = tmp_path / "role-team-mapping.yaml"
    f.write_text("roles:\n  CISO: \"@ggenomics/ciso\"\n  IT Director: \"@ggenomics/it-director\"\n")
    mapping = role_team_map.load(f)
    assert mapping["CISO"] == "@ggenomics/ciso"
    assert mapping["IT Director"] == "@ggenomics/it-director"


def test_resolve_unknown_returns_none(tmp_path):  # type: ignore[no-untyped-def]
    f = tmp_path / "role-team-mapping.yaml"
    f.write_text("roles:\n  CISO: \"@ggenomics/ciso\"\n")
    mapping = role_team_map.load(f)
    assert mapping.get("Unknown") is None
```

- [ ] **Step 7: Implement `role_team_map.py`**

`tools/ggi_policy/role_team_map.py`:

```python
from pathlib import Path

import yaml


def load(path: Path) -> dict[str, str]:
    data = yaml.safe_load(path.read_text())
    return dict(data.get("roles", {}))
```

Run:

```bash
uv run pytest tools/tests/test_role_team_map.py -v
```

Expected: 2 passed.

- [ ] **Step 8: Create the bad-approver fixture**

`tools/tests/fixtures/invalid/approvers/policies/identity-and-access/bad-approver.md`: copy of the valid policy fixture but with `approvers: [Unknown Role]`.

Add a CODEOWNERS for the test:

`tools/tests/fixtures/invalid/approvers/CODEOWNERS`:

```
/policies/identity-and-access/   @ggenomics/ciso @ggenomics/it-director
```

Add a role-team-mapping for the test:

`tools/tests/fixtures/invalid/approvers/role-team-mapping.yaml`:

```yaml
roles:
  CISO:        "@ggenomics/ciso"
  IT Director: "@ggenomics/it-director"
```

- [ ] **Step 9: Write failing test**

`tools/tests/test_validate_approvers.py`:

```python
from pathlib import Path

from ggi_policy import codeowners, io, role_team_map
from ggi_policy.result import ValidationReport
from ggi_policy.validate import approvers as approvers_validate


def test_approvers_subset_of_codeowners_passes(fixtures_dir: Path) -> None:
    policy = io.load_policy(fixtures_dir / "valid/policies/identity-and-access/group-naming.md")
    rules = codeowners.parse(fixtures_dir.parent.parent.parent / ".github" / "CODEOWNERS")
    mapping = role_team_map.load(fixtures_dir.parent.parent.parent / "schemas" / "role-team-mapping.yaml")
    report = ValidationReport()
    approvers_validate.check(policy, rules, mapping, fixtures_dir / "valid", report)
    assert report.ok, [f.message for f in report.findings]


def test_unknown_approver_role_is_reported(fixtures_dir: Path) -> None:
    policy = io.load_policy(fixtures_dir / "invalid/approvers/policies/identity-and-access/bad-approver.md")
    rules = codeowners.parse(fixtures_dir / "invalid/approvers/CODEOWNERS")
    mapping = role_team_map.load(fixtures_dir / "invalid/approvers/role-team-mapping.yaml")
    report = ValidationReport()
    approvers_validate.check(policy, rules, mapping, fixtures_dir / "invalid/approvers", report)
    codes = {f.code for f in report.findings}
    assert "APPROVER_UNKNOWN_ROLE" in codes
```

- [ ] **Step 10: Implement the approvers validator**

`tools/ggi_policy/validate/approvers.py`:

```python
from pathlib import Path

from ggi_policy import codeowners
from ggi_policy.io import LoadedPolicy
from ggi_policy.result import ValidationFinding, ValidationReport


def check(
    policy: LoadedPolicy,
    codeowner_rules: list[tuple[str, list[str]]],
    role_to_team: dict[str, str],
    repo_root: Path,
    report: ValidationReport,
) -> None:
    approvers = policy.metadata.get("approvers", [])
    rel = policy.path.relative_to(repo_root).as_posix()
    expected_owners = set(codeowners.owners_for(rel, codeowner_rules))
    if not expected_owners:
        report.add(ValidationFinding(
            code="APPROVER_NO_CODEOWNERS_RULE",
            path=policy.path,
            message=f"no CODEOWNERS rule covers path {rel!r}",
            locator="approvers",
        ))
        return

    for role in approvers:
        team = role_to_team.get(role)
        if team is None:
            report.add(ValidationFinding(
                code="APPROVER_UNKNOWN_ROLE",
                path=policy.path,
                message=f"approver role {role!r} is not declared in role-team-mapping.yaml",
                locator=f"approvers/{role}",
            ))
            continue
        if team not in expected_owners:
            report.add(ValidationFinding(
                code="APPROVER_NOT_IN_CODEOWNERS",
                path=policy.path,
                message=(
                    f"approver {role!r} → {team!r} is not in the CODEOWNERS owners "
                    f"({sorted(expected_owners)}) for path {rel!r}"
                ),
                locator=f"approvers/{role}",
            ))
```

- [ ] **Step 11: Run tests to verify passing**

```bash
uv run pytest tools/tests/test_validate_approvers.py -v
```

Expected: 2 passed.

- [ ] **Step 12: Commit**

```bash
git add schemas/role-team-mapping.schema.json schemas/role-team-mapping.yaml \
        .github/CODEOWNERS \
        tools/ggi_policy/codeowners.py tools/ggi_policy/role_team_map.py \
        tools/ggi_policy/validate/approvers.py \
        tools/tests/test_codeowners.py tools/tests/test_role_team_map.py \
        tools/tests/test_validate_approvers.py \
        tools/tests/fixtures/invalid/approvers
git commit -m "feat(validate): CODEOWNERS / role-team-mapping / approvers reconciliation"
```

---

## Task 8: Framework tag format validation

The frontmatter schema already enforces per-framework regex patterns. This task adds a *cross-cutting* check that surfaces tag-format issues with a stable code (`TAG_FORMAT_INVALID`) for the runner output, rather than the generic `FRONTMATTER_INVALID`. Membership validation against `framework-controls.json` is **deferred to Phase 2** — Phase 1 only validates *format*.

**Files:**
- Create: `tools/ggi_policy/validate/tags.py`
- Create: `tools/tests/test_validate_tags.py`
- Create: `tools/tests/fixtures/invalid/tags/policies/identity-and-access/bad-csf.md` (e.g., `nist_csf: [WRONG-FORMAT-1]`)

- [ ] **Step 1: Create the bad-tag fixture**

`tools/tests/fixtures/invalid/tags/policies/identity-and-access/bad-csf.md`: copy of the valid policy fixture, but `frameworks.nist_csf: [WRONGFMT-1]`.

- [ ] **Step 2: Write failing test**

`tools/tests/test_validate_tags.py`:

```python
from pathlib import Path

from ggi_policy import io
from ggi_policy.result import ValidationReport
from ggi_policy.validate import tags


def test_valid_tags_yield_no_findings(fixtures_dir: Path) -> None:
    policy = io.load_policy(fixtures_dir / "valid/policies/identity-and-access/group-naming.md")
    report = ValidationReport()
    tags.check(policy, report)
    assert report.ok


def test_bad_csf_tag_is_reported(fixtures_dir: Path) -> None:
    policy = io.load_policy(fixtures_dir / "invalid/tags/policies/identity-and-access/bad-csf.md")
    report = ValidationReport()
    tags.check(policy, report)
    codes = {f.code for f in report.findings}
    assert "TAG_FORMAT_INVALID" in codes
```

- [ ] **Step 3: Implement the tags validator**

`tools/ggi_policy/validate/tags.py`:

```python
import re

from ggi_policy.io import LoadedPolicy
from ggi_policy.result import ValidationFinding, ValidationReport


PATTERNS = {
    "nist_csf":     re.compile(r"^(GV|ID|PR|DE|RS|RC)\.[A-Z]{2}-\d+$"),
    "cis":          re.compile(r"^\d+(\.\d+)?$"),
    "soc2":         re.compile(r"^(CC|A|PI|C|P)\d+\.\d+$"),
    "hipaa":        re.compile(r"^164\.\d{3}\([a-z]\)(\(\d+\))?(\([ivx]+\))?$"),
    "nist_800_53":  re.compile(r"^[A-Z]{2}-\d+(\(\d+\))?$"),
    "nist_800_171": re.compile(r"^\d+\.\d+\.\d+$"),
}


def check(policy: LoadedPolicy, report: ValidationReport) -> None:
    for framework, values in policy.metadata.get("frameworks", {}).items():
        pattern = PATTERNS.get(framework)
        if pattern is None:
            continue  # frontmatter schema covers unknown framework keys
        for value in values or []:
            if not pattern.match(str(value)):
                report.add(ValidationFinding(
                    code="TAG_FORMAT_INVALID",
                    path=policy.path,
                    message=f"frameworks.{framework}: {value!r} does not match expected format",
                    locator=f"frameworks/{framework}",
                ))
```

- [ ] **Step 4: Run tests to verify passing**

```bash
uv run pytest tools/tests/test_validate_tags.py -v
```

Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add tools/ggi_policy/validate/tags.py tools/tests/test_validate_tags.py \
        tools/tests/fixtures/invalid/tags
git commit -m "feat(validate): per-framework tag format check (membership deferred to Phase 2)"
```

---

## Task 9: Removed-rule numbers integrity

Numbers (`R1`, `R2`, ...) must never be reused once removed. Within a single sidecar this is trivial (Task 4 handles duplicates). Across versions, the only way we can detect "reuse" is when the sidecar contains both the removed marker and a live entry sharing the same id. Phase 1 implements that within-file check; deeper history-aware checks are deferred to Phase 5.

**Files:**
- Create: `tools/ggi_policy/validate/removed_rules.py`
- Create: `tools/tests/test_validate_removed_rules.py`
- Create: `tools/tests/fixtures/invalid/rules/reused-removed-number.yaml`

- [ ] **Step 1: Create the reused-removed-number fixture**

`tools/tests/fixtures/invalid/rules/reused-removed-number.yaml`:

```yaml
policy_id: POL-IAM-TEST
rules:
  - { id: R1, statement: "old removed rule", type: flag, severity: required, status: removed, removed_in: 1.1.0 }
  - { id: R1, statement: "new live rule",    type: flag, severity: required }
```

- [ ] **Step 2: Write failing test**

`tools/tests/test_validate_removed_rules.py`:

```python
from pathlib import Path

import yaml

from ggi_policy.result import ValidationReport
from ggi_policy.validate import removed_rules


def test_no_reuse_passes(fixtures_dir: Path) -> None:
    path = fixtures_dir / "valid/policies/identity-and-access/group-naming.rules.yaml"
    rules = yaml.safe_load(path.read_text())
    report = ValidationReport()
    removed_rules.check(path, rules, report)
    assert report.ok


def test_reused_removed_number_is_reported(fixtures_dir: Path) -> None:
    path = fixtures_dir / "invalid/rules/reused-removed-number.yaml"
    rules = yaml.safe_load(path.read_text())
    report = ValidationReport()
    removed_rules.check(path, rules, report)
    codes = {f.code for f in report.findings}
    assert "RULE_NUMBER_REUSED" in codes
```

- [ ] **Step 3: Implement the validator**

`tools/ggi_policy/validate/removed_rules.py`:

```python
from pathlib import Path

from ggi_policy.result import ValidationFinding, ValidationReport


def check(path: Path, rules: dict, report: ValidationReport) -> None:
    seen_status: dict[str, set[str]] = {}
    for rule in rules.get("rules", []):
        if not isinstance(rule, dict) or "id" not in rule:
            continue
        rid = rule["id"]
        status = rule.get("status", "active")
        seen_status.setdefault(rid, set()).add(status)
    for rid, statuses in seen_status.items():
        if "removed" in statuses and "active" in statuses:
            report.add(ValidationFinding(
                code="RULE_NUMBER_REUSED",
                path=path,
                message=(
                    f"rule id {rid!r} appears as both 'active' and 'removed' in this sidecar; "
                    f"removed numbers must never be reused"
                ),
                locator=rid,
            ))
```

- [ ] **Step 4: Run tests to verify passing**

```bash
uv run pytest tools/tests/test_validate_removed_rules.py -v
```

Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add tools/ggi_policy/validate/removed_rules.py \
        tools/tests/test_validate_removed_rules.py \
        tools/tests/fixtures/invalid/rules/reused-removed-number.yaml
git commit -m "feat(validate): removed rule numbers must not be reused within a sidecar"
```

---

## Task 10: Validation runner + CLI integration

**Files:**
- Create: `tools/ggi_policy/validate/runner.py`
- Modify: `tools/ggi_policy/cli.py`
- Create: `tools/tests/test_validate_runner.py`
- Create: `tools/tests/test_cli.py`

- [ ] **Step 1: Write the runner test**

`tools/tests/test_validate_runner.py`:

```python
from pathlib import Path

from ggi_policy.validate import runner


def test_runner_on_valid_fixture_tree_yields_no_findings(fixtures_dir: Path) -> None:
    report = runner.run(repo_root=fixtures_dir / "valid", config_root=fixtures_dir.parent.parent.parent)
    # config_root points at the actual repo so CODEOWNERS / role-team-mapping are real.
    assert report.ok, [f.message for f in report.findings]


def test_runner_collects_findings_from_invalid_subset(fixtures_dir: Path, tmp_path: Path) -> None:
    # Build a small synthetic repo combining valid policies + one invalid frontmatter.
    repo = tmp_path / "synth"
    (repo / "policies/identity-and-access").mkdir(parents=True)
    (repo / "exceptions").mkdir()
    (repo / "schemas").mkdir()
    (repo / ".github").mkdir()

    valid_policy = (fixtures_dir / "valid/policies/identity-and-access/group-naming.md").read_text()
    invalid_policy = (fixtures_dir / "invalid/frontmatter/missing-id.md").read_text()
    (repo / "policies/identity-and-access/group-naming.md").write_text(valid_policy)
    (repo / "policies/identity-and-access/missing-id.md").write_text(invalid_policy)

    # Copy through the repo's real schemas + CODEOWNERS + role-team-mapping
    real = fixtures_dir.parent.parent.parent
    for name in ["policy-frontmatter.schema.json", "policy-rules.schema.json",
                 "exception.schema.json", "role-team-mapping.schema.json",
                 "role-team-mapping.yaml"]:
        (repo / "schemas" / name).write_text((real / "schemas" / name).read_text())
    (repo / ".github/CODEOWNERS").write_text((real / ".github/CODEOWNERS").read_text())

    report = runner.run(repo_root=repo, config_root=real)
    assert not report.ok
    codes = {f.code for f in report.findings}
    assert "FRONTMATTER_INVALID" in codes
```

- [ ] **Step 2: Implement the runner**

`tools/ggi_policy/validate/runner.py`:

```python
from pathlib import Path

from ggi_policy import codeowners, io, role_team_map
from ggi_policy.result import ValidationReport
from ggi_policy.validate import (
    approvers, consistency, exceptions as exc_validate, frontmatter as fm,
    removed_rules, rules_sidecar, tags,
)

DOMAIN_TO_FOLDER = {
    "IAM": "identity-and-access", "DAT": "data", "PRV": "privacy",
    "APP": "applications", "END": "endpoints", "NET": "network",
    "IR":  "incident-response", "VND": "vendor-and-third-party",
    "SEC": "security-operations", "BCP": "business-continuity",
    "HR":  "human-resources", "META": "meta",
}


def run(repo_root: Path, config_root: Path | None = None) -> ValidationReport:
    """Run all validation checks against the repo at `repo_root`.

    `config_root` is where shared configs live (CODEOWNERS, role-team-mapping,
    schemas). Defaults to `repo_root` — different in tests that build synthetic
    repos but want to reuse the canonical configs.
    """
    config_root = config_root or repo_root
    report = ValidationReport()

    co_rules = codeowners.parse(config_root / ".github" / "CODEOWNERS")
    role_map = role_team_map.load(config_root / "schemas" / "role-team-mapping.yaml")

    policies_root = repo_root / "policies"
    rule_index: dict[str, dict] = {}
    policies = list(io.iter_policies(policies_root)) if policies_root.exists() else []

    for policy in policies:
        fm.check(policy, report)
        consistency.check(policy, policies_root, DOMAIN_TO_FOLDER, report)
        tags.check(policy, report)
        approvers.check(policy, co_rules, role_map, repo_root, report)
        rules = io.load_rules(policy.path)
        if rules:
            sidecar_path = policy.path.parent / f"{policy.path.stem}.rules.yaml"
            rules_sidecar.check(sidecar_path, rules, report)
            removed_rules.check(sidecar_path, rules, report)
            for rule in rules.get("rules", []):
                if isinstance(rule, dict) and "id" in rule:
                    rule_index[f"{rules['policy_id']}.{rule['id']}"] = rule

    exceptions_root = repo_root / "exceptions"
    if exceptions_root.exists():
        for exc in io.iter_exceptions(exceptions_root):
            exc_validate.check(exc, rule_index, report)

    return report
```

- [ ] **Step 3: Run runner tests**

```bash
uv run pytest tools/tests/test_validate_runner.py -v
```

Expected: 2 passed.

- [ ] **Step 4: Wire the CLI**

Replace `tools/ggi_policy/cli.py` with:

```python
import sys
from pathlib import Path

import click

from ggi_policy.repo import repo_root
from ggi_policy.validate.runner import run


@click.group()
@click.version_option()
def main() -> None:
    """GGI policy documentation framework tooling."""


@main.command()
@click.option(
    "--repo-root", "repo_root_opt",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=None,
    help="Override the repo root (defaults to git rev-parse).",
)
def validate(repo_root_opt: Path | None) -> None:
    """Validate every policy, sidecar, and exception in the repo."""
    root = repo_root_opt or repo_root()
    report = run(repo_root=root, config_root=root)
    if report.ok:
        click.echo(f"OK: validated {root}")
        sys.exit(0)
    for finding in report.findings:
        rel = finding.path.relative_to(root) if finding.path.is_absolute() else finding.path
        click.echo(f"{rel}: [{finding.code}] {finding.message}", err=True)
    click.echo(f"\nFAIL: {len(report.findings)} finding(s)", err=True)
    sys.exit(1)


if __name__ == "__main__":
    main()
```

- [ ] **Step 5: Write CLI test**

`tools/tests/test_cli.py`:

```python
from pathlib import Path

from click.testing import CliRunner

from ggi_policy.cli import main


def test_validate_succeeds_on_valid_fixture(fixtures_dir: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["validate", "--repo-root", str(fixtures_dir / "valid")])
    assert result.exit_code == 0, result.output
    assert "OK" in result.output


def test_validate_fails_loudly_on_invalid(fixtures_dir: Path, tmp_path: Path) -> None:
    # Build a synthetic repo with one bad policy + necessary configs.
    repo = tmp_path / "synth"
    (repo / "policies/identity-and-access").mkdir(parents=True)
    (repo / "schemas").mkdir()
    (repo / ".github").mkdir()

    real = fixtures_dir.parent.parent.parent
    for name in ["policy-frontmatter.schema.json", "policy-rules.schema.json",
                 "exception.schema.json", "role-team-mapping.schema.json",
                 "role-team-mapping.yaml"]:
        (repo / "schemas" / name).write_text((real / "schemas" / name).read_text())
    (repo / ".github/CODEOWNERS").write_text((real / ".github/CODEOWNERS").read_text())
    (repo / "policies/identity-and-access/missing-id.md").write_text(
        (fixtures_dir / "invalid/frontmatter/missing-id.md").read_text()
    )

    runner = CliRunner()
    result = runner.invoke(main, ["validate", "--repo-root", str(repo)])
    assert result.exit_code == 1
    assert "FAIL" in result.output
```

- [ ] **Step 6: Run CLI tests**

```bash
uv run pytest tools/tests/test_cli.py -v
```

Expected: 2 passed.

- [ ] **Step 7: Run the full suite**

```bash
uv run pytest -v
```

Expected: all tests pass (~25+).

- [ ] **Step 8: Commit**

```bash
git add tools/ggi_policy/validate/runner.py tools/ggi_policy/cli.py \
        tools/tests/test_validate_runner.py tools/tests/test_cli.py
git commit -m "feat(cli): wire validate subcommand to orchestrating runner"
```

---

## Task 11: Templates + glossary stub

**Files:**
- Create: `templates/policy.md`
- Create: `templates/policy.rules.yaml`
- Create: `templates/exception.md`
- Create: `glossary/terms.md`

- [ ] **Step 1: Create `templates/policy.md`**

```markdown
---
id: POL-{DOMAIN}-{SLUG}
title: <human-readable title>
summary: >
  <one to two sentence description>
domain: {DOMAIN}                   # IAM | DAT | PRV | APP | END | NET | IR | VND | SEC | BCP | HR | META
status: draft                      # draft | effective | superseded | retired
version: 0.1.0
effective_date: 2026-01-01
last_reviewed: 2026-01-01
review_cycle: annual               # annual | biannual | triennial | event-driven
owner: <role or named person>
approvers: [<role>, <role>]        # roles must exist in schemas/role-team-mapping.yaml
applies_to:
  - <scope item>
supersedes: []
related: []
frameworks:
  nist_csf:     []
  cis:          []
  soc2:         []
  hipaa:        []
  nist_800_53:  []
  nist_800_171: []
external_references: []
---

## Purpose
<why this policy exists>

## Scope
<who/what is in and out>

## Policy Statements
**R1.** <normative statement>
**R2.** <normative statement>

## Rationale
<reasoning, framework requirements, threat model>

## Examples
Compliant:
```
<example>
```
Non-compliant:
```
<example with reason>
```

## Implementation Guidance
<runbooks, configuration links>

## Exceptions
See `exceptions/` directory.

## References
- <related policy IDs, vendor docs, framework citations>

## Revision History
- 0.1.0 (<date>): initial draft.
```

- [ ] **Step 2: Create `templates/policy.rules.yaml`**

```yaml
policy_id: POL-{DOMAIN}-{SLUG}
rules:
  - id: R1
    statement: <normative statement>
    type: flag                     # flag | setting | pattern | decision_table | allowed_values | forbidden_values
    severity: required             # required | recommended
    applies_to:
      object_type: <e.g., entra_security_group>
    # type-specific fields:
    # pattern: "<regex>"           # for type: pattern
    # inputs: [...]                # for type: decision_table
    # rows: [...]
    # allowed: [...]               # for type: allowed_values
    # forbidden: [...]             # for type: forbidden_values
    examples:
      compliant: []
      non_compliant: []
```

- [ ] **Step 3: Create `templates/exception.md`**

```markdown
---
id: EXC-{YYYY}-{NNN}-{SLUG}
policy_ref: POL-{DOMAIN}-{SLUG}.R{N}
requested_by: <email>
approver: <role>
approved_date: 2026-01-01
effective_date: 2026-01-01
expires: 2026-07-01                # cap: 6 months for required rules, 18 months for recommended
status: active                     # active | expired | revoked
compensating_control: >
  <how the risk is mitigated while the exception is in force>
risk_acceptance: <name and reference (e.g., risk register entry)>
---

## Justification
<why the policy cannot be followed in this case>

## Renewal plan
<what work must complete before the exception can be retired>
```

- [ ] **Step 4: Create `glossary/terms.md`**

```markdown
# Glossary

Controlled vocabulary used in GGI policies. Terms are added when first referenced
in a policy and stay here as a reference for both employees and AI agents.

## Identity and Access (IAM)
- **M365 Group** — TBD; will be defined when first IAM policy lands.
- **Distribution Group** — TBD.
- **Mail-enabled Security Group** — TBD.
- **Security Group** — TBD.
- **Shared Mailbox** — TBD.
- **Conditional Access** — TBD.
- **PIM (Privileged Identity Management)** — TBD.

## Data (DAT)
*(populated as data policies are added)*

## Privacy (PRV)
*(populated as privacy policies are added)*

## Other domains
*(populated as those domains' policies are added)*
```

(The glossary uses `TBD` deliberately — these are stubs to be filled when the corresponding policies are written. They are not validation gaps.)

- [ ] **Step 5: Run the full suite to confirm nothing regressed**

```bash
uv run pytest -v
```

- [ ] **Step 6: Commit**

```bash
git add templates glossary
git commit -m "feat(templates): policy / rules sidecar / exception templates and glossary stub"
```

---

## Task 12: GitHub Actions CI workflow

**Files:**
- Create: `.github/workflows/validate.yml`

- [ ] **Step 1: Write the workflow**

`.github/workflows/validate.yml`:

```yaml
name: validate

on:
  pull_request:
  push:
    branches: [main]

jobs:
  validate:
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

      - name: Run unit tests
        run: uv run pytest

      - name: Run repo-wide validation
        run: uv run ggi-policy validate
```

- [ ] **Step 2: Verify the workflow locally**

```bash
uv sync
uv run pytest
uv run ggi-policy validate
```

Expected: tests pass; `validate` reports OK against the (currently policy-empty) repo. The empty `policies/` directory has no `.md` files yet — only `.gitkeep` placeholders — so the runner walks zero policies and produces zero findings.

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/validate.yml
git commit -m "ci(validate): run pytest and ggi-policy validate on PRs and main pushes"
```

- [ ] **Step 4: Push and confirm green CI on the branch**

(Skip if executing locally without GitHub access — confirm during PR review.)

```bash
git push origin HEAD
```

Watch the Actions tab for the green checkmark. If red, fix locally and push again.

---

## Task 13: End-to-end smoke

**Files:**
- None new. This is a verification step.

- [ ] **Step 1: Author a fake `POL-IAM-GROUP-NAMING` policy from the templates**

Copy `templates/policy.md` to `policies/identity-and-access/group-naming.md` and fill in the IAM-flavored content from the design (§5.1 and §5.3 examples). Copy `templates/policy.rules.yaml` to `policies/identity-and-access/group-naming.rules.yaml` and fill in the three rules.

This is **a smoke test** — do not commit this temporary policy. It exists only to confirm the framework supports its first real artifact.

- [ ] **Step 2: Run validation**

```bash
uv run ggi-policy validate
```

Expected: `OK: validated <repo path>`.

- [ ] **Step 3: Introduce one defect at a time and confirm each is caught**

For each of the following, edit the policy, run `uv run ggi-policy validate`, confirm the expected `code` appears in the output, then revert:

| Defect | Expected code |
|--------|--------------|
| Remove `id:` from frontmatter | `FRONTMATTER_INVALID` |
| Set `version: 1.0` (non-semver) | `FRONTMATTER_INVALID` |
| Set `domain: DAT` | `POLICY_WRONG_FOLDER` |
| Rename file to `something-else.md` | `POLICY_FILENAME_MISMATCH` |
| Set `frameworks.nist_csf: [WRONG-1]` | `TAG_FORMAT_INVALID` |
| Set `approvers: [Made-Up Role]` | `APPROVER_UNKNOWN_ROLE` |
| Duplicate a rule id in the sidecar | `RULE_ID_DUPLICATE` |
| Set sidecar rule type to `pattern` without a `pattern` field | `RULES_INVALID` |

- [ ] **Step 4: Remove the smoke-test files**

```bash
rm policies/identity-and-access/group-naming.md
rm policies/identity-and-access/group-naming.rules.yaml
```

- [ ] **Step 5: Confirm a clean validation**

```bash
uv run ggi-policy validate
```

Expected: `OK`.

- [ ] **Step 6: No commit needed for this task** (smoke files were removed). Phase 1 is complete.

---

## Self-review

**Spec coverage:** every Phase-1-relevant section of the design has a task implementing it.

| Spec section | Plan task |
|---|---|
| §4 Repo layout | Task 1 (skeleton dirs) + Task 11 (templates + glossary) |
| §5.1 Frontmatter schema | Task 3 |
| §5.2 Body skeleton | Task 11 (template) |
| §5.3 Sidecar rules schema | Task 4 |
| §6.1 Policy ID rules | Task 6 (consistency) |
| §6.2 Rule sub-IDs | Task 4 (uniqueness) + Task 9 (no reuse) |
| §6.3 Framework tag formats | Task 3 (regex in schema) + Task 8 (cross-cutting check) |
| §6.4 Crosswalks | **Deferred to Phase 2** (called out in plan front matter) |
| §7.1 Lifecycle states | Task 3 (enum in schema) |
| §7.2 Versioning | Task 3 (semver pattern) |
| §7.3 CODEOWNERS + approvers | Task 7 |
| §7.4 Review cadence | **Deferred to Phase 5** (review_cycle field present in schema; the *daily checker* is Phase 5) |
| §7.5 Exceptions + tiered cap | Task 5 |
| §7.6 Change workflow | Task 12 (CI workflow) |
| §8.1 Language and runtime | Task 1 |
| §8.2 CLI components | `validate` only (Phase 1); `build-crosswalks`, `fetch-controls`, `build-site`, `check-reviews`, `notify-effective`, `check-exceptions` are Phase 2-5 |

**Placeholder scan:** the only `TBD` strings are inside `glossary/terms.md` Task 11 — they are intentional content stubs for human authors to fill when they write the corresponding policies, not plan failures. No tasks contain "implement later" or "add appropriate handling".

**Type consistency:** function names (`io.load_policy`, `io.load_rules`, `io.iter_policies`, `runner.run`, `codeowners.parse`, `codeowners.owners_for`, `role_team_map.load`) are stable across tasks. Validation modules all expose `check(...)`. The `ValidationFinding` and `ValidationReport` types are introduced in Task 3 and referenced unchanged in every later task.

**Ambiguity check:** the only judgment call is the day-count for the tiered cap (`6 * 30` and `18 * 30` days). This is an explicit approximation — calendar-month math would be more precise but adds dependency complexity for a +/- 2-day tolerance that doesn't matter for governance. If the user pushes back, swap to `dateutil.relativedelta` later without breaking the schema.
