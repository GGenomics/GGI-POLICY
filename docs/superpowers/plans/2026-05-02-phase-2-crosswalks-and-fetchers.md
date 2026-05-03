# Phase 2: Crosswalks + framework-control fetchers — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Populate `schemas/framework-controls.json` with canonical control catalogs from six external frameworks, regenerate per-framework crosswalk pages from policy tags, and upgrade tag validation from format-only to membership-based.

**Architecture:** Each framework gets a fetcher module under `tools/ggi_policy/fetchers/`. Fetchers expose a uniform `fetch() -> FrameworkData` interface and are registered in a central registry. Network-fetching frameworks (NIST OSCAL catalogs, eCFR HIPAA) hit live HTTP endpoints; non-machine-readable frameworks (CIS, SOC 2) read from snapshot files committed alongside the fetcher. A new `ggi-policy fetch-controls` subcommand runs the registry and writes the merged JSON. A second new subcommand, `ggi-policy build-crosswalks`, joins the canonical controls with each policy's `frameworks:` block to regenerate marked regions inside `crosswalks/*.md`. CI runs `build-crosswalks --check` to prevent stale crosswalk pages from merging. Finally, `tags.py` upgrades from regex format checks to membership lookups against the populated catalog.

**Tech Stack:** Python 3.12+ (uv-managed), `httpx` for HTTP fetches with connect/read timeouts, `jsonschema` for validation, `PyYAML` for the existing config files. No new runtime dependencies beyond `httpx`. Tests use canned snapshot fixtures so the suite never requires network access.

---

## Prerequisites

- Phase 1 is merged (HEAD on `origin/main` should be `ac50eaa` or later). 40 unit tests pass, `ggi-policy validate` runs cleanly against an empty policy tree.
- Reference: design doc at [docs/superpowers/specs/2026-05-02-policy-doc-framework-design.md](../specs/2026-05-02-policy-doc-framework-design.md). Sections referenced as **§N** below.
- Reference: Phase 1 plan at [docs/superpowers/plans/2026-05-02-phase-1-foundation.md](2026-05-02-phase-1-foundation.md). Plan-1's §Self-review row "§6.4 Crosswalks → Deferred to Phase 2" is what this plan delivers.
- Network access during dev: the OSCAL and eCFR fetchers hit live endpoints. CI **does not** run `fetch-controls` — only `build-crosswalks --check` and `tags` membership validation against the committed `framework-controls.json`. Refreshing the catalog is a manual `uv run ggi-policy fetch-controls` followed by a PR.
- Phase 2 leaves the validate-only CI workflow alone. Refreshing the catalog is a separate human-initiated workflow.

## File structure (locked-in decomposition)

```
GGI-POLICY/
├── pyproject.toml                               # add httpx >=0.27 to dependencies
├── schemas/
│   ├── framework-controls.schema.json           # NEW: validates the catalog file
│   └── framework-controls.json                  # NEW: catalog data (committed)
│
├── crosswalks/
│   ├── nist-csf.md                              # NEW: prose + markered table + markered gaps
│   ├── cis.md                                   # NEW
│   ├── soc2.md                                  # NEW
│   ├── hipaa.md                                 # NEW
│   ├── nist-800-53.md                           # NEW
│   └── nist-800-171.md                          # NEW
│
├── tools/
│   ├── ggi_policy/
│   │   ├── fetchers/
│   │   │   ├── __init__.py                      # NEW: registry of fetchers
│   │   │   ├── _models.py                       # NEW: Control, FrameworkData dataclasses
│   │   │   ├── _http.py                         # NEW: httpx.get wrapper with timeout/retry
│   │   │   ├── _oscal.py                        # NEW: shared OSCAL JSON parser
│   │   │   ├── nist_csf.py                      # NEW
│   │   │   ├── nist_800_53.py                   # NEW
│   │   │   ├── nist_800_171.py                  # NEW
│   │   │   ├── hipaa.py                         # NEW
│   │   │   ├── cis.py                           # NEW
│   │   │   ├── soc2.py                          # NEW
│   │   │   └── data/                            # NEW: snapshot files for non-fetchable sources
│   │   │       ├── cis-v8.json                  # NEW: committed snapshot
│   │   │       └── soc2-tsc-2017.json           # NEW: committed snapshot
│   │   ├── crosswalks.py                        # NEW: build-crosswalks logic
│   │   ├── controls.py                          # NEW: load framework-controls.json
│   │   └── cli.py                               # MODIFY: add fetch-controls + build-crosswalks
│   └── tests/
│       ├── fixtures/
│       │   ├── fetchers/                        # NEW: canned source-document snapshots
│       │   │   ├── nist_csf.oscal.json
│       │   │   ├── nist_800_53.oscal.json
│       │   │   ├── nist_800_171.oscal.json
│       │   │   └── hipaa.ecfr.json
│       │   └── crosswalks/                      # NEW: round-trip fixtures
│       │       ├── nist-csf-empty.md
│       │       └── nist-csf-populated.md
│       ├── test_fetchers_models.py              # NEW
│       ├── test_fetchers_http.py                # NEW
│       ├── test_fetchers_oscal.py               # NEW
│       ├── test_fetchers_nist_csf.py            # NEW
│       ├── test_fetchers_nist_800_53.py         # NEW
│       ├── test_fetchers_nist_800_171.py        # NEW
│       ├── test_fetchers_hipaa.py               # NEW
│       ├── test_fetchers_cis.py                 # NEW
│       ├── test_fetchers_soc2.py                # NEW
│       ├── test_controls.py                     # NEW
│       ├── test_crosswalks.py                   # NEW
│       ├── test_validate_tags.py                # MODIFY: add membership-check tests
│       └── test_cli.py                          # MODIFY: add fetch-controls + build-crosswalks tests
└── .github/workflows/
    └── validate.yml                             # MODIFY: add `build-crosswalks --check`
```

## Conventions

- **Commits:** Conventional Commits (`feat(fetchers): ...`, `feat(crosswalks): ...`, `chore(deps): ...`). One commit per task unless explicitly split.
- **TDD discipline:** Every fetcher and module has a paired test that uses a canned fixture — never the live network. Tests must run offline.
- **Fixtures are real-world snapshots:** the test fixtures under `tools/tests/fixtures/fetchers/` are real captures of the upstream JSON, lightly trimmed to a representative subset (10-30 controls per framework). They are committed to the repo.
- **Network calls are isolated:** `_http.py` exposes a `fetch_text(url) -> str` and `fetch_json(url) -> dict`. Fetchers never call `httpx` directly. Tests inject fake response text rather than mocking httpx.
- **Find by repo root:** all tooling resolves the repo root via `repo_root()` (cached) — same as Phase 1.

---

## Task 1: Project prerequisites — httpx + framework-controls schema + empty catalog

**Files:**
- Modify: `pyproject.toml` (add `httpx>=0.27` dep)
- Create: `schemas/framework-controls.schema.json`
- Create: `schemas/framework-controls.json` (empty initial state)
- Create: `tools/ggi_policy/fetchers/__init__.py` (empty package marker)
- Create: `tools/ggi_policy/fetchers/_models.py`
- Create: `tools/tests/test_fetchers_models.py`

- [ ] **Step 1: Add httpx to `pyproject.toml`**

In `[project].dependencies`, append `"httpx>=0.27"` so the dependency list reads:

```toml
dependencies = [
  "click>=8.1",
  "httpx>=0.27",
  "jsonschema>=4.21",
  "python-frontmatter>=1.1",
  "PyYAML>=6.0",
]
```

Run `uv sync` to refresh the lockfile. `uv.lock` will be updated.

- [ ] **Step 2: Create `schemas/framework-controls.schema.json`**

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://ggenomics.com/schemas/framework-controls.schema.json",
  "title": "Framework controls catalog",
  "type": "object",
  "additionalProperties": false,
  "required": ["frameworks"],
  "properties": {
    "frameworks": {
      "type": "object",
      "additionalProperties": false,
      "properties": {
        "nist_csf":     { "$ref": "#/$defs/framework" },
        "cis":          { "$ref": "#/$defs/framework" },
        "soc2":         { "$ref": "#/$defs/framework" },
        "hipaa":        { "$ref": "#/$defs/framework" },
        "nist_800_53":  { "$ref": "#/$defs/framework" },
        "nist_800_171": { "$ref": "#/$defs/framework" }
      }
    }
  },
  "$defs": {
    "framework": {
      "type": "object",
      "additionalProperties": false,
      "required": ["metadata", "controls"],
      "properties": {
        "metadata": {
          "type": "object",
          "additionalProperties": false,
          "required": ["version", "fetched_at", "source_url", "fetcher"],
          "properties": {
            "version":     { "type": "string", "minLength": 1 },
            "fetched_at":  { "type": "string", "format": "date" },
            "source_url":  { "type": "string", "format": "uri" },
            "fetcher":     { "type": "string", "minLength": 1 },
            "notes":       { "type": "string" }
          }
        },
        "controls": {
          "type": "array",
          "items": { "$ref": "#/$defs/control" }
        }
      }
    },
    "control": {
      "type": "object",
      "additionalProperties": false,
      "required": ["id", "title"],
      "properties": {
        "id":          { "type": "string", "minLength": 1 },
        "title":       { "type": "string", "minLength": 1 },
        "description": { "type": "string" }
      }
    }
  }
}
```

- [ ] **Step 3: Create the initial empty `framework-controls.json`**

```json
{
  "frameworks": {}
}
```

This file will be populated by Task 9's `fetch-controls` invocation. Committing the empty form now establishes the path so downstream code (Task 13's tag-membership upgrade, Task 11's crosswalk builder) can reliably read from it.

- [ ] **Step 4: Create `tools/ggi_policy/fetchers/__init__.py`**

Empty file. Tasks 2 and onward populate it with the registry.

- [ ] **Step 5: Write failing test for models**

`tools/tests/test_fetchers_models.py`:

```python
from datetime import date

from ggi_policy.fetchers._models import Control, FrameworkData, Metadata


def test_control_dataclass_round_trip() -> None:
    c = Control(id="PR.AC-01", title="Identities issued", description="long form")
    assert c.id == "PR.AC-01"
    assert c.description == "long form"


def test_control_description_optional() -> None:
    c = Control(id="X", title="Y")
    assert c.description == ""


def test_framework_data_to_json_round_trip() -> None:
    meta = Metadata(
        version="2.0",
        fetched_at=date(2026, 5, 2),
        source_url="https://example.com/x.json",
        fetcher="nist_csf",
    )
    fd = FrameworkData(metadata=meta, controls=[Control(id="A", title="B")])
    payload = fd.to_json()
    assert payload["metadata"]["version"] == "2.0"
    assert payload["metadata"]["fetched_at"] == "2026-05-02"
    assert payload["controls"] == [{"id": "A", "title": "B"}]


def test_framework_data_to_json_includes_description_when_set() -> None:
    meta = Metadata(version="2.0", fetched_at=date(2026, 5, 2),
                    source_url="https://x", fetcher="t")
    fd = FrameworkData(metadata=meta, controls=[Control(id="A", title="B", description="long")])
    payload = fd.to_json()
    assert payload["controls"][0]["description"] == "long"
```

Run: `uv run pytest tools/tests/test_fetchers_models.py -v`
Expected: import errors for `ggi_policy.fetchers._models`.

- [ ] **Step 6: Implement `tools/ggi_policy/fetchers/_models.py`**

```python
from dataclasses import dataclass, field
from datetime import date


@dataclass(frozen=True)
class Control:
    id: str
    title: str
    description: str = ""


@dataclass(frozen=True)
class Metadata:
    version: str
    fetched_at: date
    source_url: str
    fetcher: str
    notes: str = ""


@dataclass(frozen=True)
class FrameworkData:
    metadata: Metadata
    controls: list[Control] = field(default_factory=list)

    def to_json(self) -> dict:
        meta = {
            "version": self.metadata.version,
            "fetched_at": self.metadata.fetched_at.isoformat(),
            "source_url": self.metadata.source_url,
            "fetcher": self.metadata.fetcher,
        }
        if self.metadata.notes:
            meta["notes"] = self.metadata.notes
        out_controls = []
        for c in self.controls:
            entry = {"id": c.id, "title": c.title}
            if c.description:
                entry["description"] = c.description
            out_controls.append(entry)
        return {"metadata": meta, "controls": out_controls}
```

- [ ] **Step 7: Run tests to verify passing**

```bash
uv run pytest tools/tests/test_fetchers_models.py -v
```

Expected: 4 passed.

- [ ] **Step 8: Run full suite (44 expected: 40 prior + 4 new)**

```bash
uv run pytest -q
```

Expected: 44 passed.

- [ ] **Step 9: Commit**

```bash
git add pyproject.toml uv.lock schemas/framework-controls.schema.json \
        schemas/framework-controls.json tools/ggi_policy/fetchers \
        tools/tests/test_fetchers_models.py
git commit -m "$(cat <<'EOF'
feat(fetchers): scaffold + framework-controls schema + Control/FrameworkData models

Adds httpx as a runtime dep, defines the JSON Schema for
framework-controls.json (with empty initial file), and lands the
Control / Metadata / FrameworkData dataclasses every fetcher will use.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 2: HTTP wrapper

**Files:**
- Create: `tools/ggi_policy/fetchers/_http.py`
- Create: `tools/tests/test_fetchers_http.py`

- [ ] **Step 1: Write failing test**

`tools/tests/test_fetchers_http.py`:

```python
from unittest.mock import MagicMock, patch

import pytest

from ggi_policy.fetchers import _http


def test_fetch_json_parses_a_response() -> None:
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"a": 1}
    mock_resp.raise_for_status = MagicMock()
    with patch("ggi_policy.fetchers._http.httpx.get", return_value=mock_resp) as get:
        out = _http.fetch_json("https://example.com/x")
    assert out == {"a": 1}
    get.assert_called_once()
    kwargs = get.call_args.kwargs
    assert kwargs.get("timeout") == _http.DEFAULT_TIMEOUT


def test_fetch_text_parses_a_response() -> None:
    mock_resp = MagicMock()
    mock_resp.text = "hello"
    mock_resp.raise_for_status = MagicMock()
    with patch("ggi_policy.fetchers._http.httpx.get", return_value=mock_resp):
        assert _http.fetch_text("https://example.com/x") == "hello"


def test_fetch_json_raises_on_http_error() -> None:
    import httpx
    mock_resp = MagicMock()
    mock_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
        "404", request=MagicMock(), response=MagicMock(status_code=404)
    )
    with patch("ggi_policy.fetchers._http.httpx.get", return_value=mock_resp):
        with pytest.raises(httpx.HTTPStatusError):
            _http.fetch_json("https://example.com/missing")
```

- [ ] **Step 2: Run test (fail expected)**

```bash
uv run pytest tools/tests/test_fetchers_http.py -v
```

Expected: import error for `ggi_policy.fetchers._http`.

- [ ] **Step 3: Implement `_http.py`**

```python
"""Thin wrapper around httpx so fetchers don't all carry duplicate timeout config."""

import httpx

DEFAULT_TIMEOUT = httpx.Timeout(connect=10.0, read=30.0, write=10.0, pool=10.0)


def fetch_text(url: str) -> str:
    """GET `url`, raise on non-2xx, return body as text."""
    resp = httpx.get(url, follow_redirects=True, timeout=DEFAULT_TIMEOUT)
    resp.raise_for_status()
    return resp.text


def fetch_json(url: str) -> dict:
    """GET `url`, raise on non-2xx, return body parsed as JSON."""
    resp = httpx.get(url, follow_redirects=True, timeout=DEFAULT_TIMEOUT)
    resp.raise_for_status()
    return resp.json()
```

- [ ] **Step 4: Run tests to verify passing**

```bash
uv run pytest tools/tests/test_fetchers_http.py -v
```

Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add tools/ggi_policy/fetchers/_http.py tools/tests/test_fetchers_http.py
git commit -m "$(cat <<'EOF'
feat(fetchers): http wrapper with bounded timeouts

Single point of contact for outbound HTTP from fetchers; centralizes
connect/read/write timeouts and follow_redirects. Tests mock httpx.get
so the suite stays offline.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 3: Shared OSCAL parser + NIST CSF fetcher

OSCAL (https://pages.nist.gov/OSCAL/) is the JSON-based catalog format NIST uses for all of CSF, 800-53, and 800-171. Three fetchers share one parser.

**Files:**
- Create: `tools/ggi_policy/fetchers/_oscal.py`
- Create: `tools/ggi_policy/fetchers/nist_csf.py`
- Create: `tools/tests/test_fetchers_oscal.py`
- Create: `tools/tests/test_fetchers_nist_csf.py`
- Create: `tools/tests/fixtures/fetchers/nist_csf.oscal.json`

- [ ] **Step 1: Capture the OSCAL CSF fixture**

`tools/tests/fixtures/fetchers/nist_csf.oscal.json`: a trimmed, representative fragment of the published NIST CSF 2.0 OSCAL catalog. The committed file represents the structure the parser must handle. Keep ~6 controls covering at least 2 functions.

```json
{
  "catalog": {
    "uuid": "csf-2.0-test-fixture",
    "metadata": {
      "title": "NIST Cybersecurity Framework",
      "version": "2.0",
      "oscal-version": "1.1.2"
    },
    "groups": [
      {
        "id": "GV",
        "class": "csf-function",
        "title": "Govern",
        "groups": [
          {
            "id": "GV.OC",
            "class": "csf-category",
            "title": "Organizational Context",
            "controls": [
              {
                "id": "GV.OC-01",
                "class": "csf-subcategory",
                "title": "The organizational mission is understood and informs cybersecurity risk management"
              },
              {
                "id": "GV.OC-02",
                "class": "csf-subcategory",
                "title": "Internal and external stakeholders are understood, and their needs and expectations are understood"
              }
            ]
          }
        ]
      },
      {
        "id": "PR",
        "class": "csf-function",
        "title": "Protect",
        "groups": [
          {
            "id": "PR.AC",
            "class": "csf-category",
            "title": "Access Control",
            "controls": [
              {
                "id": "PR.AC-01",
                "class": "csf-subcategory",
                "title": "Identities and credentials are issued, managed, verified, revoked, and audited"
              },
              {
                "id": "PR.AC-03",
                "class": "csf-subcategory",
                "title": "Remote access is managed"
              },
              {
                "id": "PR.AC-04",
                "class": "csf-subcategory",
                "title": "Access permissions and authorizations are managed, incorporating the principles of least privilege and separation of duties"
              }
            ]
          }
        ]
      }
    ]
  }
}
```

- [ ] **Step 2: Write OSCAL parser test**

`tools/tests/test_fetchers_oscal.py`:

```python
import json
from pathlib import Path

from ggi_policy.fetchers._oscal import iter_controls, parse_catalog


def test_parse_catalog_returns_metadata_and_controls(fixtures_dir: Path) -> None:
    payload = json.loads((fixtures_dir / "fetchers/nist_csf.oscal.json").read_text())
    title, version, controls = parse_catalog(payload)
    assert title == "NIST Cybersecurity Framework"
    assert version == "2.0"
    assert len(controls) == 5
    ids = [c["id"] for c in controls]
    assert "GV.OC-01" in ids and "PR.AC-04" in ids


def test_iter_controls_walks_nested_groups(fixtures_dir: Path) -> None:
    payload = json.loads((fixtures_dir / "fetchers/nist_csf.oscal.json").read_text())
    titles = {c["id"]: c["title"] for c in iter_controls(payload["catalog"]["groups"])}
    assert titles["PR.AC-01"].startswith("Identities")
```

- [ ] **Step 3: Implement `_oscal.py`**

```python
"""Shared parser for OSCAL JSON catalogs (NIST CSF, 800-53, 800-171)."""

from typing import Iterator


def iter_controls(groups: list[dict]) -> Iterator[dict]:
    """Yield every control object reachable from a list of OSCAL groups, recursing nested groups."""
    for group in groups or []:
        for control in group.get("controls", []) or []:
            yield control
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
```

- [ ] **Step 4: Run OSCAL parser tests**

```bash
uv run pytest tools/tests/test_fetchers_oscal.py -v
```

Expected: 2 passed.

- [ ] **Step 5: Write NIST CSF fetcher test**

`tools/tests/test_fetchers_nist_csf.py`:

```python
from datetime import date
from pathlib import Path

from ggi_policy.fetchers import nist_csf


def test_fetch_from_text_returns_framework_data(fixtures_dir: Path) -> None:
    text = (fixtures_dir / "fetchers/nist_csf.oscal.json").read_text()
    fd = nist_csf.fetch_from_text(text, fetched_at=date(2026, 5, 2))
    assert fd.metadata.fetcher == "nist_csf"
    assert fd.metadata.version == "2.0"
    assert fd.metadata.fetched_at == date(2026, 5, 2)
    ids = [c.id for c in fd.controls]
    assert "PR.AC-01" in ids
    assert len(fd.controls) == 5
    pr_ac_01 = next(c for c in fd.controls if c.id == "PR.AC-01")
    assert pr_ac_01.title.startswith("Identities")


def test_fetch_invokes_http_then_parses(fixtures_dir: Path, monkeypatch) -> None:
    canned = (fixtures_dir / "fetchers/nist_csf.oscal.json").read_text()
    monkeypatch.setattr(
        "ggi_policy.fetchers.nist_csf._http.fetch_text",
        lambda url: canned,
    )
    fd = nist_csf.fetch(fetched_at=date(2026, 5, 2))
    assert fd.metadata.source_url == nist_csf.SOURCE_URL
    assert len(fd.controls) == 5
```

- [ ] **Step 6: Implement `nist_csf.py`**

```python
"""NIST Cybersecurity Framework 2.0 fetcher (OSCAL JSON catalog)."""

from datetime import date

from ggi_policy.fetchers import _http
from ggi_policy.fetchers._models import Control, FrameworkData, Metadata
from ggi_policy.fetchers._oscal import parse_catalog
import json


SOURCE_URL = "https://raw.githubusercontent.com/usnistgov/OSCAL/main/src/specifications/json/oscal-catalog-csf-2-0.json"


def fetch_from_text(text: str, *, fetched_at: date) -> FrameworkData:
    payload = json.loads(text)
    _title, version, raw_controls = parse_catalog(payload)
    controls = [Control(id=c["id"], title=c.get("title", "")) for c in raw_controls]
    return FrameworkData(
        metadata=Metadata(
            version=version,
            fetched_at=fetched_at,
            source_url=SOURCE_URL,
            fetcher="nist_csf",
        ),
        controls=controls,
    )


def fetch(*, fetched_at: date | None = None) -> FrameworkData:
    text = _http.fetch_text(SOURCE_URL)
    return fetch_from_text(text, fetched_at=fetched_at or date.today())
```

- [ ] **Step 7: Run NIST CSF tests**

```bash
uv run pytest tools/tests/test_fetchers_nist_csf.py -v
```

Expected: 2 passed.

- [ ] **Step 8: Run full suite**

```bash
uv run pytest -q
```

Expected: 51 passed (44 prior + 2 OSCAL + 2 NIST CSF + 3 http = 51).

- [ ] **Step 9: Commit**

```bash
git add tools/ggi_policy/fetchers/_oscal.py tools/ggi_policy/fetchers/nist_csf.py \
        tools/tests/test_fetchers_oscal.py tools/tests/test_fetchers_nist_csf.py \
        tools/tests/fixtures/fetchers/nist_csf.oscal.json
git commit -m "$(cat <<'EOF'
feat(fetchers): NIST CSF 2.0 fetcher + shared OSCAL parser

OSCAL parser walks nested catalog groups and surfaces every control.
NIST CSF fetcher hits the upstream OSCAL JSON, parses it, and returns
FrameworkData. Tests inject canned source text via monkeypatch so the
suite never touches the network.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 4: NIST 800-53 fetcher

**Files:**
- Create: `tools/ggi_policy/fetchers/nist_800_53.py`
- Create: `tools/tests/test_fetchers_nist_800_53.py`
- Create: `tools/tests/fixtures/fetchers/nist_800_53.oscal.json`

- [ ] **Step 1: Capture a trimmed 800-53 OSCAL fixture**

`tools/tests/fixtures/fetchers/nist_800_53.oscal.json`:

```json
{
  "catalog": {
    "uuid": "800-53-test-fixture",
    "metadata": {
      "title": "NIST Special Publication 800-53 Revision 5",
      "version": "5.1.1",
      "oscal-version": "1.1.2"
    },
    "groups": [
      {
        "id": "ac",
        "class": "family",
        "title": "Access Control",
        "controls": [
          {
            "id": "ac-1",
            "class": "SP800-53",
            "title": "Policy and Procedures"
          },
          {
            "id": "ac-2",
            "class": "SP800-53",
            "title": "Account Management",
            "controls": [
              { "id": "ac-2.1", "class": "SP800-53-enhancement", "title": "Automated System Account Management" },
              { "id": "ac-2.2", "class": "SP800-53-enhancement", "title": "Automated Temporary and Emergency Account Management" }
            ]
          },
          { "id": "ac-3", "class": "SP800-53", "title": "Access Enforcement" },
          { "id": "ac-6", "class": "SP800-53", "title": "Least Privilege" }
        ]
      },
      {
        "id": "au",
        "class": "family",
        "title": "Audit and Accountability",
        "controls": [
          { "id": "au-2", "class": "SP800-53", "title": "Event Logging" },
          { "id": "au-3", "class": "SP800-53", "title": "Content of Audit Records" }
        ]
      }
    ]
  }
}
```

- [ ] **Step 2: Write fetcher tests**

`tools/tests/test_fetchers_nist_800_53.py`:

```python
from datetime import date
from pathlib import Path

from ggi_policy.fetchers import nist_800_53


def test_fetch_from_text_normalizes_ids_to_uppercase(fixtures_dir: Path) -> None:
    text = (fixtures_dir / "fetchers/nist_800_53.oscal.json").read_text()
    fd = nist_800_53.fetch_from_text(text, fetched_at=date(2026, 5, 2))
    ids = [c.id for c in fd.controls]
    # OSCAL uses lowercase ids (`ac-2`); we normalize to the citation form (`AC-2`).
    assert "AC-2" in ids
    assert "AC-2(1)" in ids
    assert "AU-3" in ids


def test_enhancement_id_format(fixtures_dir: Path) -> None:
    text = (fixtures_dir / "fetchers/nist_800_53.oscal.json").read_text()
    fd = nist_800_53.fetch_from_text(text, fetched_at=date(2026, 5, 2))
    ids = {c.id for c in fd.controls}
    # AC-2.1 in OSCAL is AC-2(1) in citations
    assert "AC-2(1)" in ids
    assert "AC-2(2)" in ids


def test_metadata_includes_source_url(fixtures_dir: Path) -> None:
    text = (fixtures_dir / "fetchers/nist_800_53.oscal.json").read_text()
    fd = nist_800_53.fetch_from_text(text, fetched_at=date(2026, 5, 2))
    assert fd.metadata.source_url == nist_800_53.SOURCE_URL
    assert fd.metadata.fetcher == "nist_800_53"
    assert fd.metadata.version == "5.1.1"
```

- [ ] **Step 3: Implement `nist_800_53.py`**

```python
"""NIST 800-53 Rev 5 fetcher (OSCAL JSON catalog).

OSCAL stores control IDs in lowercase with a dot separator for enhancements
(e.g., `ac-2.1`). The citation form used in policy frontmatter is uppercase
with parenthesized enhancement (e.g., `AC-2(1)`). This fetcher converts.
"""

import json
import re
from datetime import date

from ggi_policy.fetchers import _http
from ggi_policy.fetchers._models import Control, FrameworkData, Metadata
from ggi_policy.fetchers._oscal import parse_catalog


SOURCE_URL = "https://raw.githubusercontent.com/usnistgov/OSCAL/main/src/specifications/json/oscal-catalog-sp800-53-rev5.json"

_BASE_RE = re.compile(r"^([a-z]{2})-(\d+)$")
_ENH_RE  = re.compile(r"^([a-z]{2})-(\d+)\.(\d+)$")


def _normalize_id(oscal_id: str) -> str:
    m = _ENH_RE.match(oscal_id)
    if m:
        return f"{m.group(1).upper()}-{m.group(2)}({m.group(3)})"
    m = _BASE_RE.match(oscal_id)
    if m:
        return f"{m.group(1).upper()}-{m.group(2)}"
    return oscal_id  # Pass through anything we don't recognize.


def fetch_from_text(text: str, *, fetched_at: date) -> FrameworkData:
    payload = json.loads(text)
    _title, version, raw_controls = parse_catalog(payload)
    controls = [
        Control(id=_normalize_id(c["id"]), title=c.get("title", ""))
        for c in raw_controls
    ]
    return FrameworkData(
        metadata=Metadata(
            version=version,
            fetched_at=fetched_at,
            source_url=SOURCE_URL,
            fetcher="nist_800_53",
        ),
        controls=controls,
    )


def fetch(*, fetched_at: date | None = None) -> FrameworkData:
    text = _http.fetch_text(SOURCE_URL)
    return fetch_from_text(text, fetched_at=fetched_at or date.today())
```

- [ ] **Step 4: Run tests**

```bash
uv run pytest tools/tests/test_fetchers_nist_800_53.py -v
```

Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add tools/ggi_policy/fetchers/nist_800_53.py \
        tools/tests/test_fetchers_nist_800_53.py \
        tools/tests/fixtures/fetchers/nist_800_53.oscal.json
git commit -m "$(cat <<'EOF'
feat(fetchers): NIST 800-53 Rev 5 fetcher with id normalization

OSCAL stores control IDs as lowercase with dot-separated enhancements
(ac-2.1). Policy frontmatter uses the uppercase parenthesized citation
form (AC-2(1)). The fetcher normalizes during ingest so both shapes
are supported.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 5: NIST 800-171 fetcher

**Files:**
- Create: `tools/ggi_policy/fetchers/nist_800_171.py`
- Create: `tools/tests/test_fetchers_nist_800_171.py`
- Create: `tools/tests/fixtures/fetchers/nist_800_171.oscal.json`

- [ ] **Step 1: Capture a trimmed 800-171 OSCAL fixture**

`tools/tests/fixtures/fetchers/nist_800_171.oscal.json`:

```json
{
  "catalog": {
    "uuid": "800-171-test-fixture",
    "metadata": {
      "title": "NIST Special Publication 800-171 Revision 3",
      "version": "3.0.0",
      "oscal-version": "1.1.2"
    },
    "groups": [
      {
        "id": "3.1",
        "class": "family",
        "title": "Access Control",
        "controls": [
          { "id": "3.1.1", "class": "SP800-171", "title": "Account Management" },
          { "id": "3.1.2", "class": "SP800-171", "title": "Access Enforcement" },
          { "id": "3.1.5", "class": "SP800-171", "title": "Least Privilege" }
        ]
      },
      {
        "id": "3.13",
        "class": "family",
        "title": "System and Communications Protection",
        "controls": [
          { "id": "3.13.11", "class": "SP800-171", "title": "Cryptographic Protection" }
        ]
      }
    ]
  }
}
```

- [ ] **Step 2: Write fetcher tests**

`tools/tests/test_fetchers_nist_800_171.py`:

```python
from datetime import date
from pathlib import Path

from ggi_policy.fetchers import nist_800_171


def test_fetch_from_text_returns_three_dot_ids(fixtures_dir: Path) -> None:
    text = (fixtures_dir / "fetchers/nist_800_171.oscal.json").read_text()
    fd = nist_800_171.fetch_from_text(text, fetched_at=date(2026, 5, 2))
    ids = [c.id for c in fd.controls]
    assert "3.1.1" in ids
    assert "3.13.11" in ids
    assert len(fd.controls) == 4


def test_metadata(fixtures_dir: Path) -> None:
    text = (fixtures_dir / "fetchers/nist_800_171.oscal.json").read_text()
    fd = nist_800_171.fetch_from_text(text, fetched_at=date(2026, 5, 2))
    assert fd.metadata.fetcher == "nist_800_171"
    assert fd.metadata.version == "3.0.0"
```

- [ ] **Step 3: Implement `nist_800_171.py`**

```python
"""NIST 800-171 Rev 3 fetcher (OSCAL JSON catalog).

OSCAL IDs already use the dotted citation form (`3.1.1`, `3.13.11`), so
no normalization is needed.
"""

import json
from datetime import date

from ggi_policy.fetchers import _http
from ggi_policy.fetchers._models import Control, FrameworkData, Metadata
from ggi_policy.fetchers._oscal import parse_catalog


SOURCE_URL = "https://raw.githubusercontent.com/usnistgov/OSCAL/main/src/specifications/json/oscal-catalog-sp800-171-rev3.json"


def fetch_from_text(text: str, *, fetched_at: date) -> FrameworkData:
    payload = json.loads(text)
    _title, version, raw_controls = parse_catalog(payload)
    controls = [Control(id=c["id"], title=c.get("title", "")) for c in raw_controls]
    return FrameworkData(
        metadata=Metadata(
            version=version,
            fetched_at=fetched_at,
            source_url=SOURCE_URL,
            fetcher="nist_800_171",
        ),
        controls=controls,
    )


def fetch(*, fetched_at: date | None = None) -> FrameworkData:
    text = _http.fetch_text(SOURCE_URL)
    return fetch_from_text(text, fetched_at=fetched_at or date.today())
```

- [ ] **Step 4: Run tests**

```bash
uv run pytest tools/tests/test_fetchers_nist_800_171.py -v
```

Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add tools/ggi_policy/fetchers/nist_800_171.py \
        tools/tests/test_fetchers_nist_800_171.py \
        tools/tests/fixtures/fetchers/nist_800_171.oscal.json
git commit -m "$(cat <<'EOF'
feat(fetchers): NIST 800-171 Rev 3 fetcher

Uses the same OSCAL parser as the CSF and 800-53 fetchers. IDs are
already in the dotted citation form (3.1.1, 3.13.11) so no
normalization is required.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 6: HIPAA fetcher (eCFR API)

The eCFR API at `https://www.ecfr.gov/api/versioner/v1/full/{date}/title-45.json?part=164` returns the full structure of 45 CFR Part 164 (Privacy and Security Rules) as JSON.

**Files:**
- Create: `tools/ggi_policy/fetchers/hipaa.py`
- Create: `tools/tests/test_fetchers_hipaa.py`
- Create: `tools/tests/fixtures/fetchers/hipaa.ecfr.json`

- [ ] **Step 1: Capture a trimmed eCFR fixture**

`tools/tests/fixtures/fetchers/hipaa.ecfr.json`:

```json
{
  "structure": {
    "type": "title",
    "identifier": "45",
    "label": "Title 45",
    "children": [
      {
        "type": "subtitle",
        "identifier": "A",
        "label": "Subtitle A",
        "children": [
          {
            "type": "subchapter",
            "identifier": "C",
            "label": "Subchapter C — Administrative Data Standards and Related Requirements",
            "children": [
              {
                "type": "part",
                "identifier": "164",
                "label": "Part 164 — Security and Privacy",
                "children": [
                  {
                    "type": "subpart",
                    "identifier": "C",
                    "label": "Subpart C — Security Standards for the Protection of Electronic Protected Health Information",
                    "children": [
                      {
                        "type": "section",
                        "identifier": "164.308",
                        "label": "Administrative safeguards",
                        "children": [
                          {
                            "type": "paragraph",
                            "identifier": "164.308(a)",
                            "label": "Standards"
                          },
                          {
                            "type": "paragraph",
                            "identifier": "164.308(a)(1)",
                            "label": "Security management process"
                          },
                          {
                            "type": "paragraph",
                            "identifier": "164.308(a)(4)",
                            "label": "Information access management"
                          }
                        ]
                      },
                      {
                        "type": "section",
                        "identifier": "164.312",
                        "label": "Technical safeguards",
                        "children": [
                          {
                            "type": "paragraph",
                            "identifier": "164.312(a)(1)",
                            "label": "Access control"
                          },
                          {
                            "type": "paragraph",
                            "identifier": "164.312(a)(2)(i)",
                            "label": "Unique user identification"
                          }
                        ]
                      }
                    ]
                  }
                ]
              }
            ]
          }
        ]
      }
    ]
  },
  "meta": {
    "title": "Title 45",
    "date": "2026-04-15"
  }
}
```

- [ ] **Step 2: Write fetcher tests**

`tools/tests/test_fetchers_hipaa.py`:

```python
from datetime import date
from pathlib import Path

from ggi_policy.fetchers import hipaa


def test_fetch_from_text_returns_paragraph_level_controls(fixtures_dir: Path) -> None:
    text = (fixtures_dir / "fetchers/hipaa.ecfr.json").read_text()
    fd = hipaa.fetch_from_text(text, fetched_at=date(2026, 5, 2))
    ids = {c.id for c in fd.controls}
    # We only emit paragraph-level identifiers under §164, not section roots.
    assert "164.308(a)(1)" in ids
    assert "164.308(a)(4)" in ids
    assert "164.312(a)(2)(i)" in ids
    # Section roots like "164.308" are NOT controls in our model.
    assert "164.308" not in ids


def test_titles_come_from_label_field(fixtures_dir: Path) -> None:
    text = (fixtures_dir / "fetchers/hipaa.ecfr.json").read_text()
    fd = hipaa.fetch_from_text(text, fetched_at=date(2026, 5, 2))
    by_id = {c.id: c.title for c in fd.controls}
    assert by_id["164.308(a)(4)"] == "Information access management"


def test_metadata(fixtures_dir: Path) -> None:
    text = (fixtures_dir / "fetchers/hipaa.ecfr.json").read_text()
    fd = hipaa.fetch_from_text(text, fetched_at=date(2026, 5, 2))
    assert fd.metadata.fetcher == "hipaa"
    assert fd.metadata.version == "2026-04-15"
```

- [ ] **Step 3: Implement `hipaa.py`**

```python
"""HIPAA Privacy + Security Rules fetcher via the eCFR API.

Pulls 45 CFR Part 164 and emits one Control per paragraph-level identifier
matching the citation form policies use (e.g., `164.308(a)(4)`).
"""

import json
from datetime import date
from typing import Iterator

from ggi_policy.fetchers import _http
from ggi_policy.fetchers._models import Control, FrameworkData, Metadata


SOURCE_URL = "https://www.ecfr.gov/api/versioner/v1/full/latest/title-45.json?part=164"


def _walk(node: dict) -> Iterator[dict]:
    yield node
    for child in node.get("children", []) or []:
        yield from _walk(child)


def fetch_from_text(text: str, *, fetched_at: date) -> FrameworkData:
    payload = json.loads(text)
    structure = payload.get("structure", {})
    catalog_date = payload.get("meta", {}).get("date", fetched_at.isoformat())
    controls: list[Control] = []
    for node in _walk(structure):
        if node.get("type") != "paragraph":
            continue
        identifier = node.get("identifier", "")
        # Only paragraph-level identifiers under §164 with at least one parenthesized component.
        if not identifier.startswith("164.") or "(" not in identifier:
            continue
        controls.append(Control(id=identifier, title=node.get("label", "")))
    return FrameworkData(
        metadata=Metadata(
            version=catalog_date,
            fetched_at=fetched_at,
            source_url=SOURCE_URL,
            fetcher="hipaa",
        ),
        controls=controls,
    )


def fetch(*, fetched_at: date | None = None) -> FrameworkData:
    text = _http.fetch_text(SOURCE_URL)
    return fetch_from_text(text, fetched_at=fetched_at or date.today())
```

- [ ] **Step 4: Run tests**

```bash
uv run pytest tools/tests/test_fetchers_hipaa.py -v
```

Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add tools/ggi_policy/fetchers/hipaa.py \
        tools/tests/test_fetchers_hipaa.py \
        tools/tests/fixtures/fetchers/hipaa.ecfr.json
git commit -m "$(cat <<'EOF'
feat(fetchers): HIPAA fetcher via the eCFR API

Walks the 45 CFR Part 164 structure tree and emits one Control per
paragraph-level identifier with parenthesized components, matching the
citation form policies already use (e.g., 164.308(a)(4)).

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 7: CIS Controls v8 fetcher (committed snapshot)

CIS Workbench requires registration to download the official XML/CSV. This fetcher reads from a snapshot file we maintain in-tree under `tools/ggi_policy/fetchers/data/cis-v8.json`.

**Files:**
- Create: `tools/ggi_policy/fetchers/data/cis-v8.json`
- Create: `tools/ggi_policy/fetchers/cis.py`
- Create: `tools/tests/test_fetchers_cis.py`

- [ ] **Step 1: Create the CIS v8 snapshot**

`tools/ggi_policy/fetchers/data/cis-v8.json`: a hand-curated subset of CIS Controls v8 covering the 18 top-level controls. Each top-level control may have sub-controls; we include a representative subset (~30 entries total).

```json
{
  "version": "8.0",
  "source": "CIS Controls v8 (https://www.cisecurity.org/controls/v8/)",
  "controls": [
    { "id": "1",    "title": "Inventory and Control of Enterprise Assets" },
    { "id": "1.1",  "title": "Establish and Maintain Detailed Enterprise Asset Inventory" },
    { "id": "1.2",  "title": "Address Unauthorized Assets" },
    { "id": "2",    "title": "Inventory and Control of Software Assets" },
    { "id": "2.1",  "title": "Establish and Maintain a Software Inventory" },
    { "id": "3",    "title": "Data Protection" },
    { "id": "3.1",  "title": "Establish and Maintain a Data Management Process" },
    { "id": "4",    "title": "Secure Configuration of Enterprise Assets and Software" },
    { "id": "5",    "title": "Account Management" },
    { "id": "5.1",  "title": "Establish and Maintain an Inventory of Accounts" },
    { "id": "5.2",  "title": "Use Unique Passwords" },
    { "id": "5.3",  "title": "Disable Dormant Accounts" },
    { "id": "5.4",  "title": "Restrict Administrator Privileges to Dedicated Administrator Accounts" },
    { "id": "5.5",  "title": "Establish and Maintain an Inventory of Service Accounts" },
    { "id": "5.6",  "title": "Centralize Account Management" },
    { "id": "6",    "title": "Access Control Management" },
    { "id": "6.1",  "title": "Establish an Access Granting Process" },
    { "id": "6.2",  "title": "Establish an Access Revoking Process" },
    { "id": "6.3",  "title": "Require MFA for Externally-Exposed Applications" },
    { "id": "6.4",  "title": "Require MFA for Remote Network Access" },
    { "id": "6.5",  "title": "Require MFA for Administrative Access" },
    { "id": "6.6",  "title": "Establish and Maintain an Inventory of Authentication and Authorization Systems" },
    { "id": "6.7",  "title": "Centralize Access Control" },
    { "id": "6.8",  "title": "Define and Maintain Role-Based Access Control" },
    { "id": "8",    "title": "Audit Log Management" },
    { "id": "8.1",  "title": "Establish and Maintain an Audit Log Management Process" },
    { "id": "13",   "title": "Network Monitoring and Defense" },
    { "id": "14",   "title": "Security Awareness and Skills Training" },
    { "id": "16",   "title": "Application Software Security" },
    { "id": "17",   "title": "Incident Response Management" }
  ]
}
```

(The committed file is the source of truth. To refresh, manually export the latest CIS Controls list from CIS Workbench, transform it to this shape, and commit a PR.)

- [ ] **Step 2: Write fetcher tests**

`tools/tests/test_fetchers_cis.py`:

```python
from datetime import date

from ggi_policy.fetchers import cis


def test_fetch_loads_snapshot() -> None:
    fd = cis.fetch(fetched_at=date(2026, 5, 2))
    ids = {c.id for c in fd.controls}
    assert "5.4" in ids
    assert "6.1" in ids


def test_metadata() -> None:
    fd = cis.fetch(fetched_at=date(2026, 5, 2))
    assert fd.metadata.fetcher == "cis"
    assert fd.metadata.version == "8.0"
    assert fd.metadata.source_url.startswith("https://www.cisecurity.org")
    assert fd.metadata.notes  # snapshot disclaimer
```

- [ ] **Step 3: Implement `cis.py`**

```python
"""CIS Controls v8 fetcher.

CIS Workbench requires registration to download the official catalog, so
the canonical control list is maintained as a committed snapshot under
data/cis-v8.json. To refresh, export the latest list from CIS Workbench,
transform it to this file's shape, and commit the change.
"""

import json
from datetime import date
from pathlib import Path

from ggi_policy.fetchers._models import Control, FrameworkData, Metadata


SNAPSHOT_PATH = Path(__file__).parent / "data" / "cis-v8.json"
SOURCE_URL = "https://www.cisecurity.org/controls/v8/"


def fetch(*, fetched_at: date | None = None) -> FrameworkData:
    payload = json.loads(SNAPSHOT_PATH.read_text())
    controls = [Control(id=c["id"], title=c["title"]) for c in payload.get("controls", [])]
    return FrameworkData(
        metadata=Metadata(
            version=payload.get("version", "unknown"),
            fetched_at=fetched_at or date.today(),
            source_url=SOURCE_URL,
            fetcher="cis",
            notes="Maintained as a committed snapshot; refresh via CIS Workbench export.",
        ),
        controls=controls,
    )
```

- [ ] **Step 4: Run tests**

```bash
uv run pytest tools/tests/test_fetchers_cis.py -v
```

Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add tools/ggi_policy/fetchers/cis.py tools/ggi_policy/fetchers/data/cis-v8.json \
        tools/tests/test_fetchers_cis.py
git commit -m "$(cat <<'EOF'
feat(fetchers): CIS Controls v8 fetcher backed by committed snapshot

CIS Workbench requires registration so we cannot fetch programmatically.
The snapshot file at fetchers/data/cis-v8.json is the source of truth;
refreshing means exporting from Workbench and opening a PR.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 8: SOC 2 fetcher (manually-maintained data)

SOC 2 Trust Services Criteria are an AICPA proprietary publication (no machine-readable feed). Maintain a curated table.

**Files:**
- Create: `tools/ggi_policy/fetchers/data/soc2-tsc-2017.json`
- Create: `tools/ggi_policy/fetchers/soc2.py`
- Create: `tools/tests/test_fetchers_soc2.py`

- [ ] **Step 1: Create the SOC 2 TSC snapshot**

`tools/ggi_policy/fetchers/data/soc2-tsc-2017.json`: the AICPA Trust Services Criteria (as last revised 2017, points of focus updated 2022).

```json
{
  "version": "TSC-2017 (2022 points of focus)",
  "source": "AICPA Trust Services Criteria",
  "controls": [
    { "id": "CC1.1", "title": "COSO Principle 1: Integrity and ethical values" },
    { "id": "CC1.2", "title": "COSO Principle 2: Board independence and oversight" },
    { "id": "CC1.3", "title": "COSO Principle 3: Management establishes structures" },
    { "id": "CC1.4", "title": "COSO Principle 4: Commitment to competence" },
    { "id": "CC1.5", "title": "COSO Principle 5: Accountability" },
    { "id": "CC2.1", "title": "Internal information for internal control" },
    { "id": "CC2.2", "title": "Internal communication of internal control responsibilities" },
    { "id": "CC2.3", "title": "External communication" },
    { "id": "CC3.1", "title": "Specifying suitable objectives" },
    { "id": "CC3.2", "title": "Identifying and analyzing risk" },
    { "id": "CC3.3", "title": "Assessing fraud risk" },
    { "id": "CC3.4", "title": "Identifying and analyzing significant change" },
    { "id": "CC4.1", "title": "Selecting and developing control activities" },
    { "id": "CC4.2", "title": "Evaluating and communicating deficiencies" },
    { "id": "CC5.1", "title": "Selecting and developing general controls over technology" },
    { "id": "CC5.2", "title": "Selecting and developing physical controls" },
    { "id": "CC5.3", "title": "Deploying control activities" },
    { "id": "CC6.1", "title": "Logical access security software, infrastructure, architectures" },
    { "id": "CC6.2", "title": "Registration and authorization of new users" },
    { "id": "CC6.3", "title": "Modification and removal of access" },
    { "id": "CC6.4", "title": "Restriction of physical access" },
    { "id": "CC6.5", "title": "Disposal of physical assets" },
    { "id": "CC6.6", "title": "External access threats" },
    { "id": "CC6.7", "title": "Restriction of information assets in transit" },
    { "id": "CC6.8", "title": "Prevention or detection of unauthorized software" },
    { "id": "CC7.1", "title": "Detection and monitoring of vulnerabilities" },
    { "id": "CC7.2", "title": "Detection of anomalies and security events" },
    { "id": "CC7.3", "title": "Evaluation of security events for impact" },
    { "id": "CC7.4", "title": "Response to security incidents" },
    { "id": "CC7.5", "title": "Recovery from security incidents" },
    { "id": "CC8.1", "title": "Change management process" },
    { "id": "CC9.1", "title": "Risk mitigation activities" },
    { "id": "CC9.2", "title": "Vendor and business partner risk management" },
    { "id": "A1.1",  "title": "Capacity demand monitoring" },
    { "id": "A1.2",  "title": "Environmental protections, software, data backup, recovery" },
    { "id": "A1.3",  "title": "Recovery plan testing" },
    { "id": "C1.1",  "title": "Identification and maintenance of confidential information" },
    { "id": "C1.2",  "title": "Disposal of confidential information" },
    { "id": "PI1.1", "title": "Definition of data processing requirements" },
    { "id": "PI1.2", "title": "System inputs over completeness and accuracy" },
    { "id": "PI1.3", "title": "System processing" },
    { "id": "PI1.4", "title": "System output completeness, accuracy, and timeliness" },
    { "id": "PI1.5", "title": "Data storage" },
    { "id": "P1.1",  "title": "Notice of objectives related to privacy" },
    { "id": "P2.1",  "title": "Choice and consent" },
    { "id": "P3.1",  "title": "Personal information collection" },
    { "id": "P4.1",  "title": "Limited use, retention, and disposal" },
    { "id": "P5.1",  "title": "Access to personal information" },
    { "id": "P6.1",  "title": "Disclosure to third parties" },
    { "id": "P7.1",  "title": "Quality of personal information" },
    { "id": "P8.1",  "title": "Monitoring and enforcement of privacy" }
  ]
}
```

- [ ] **Step 2: Write fetcher tests**

`tools/tests/test_fetchers_soc2.py`:

```python
from datetime import date

from ggi_policy.fetchers import soc2


def test_fetch_loads_snapshot() -> None:
    fd = soc2.fetch(fetched_at=date(2026, 5, 2))
    ids = {c.id for c in fd.controls}
    assert "CC6.1" in ids
    assert "A1.1" in ids
    assert "PI1.1" in ids


def test_metadata() -> None:
    fd = soc2.fetch(fetched_at=date(2026, 5, 2))
    assert fd.metadata.fetcher == "soc2"
    assert fd.metadata.version.startswith("TSC-2017")
    assert fd.metadata.notes  # disclaimer about manual maintenance
```

- [ ] **Step 3: Implement `soc2.py`**

```python
"""SOC 2 Trust Services Criteria fetcher.

The AICPA TSC publication is proprietary and has no machine-readable
distribution. The control list is maintained as a committed snapshot.
"""

import json
from datetime import date
from pathlib import Path

from ggi_policy.fetchers._models import Control, FrameworkData, Metadata


SNAPSHOT_PATH = Path(__file__).parent / "data" / "soc2-tsc-2017.json"
SOURCE_URL = "https://www.aicpa-cima.com/topic/audit-assurance/audit-and-assurance-greater-than-soc-2"


def fetch(*, fetched_at: date | None = None) -> FrameworkData:
    payload = json.loads(SNAPSHOT_PATH.read_text())
    controls = [Control(id=c["id"], title=c["title"]) for c in payload.get("controls", [])]
    return FrameworkData(
        metadata=Metadata(
            version=payload.get("version", "unknown"),
            fetched_at=fetched_at or date.today(),
            source_url=SOURCE_URL,
            fetcher="soc2",
            notes="Maintained manually from the AICPA TSC publication; no machine source.",
        ),
        controls=controls,
    )
```

- [ ] **Step 4: Run tests**

```bash
uv run pytest tools/tests/test_fetchers_soc2.py -v
```

Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add tools/ggi_policy/fetchers/soc2.py \
        tools/ggi_policy/fetchers/data/soc2-tsc-2017.json \
        tools/tests/test_fetchers_soc2.py
git commit -m "$(cat <<'EOF'
feat(fetchers): SOC 2 Trust Services Criteria fetcher (committed snapshot)

AICPA does not publish a machine-readable TSC catalog. The committed
JSON file under fetchers/data/soc2-tsc-2017.json is the source of truth
for crosswalk and tag-membership purposes; updates require a manual PR.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 9: `fetch-controls` CLI subcommand

Wires the registry of fetchers into a CLI command. Running `uv run ggi-policy fetch-controls` overwrites `schemas/framework-controls.json` with the merged output of every fetcher.

**Files:**
- Modify: `tools/ggi_policy/fetchers/__init__.py` (add `REGISTRY` dict)
- Create: `tools/ggi_policy/controls.py`
- Modify: `tools/ggi_policy/cli.py`
- Create: `tools/tests/test_controls.py`
- Modify: `tools/tests/test_cli.py`

- [ ] **Step 1: Add the registry to `fetchers/__init__.py`**

```python
"""Pluggable framework-control fetchers.

Each fetcher module exposes a ``fetch(*, fetched_at: date | None = None)``
function returning a FrameworkData. The REGISTRY below maps the framework
key (which appears in policy frontmatter under `frameworks:` and in the
framework-controls.json file) to its fetcher module.
"""

from ggi_policy.fetchers import (
    cis as _cis,
    hipaa as _hipaa,
    nist_800_53 as _nist_800_53,
    nist_800_171 as _nist_800_171,
    nist_csf as _nist_csf,
    soc2 as _soc2,
)


REGISTRY = {
    "nist_csf":     _nist_csf,
    "cis":          _cis,
    "soc2":         _soc2,
    "hipaa":        _hipaa,
    "nist_800_53":  _nist_800_53,
    "nist_800_171": _nist_800_171,
}
```

- [ ] **Step 2: Write tests for `controls.py`**

`tools/tests/test_controls.py`:

```python
from datetime import date
from pathlib import Path

from ggi_policy import controls
from ggi_policy.fetchers._models import Control, FrameworkData, Metadata


def _sample_fd(name: str) -> FrameworkData:
    return FrameworkData(
        metadata=Metadata(
            version="1", fetched_at=date(2026, 5, 2),
            source_url="https://x", fetcher=name,
        ),
        controls=[Control(id="A", title="t")],
    )


def test_save_and_load_round_trips(tmp_path: Path) -> None:
    target = tmp_path / "fc.json"
    controls.save({"nist_csf": _sample_fd("nist_csf")}, target)
    loaded = controls.load(target)
    assert "nist_csf" in loaded["frameworks"]
    assert loaded["frameworks"]["nist_csf"]["controls"] == [{"id": "A", "title": "t"}]


def test_ids_for_returns_only_existing_framework(tmp_path: Path) -> None:
    target = tmp_path / "fc.json"
    controls.save({"cis": _sample_fd("cis")}, target)
    loaded = controls.load(target)
    assert controls.ids_for("cis", loaded) == {"A"}
    assert controls.ids_for("nist_csf", loaded) == set()
```

- [ ] **Step 3: Implement `tools/ggi_policy/controls.py`**

```python
"""Read/write the canonical framework-controls catalog."""

import json
from pathlib import Path

from ggi_policy.fetchers._models import FrameworkData


def save(per_framework: dict[str, FrameworkData], path: Path) -> None:
    """Write the merged catalog to `path`. Overwrites existing content."""
    payload = {"frameworks": {name: fd.to_json() for name, fd in per_framework.items()}}
    path.write_text(json.dumps(payload, indent=2, sort_keys=False) + "\n")


def load(path: Path) -> dict:
    """Read and return the catalog as a dict (validate against the schema upstream)."""
    return json.loads(path.read_text())


def ids_for(framework: str, catalog: dict) -> set[str]:
    """Return the set of control IDs known for `framework` in the catalog."""
    framework_data = catalog.get("frameworks", {}).get(framework)
    if not framework_data:
        return set()
    return {c["id"] for c in framework_data.get("controls", [])}
```

- [ ] **Step 4: Run controls tests**

```bash
uv run pytest tools/tests/test_controls.py -v
```

Expected: 2 passed.

- [ ] **Step 5: Add `fetch-controls` to the CLI**

Modify `tools/ggi_policy/cli.py`. Add a new command after `validate`:

```python
@main.command("fetch-controls")
@click.option("--framework", "framework_filter", default=None,
              help="Refresh only the named framework (default: all).")
@click.option("--output", "output_opt", type=click.Path(path_type=Path), default=None,
              help="Write to this path (default: <repo>/schemas/framework-controls.json).")
def fetch_controls(framework_filter: str | None, output_opt: Path | None) -> None:
    """Fetch the latest framework control catalogs and write framework-controls.json."""
    from datetime import date

    from ggi_policy import controls
    from ggi_policy.fetchers import REGISTRY

    today = date.today()
    target_path = output_opt or (repo_root() / "schemas" / "framework-controls.json")

    if target_path.exists():
        existing = controls.load(target_path)
    else:
        existing = {"frameworks": {}}

    selected = ([framework_filter] if framework_filter else list(REGISTRY.keys()))
    out_per_framework = {}

    # Preserve frameworks we aren't refreshing this run.
    for name, raw in existing.get("frameworks", {}).items():
        if name not in selected:
            out_per_framework[name] = _frameworkdata_from_dict(name, raw)

    for name in selected:
        if name not in REGISTRY:
            raise click.ClickException(f"unknown framework: {name!r}")
        click.echo(f"fetching {name}...", err=True)
        out_per_framework[name] = REGISTRY[name].fetch(fetched_at=today)

    controls.save(out_per_framework, target_path)
    click.echo(f"wrote {len(out_per_framework)} framework(s) to {target_path}")


def _frameworkdata_from_dict(name: str, raw: dict):
    """Rehydrate a FrameworkData from the on-disk JSON shape (used to preserve frameworks
    we aren't refreshing this run)."""
    from datetime import date as _date

    from ggi_policy.fetchers._models import Control, FrameworkData, Metadata

    md = raw.get("metadata", {})
    return FrameworkData(
        metadata=Metadata(
            version=md.get("version", ""),
            fetched_at=_date.fromisoformat(md.get("fetched_at", _date.today().isoformat())),
            source_url=md.get("source_url", ""),
            fetcher=md.get("fetcher", name),
            notes=md.get("notes", ""),
        ),
        controls=[Control(id=c["id"], title=c["title"], description=c.get("description", ""))
                  for c in raw.get("controls", [])],
    )
```

- [ ] **Step 6: Add CLI test**

Append to `tools/tests/test_cli.py`:

```python
def test_fetch_controls_writes_catalog(fixtures_dir: Path, tmp_path: Path, monkeypatch) -> None:
    """The fetch-controls subcommand writes a framework-controls.json that
    validates against the schema. We monkeypatch the network-bound fetchers to
    return their canned fixtures so the test stays offline."""
    from datetime import date

    from ggi_policy.fetchers import nist_csf, hipaa, nist_800_53, nist_800_171

    real = fixtures_dir.parent.parent.parent

    def _make_patch(module, fixture_name):
        text = (fixtures_dir / "fetchers" / fixture_name).read_text()
        return lambda *, fetched_at=None: module.fetch_from_text(
            text, fetched_at=fetched_at or date(2026, 5, 2)
        )

    monkeypatch.setattr(nist_csf, "fetch", _make_patch(nist_csf, "nist_csf.oscal.json"))
    monkeypatch.setattr(nist_800_53, "fetch", _make_patch(nist_800_53, "nist_800_53.oscal.json"))
    monkeypatch.setattr(nist_800_171, "fetch", _make_patch(nist_800_171, "nist_800_171.oscal.json"))
    monkeypatch.setattr(hipaa, "fetch", _make_patch(hipaa, "hipaa.ecfr.json"))

    out = tmp_path / "fc.json"

    runner = CliRunner()
    result = runner.invoke(main, ["fetch-controls", "--output", str(out)])
    assert result.exit_code == 0, result.output

    payload = json.loads(out.read_text())
    assert set(payload["frameworks"].keys()) == {
        "nist_csf", "cis", "soc2", "hipaa", "nist_800_53", "nist_800_171"
    }
    assert any(c["id"] == "PR.AC-01" for c in payload["frameworks"]["nist_csf"]["controls"])
    assert any(c["id"] == "5.4" for c in payload["frameworks"]["cis"]["controls"])
```

You will also need to add `import json` at the top of `test_cli.py` if it isn't already imported.

- [ ] **Step 7: Run CLI test**

```bash
uv run pytest tools/tests/test_cli.py -v
```

Expected: 3 passed (2 prior + 1 new).

- [ ] **Step 8: Run end-to-end against the live network**

```bash
uv run ggi-policy fetch-controls
```

Expected: writes `schemas/framework-controls.json` with all 6 frameworks and ~hundreds of controls. Inspect by:

```bash
jq '.frameworks | keys' schemas/framework-controls.json
jq '.frameworks.nist_csf.controls | length' schemas/framework-controls.json
```

If the fetch fails (network unavailable, upstream URL change), do not commit the partial file — investigate first. The committed `framework-controls.json` from this commit is the source of truth for the rest of Phase 2.

- [ ] **Step 9: Commit**

```bash
git add tools/ggi_policy/fetchers/__init__.py tools/ggi_policy/controls.py \
        tools/ggi_policy/cli.py tools/tests/test_controls.py \
        tools/tests/test_cli.py schemas/framework-controls.json
git commit -m "$(cat <<'EOF'
feat(cli): fetch-controls subcommand and populated framework-controls.json

Wires the fetcher registry into a CLI subcommand that overwrites
schemas/framework-controls.json with merged output from all 6 fetchers.
--framework lets you refresh just one. The committed framework-controls.json
is the result of running this against live sources today.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 10: Crosswalk file scaffolding

Create the six crosswalk Markdown files. Each has prose surrounded by two marker regions that `build-crosswalks` will regenerate.

**Files:**
- Create: `crosswalks/nist-csf.md`
- Create: `crosswalks/cis.md`
- Create: `crosswalks/soc2.md`
- Create: `crosswalks/hipaa.md`
- Create: `crosswalks/nist-800-53.md`
- Create: `crosswalks/nist-800-171.md`
- Modify: `crosswalks/.gitkeep` (delete it; the directory now has real content)

- [ ] **Step 1: Create `crosswalks/nist-csf.md`**

```markdown
# NIST CSF 2.0 Crosswalk

This page maps NIST Cybersecurity Framework 2.0 subcategories to current
GGI policy coverage. Subcategories with no policy coverage appear under
"Coverage gaps" — those are an open backlog for future policy work.

Tables and gap lists are regenerated by
`uv run ggi-policy build-crosswalks`. Do not edit the marked regions
by hand; they will be overwritten.

## Coverage table

<!-- BEGIN: crosswalk-table nist_csf -->
<!-- END: crosswalk-table nist_csf -->

## Coverage gaps

<!-- BEGIN: crosswalk-gaps nist_csf -->
<!-- END: crosswalk-gaps nist_csf -->
```

- [ ] **Step 2: Create the other five crosswalk files**

`crosswalks/cis.md`, `crosswalks/soc2.md`, `crosswalks/hipaa.md`, `crosswalks/nist-800-53.md`, `crosswalks/nist-800-171.md` — each follows the same structure, swapping the framework key in the markers and adjusting the H1.

For example, `crosswalks/cis.md`:

```markdown
# CIS Controls v8 Crosswalk

This page maps CIS Controls v8 to current GGI policy coverage.
Tables and gap lists are regenerated by
`uv run ggi-policy build-crosswalks`.

## Coverage table

<!-- BEGIN: crosswalk-table cis -->
<!-- END: crosswalk-table cis -->

## Coverage gaps

<!-- BEGIN: crosswalk-gaps cis -->
<!-- END: crosswalk-gaps cis -->
```

Apply the same pattern, with the appropriate H1 ("SOC 2 Trust Services Criteria Crosswalk", "HIPAA 45 CFR Part 164 Crosswalk", "NIST 800-53 Rev 5 Crosswalk", "NIST 800-171 Rev 3 Crosswalk") and marker keys (`soc2`, `hipaa`, `nist_800_53`, `nist_800_171`).

- [ ] **Step 3: Delete the placeholder**

```bash
rm crosswalks/.gitkeep
```

- [ ] **Step 4: Verify validate still passes**

```bash
uv run pytest -q
uv run ggi-policy validate
```

Expected: tests pass; `validate` reports OK (validate doesn't traverse `crosswalks/`).

- [ ] **Step 5: Commit**

```bash
git add crosswalks
git commit -m "$(cat <<'EOF'
feat(crosswalks): scaffold six per-framework crosswalk pages

Each page has two marker regions (table + gaps) that will be
regenerated by build-crosswalks. The marker shape lets the tool find
its insertion points without parsing the surrounding prose.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 11: `build-crosswalks` subcommand

Reads policies + framework-controls.json, regenerates the marker regions in each `crosswalks/*.md`. `--check` mode fails if regeneration would produce a diff.

**Files:**
- Create: `tools/ggi_policy/crosswalks.py`
- Modify: `tools/ggi_policy/cli.py`
- Create: `tools/tests/test_crosswalks.py`
- Create: `tools/tests/fixtures/crosswalks/nist-csf-empty.md`
- Create: `tools/tests/fixtures/crosswalks/nist-csf-populated.md`

- [ ] **Step 1: Create the empty fixture**

`tools/tests/fixtures/crosswalks/nist-csf-empty.md`:

```markdown
# NIST CSF 2.0 Crosswalk

<!-- BEGIN: crosswalk-table nist_csf -->
<!-- END: crosswalk-table nist_csf -->

<!-- BEGIN: crosswalk-gaps nist_csf -->
<!-- END: crosswalk-gaps nist_csf -->
```

- [ ] **Step 2: Create the populated fixture**

`tools/tests/fixtures/crosswalks/nist-csf-populated.md`:

```markdown
# NIST CSF 2.0 Crosswalk

<!-- BEGIN: crosswalk-table nist_csf -->
| Control | Title | Policies |
|---|---|---|
| GV.OC-01 | The organizational mission is understood and informs cybersecurity risk management | _(no policy)_ |
| PR.AC-01 | Identities and credentials are issued, managed, verified, revoked, and audited | POL-IAM-GROUP-NAMING |
<!-- END: crosswalk-table nist_csf -->

<!-- BEGIN: crosswalk-gaps nist_csf -->
- GV.OC-01 — The organizational mission is understood and informs cybersecurity risk management
<!-- END: crosswalk-gaps nist_csf -->
```

- [ ] **Step 3: Write tests for the crosswalks module**

`tools/tests/test_crosswalks.py`:

```python
from datetime import date
from pathlib import Path

from ggi_policy import crosswalks


SAMPLE_CATALOG = {
    "frameworks": {
        "nist_csf": {
            "metadata": {
                "version": "2.0", "fetched_at": "2026-05-02",
                "source_url": "https://x", "fetcher": "nist_csf",
            },
            "controls": [
                {"id": "GV.OC-01", "title": "The organizational mission is understood and informs cybersecurity risk management"},
                {"id": "PR.AC-01", "title": "Identities and credentials are issued, managed, verified, revoked, and audited"},
            ],
        }
    }
}


def test_render_replaces_marker_regions(fixtures_dir: Path) -> None:
    empty = (fixtures_dir / "crosswalks/nist-csf-empty.md").read_text()
    expected = (fixtures_dir / "crosswalks/nist-csf-populated.md").read_text()
    coverage = {"PR.AC-01": ["POL-IAM-GROUP-NAMING"]}
    rendered = crosswalks.render(empty, "nist_csf", SAMPLE_CATALOG, coverage)
    assert rendered.strip() == expected.strip()


def test_render_is_idempotent(fixtures_dir: Path) -> None:
    text = (fixtures_dir / "crosswalks/nist-csf-empty.md").read_text()
    coverage = {"PR.AC-01": ["POL-IAM-GROUP-NAMING"]}
    once = crosswalks.render(text, "nist_csf", SAMPLE_CATALOG, coverage)
    twice = crosswalks.render(once, "nist_csf", SAMPLE_CATALOG, coverage)
    assert once == twice


def test_build_coverage_inverts_policy_frameworks_block() -> None:
    policies = [
        {"id": "POL-IAM-GROUP-NAMING", "frameworks": {"nist_csf": ["PR.AC-01", "PR.AC-03"]}},
        {"id": "POL-DAT-CLASSIFICATION", "frameworks": {"nist_csf": ["PR.AC-01"]}},
    ]
    coverage = crosswalks.build_coverage(policies, framework="nist_csf")
    assert coverage["PR.AC-01"] == ["POL-DAT-CLASSIFICATION", "POL-IAM-GROUP-NAMING"]
    assert coverage["PR.AC-03"] == ["POL-IAM-GROUP-NAMING"]
```

- [ ] **Step 4: Implement `crosswalks.py`**

```python
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
```

- [ ] **Step 5: Wire `build-crosswalks` into the CLI**

Modify `tools/ggi_policy/cli.py`. Add another command after `fetch-controls`:

```python
@main.command("build-crosswalks")
@click.option("--check", "check_mode", is_flag=True, default=False,
              help="Exit non-zero if regeneration would change any file.")
@click.option("--repo-root", "repo_root_opt",
              type=click.Path(exists=True, file_okay=False, path_type=Path),
              default=None)
def build_crosswalks(check_mode: bool, repo_root_opt: Path | None) -> None:
    """Regenerate the marker regions inside crosswalks/<framework>.md files."""
    from ggi_policy import crosswalks as crosswalks_mod

    root = (repo_root_opt or repo_root()).resolve()
    ok, changed = crosswalks_mod.build_all(root, check=check_mode)
    if check_mode:
        if ok:
            click.echo("OK: crosswalks up to date")
            sys.exit(0)
        for path in changed:
            click.echo(path, err=True)
        click.echo(f"\nFAIL: {len(changed)} crosswalk file(s) would change. "
                   f"Run `uv run ggi-policy build-crosswalks` and commit.", err=True)
        sys.exit(1)
    if changed:
        for path in changed:
            click.echo(f"updated {path}")
    else:
        click.echo("no changes")
```

- [ ] **Step 6: Run all crosswalks tests**

```bash
uv run pytest tools/tests/test_crosswalks.py -v
```

Expected: 3 passed.

- [ ] **Step 7: Generate the live crosswalks**

```bash
uv run ggi-policy build-crosswalks
```

Expected: "no changes" — there are no policies yet, so the table and gaps blocks are empty (controls listed as `_(no policy)_` and every control listed as a gap). After the first invocation: every crosswalk file's marker region should be populated.

Inspect e.g. `crosswalks/nist-csf.md` to confirm the structure.

- [ ] **Step 8: Run idempotency check**

```bash
uv run ggi-policy build-crosswalks --check
```

Expected: `OK: crosswalks up to date`, exit 0.

- [ ] **Step 9: Run full suite**

```bash
uv run pytest -q
```

Expected: all tests pass.

- [ ] **Step 10: Commit**

```bash
git add tools/ggi_policy/crosswalks.py tools/ggi_policy/cli.py \
        tools/tests/test_crosswalks.py tools/tests/fixtures/crosswalks \
        crosswalks
git commit -m "$(cat <<'EOF'
feat(crosswalks): build-crosswalks subcommand with --check mode

Inverts each policy's frameworks: block to control_id -> [policy_ids],
joins against framework-controls.json to render coverage tables and
gap lists inside the marker regions of crosswalks/<framework>.md.
Idempotent. --check mode is what CI will run on every PR.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 12: CI integration of `build-crosswalks --check`

**Files:**
- Modify: `.github/workflows/validate.yml`

- [ ] **Step 1: Add the build-crosswalks check step**

Append a step to `.github/workflows/validate.yml` after the existing `Run repo-wide validation` step:

```yaml
      - name: Check crosswalks are up to date
        run: uv run ggi-policy build-crosswalks --check
```

The full workflow file should now look like:

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

      - name: Check crosswalks are up to date
        run: uv run ggi-policy build-crosswalks --check
```

- [ ] **Step 2: Verify the check passes locally**

```bash
uv run ggi-policy build-crosswalks --check
```

Expected: `OK: crosswalks up to date`.

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/validate.yml
git commit -m "$(cat <<'EOF'
ci(crosswalks): block PRs that would leave crosswalks stale

Adds a build-crosswalks --check step to the validate workflow so a PR
that touches any policy's frameworks: block must also rebuild the
crosswalks. Refresh locally with `uv run ggi-policy build-crosswalks`.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 13: Upgrade `tags.py` to membership validation

Now that `framework-controls.json` is populated, `tags.py` can verify that every framework tag in a policy actually exists in the canonical catalog. The format-only check is replaced with a membership check that emits a new finding code `TAG_UNKNOWN` for unrecognized control IDs.

**Files:**
- Modify: `tools/ggi_policy/validate/tags.py`
- Modify: `tools/ggi_policy/validate/runner.py`
- Modify: `tools/tests/test_validate_tags.py`
- Create: `tools/tests/fixtures/invalid/tags/policies/identity-and-access/unknown-csf.md`

- [ ] **Step 1: Create the unknown-tag fixture**

`tools/tests/fixtures/invalid/tags/policies/identity-and-access/unknown-csf.md`: copy of the valid policy fixture but with `nist_csf: [PR.AC-99]`. (`PR.AC-99` *passes the format regex* but is not a real CSF subcategory.)

- [ ] **Step 2: Update existing tag tests + add the new one**

Modify `tools/tests/test_validate_tags.py`:

```python
from pathlib import Path

from ggi_policy import io
from ggi_policy.result import ValidationReport
from ggi_policy.validate import tags


SAMPLE_CATALOG = {
    "frameworks": {
        "nist_csf": {"controls": [
            {"id": "PR.AC-1", "title": "x"},
            {"id": "PR.AC-3", "title": "x"},
        ]},
        "cis":          {"controls": [{"id": "5.4", "title": "x"}, {"id": "6.1", "title": "x"}]},
        "soc2":         {"controls": [{"id": "CC6.1", "title": "x"}]},
        "hipaa":        {"controls": [{"id": "164.308(a)(4)", "title": "x"}]},
        "nist_800_53":  {"controls": [{"id": "AC-2", "title": "x"}]},
        "nist_800_171": {"controls": [{"id": "3.1.1", "title": "x"}]},
    }
}


def test_valid_tags_yield_no_findings(fixtures_dir: Path) -> None:
    policy = io.load_policy(fixtures_dir / "valid/policies/identity-and-access/group-naming.md")
    report = ValidationReport()
    tags.check(policy, SAMPLE_CATALOG, report)
    assert report.ok, [f.message for f in report.findings]


def test_unknown_csf_tag_is_reported(fixtures_dir: Path) -> None:
    policy = io.load_policy(fixtures_dir / "invalid/tags/policies/identity-and-access/unknown-csf.md")
    report = ValidationReport()
    tags.check(policy, SAMPLE_CATALOG, report)
    codes = {f.code for f in report.findings}
    assert "TAG_UNKNOWN" in codes
```

The previous `bad-csf.md` fixture (with `WRONGFMT-1`) is no longer needed for tag validation because the schema's `additionalProperties: false` and the runner's tag-membership check together cover the same case. Delete it to keep the suite tight:

```bash
rm tools/tests/fixtures/invalid/tags/policies/identity-and-access/bad-csf.md
```

- [ ] **Step 3: Update `tags.py`**

Replace the entire file:

```python
"""Per-framework tag membership validation.

Phase 1 used regex format checks; Phase 2 upgrades to membership lookups against
schemas/framework-controls.json so that `PR.AC-99` (correct format, doesn't
exist) is caught.
"""

from ggi_policy.io import LoadedPolicy
from ggi_policy.result import ValidationFinding, ValidationReport


def check(policy: LoadedPolicy, catalog: dict, report: ValidationReport) -> None:
    """`catalog` is the parsed schemas/framework-controls.json document."""
    framework_index: dict[str, set[str]] = {
        framework: {c["id"] for c in fw.get("controls", [])}
        for framework, fw in catalog.get("frameworks", {}).items()
    }

    for framework, values in policy.metadata.get("frameworks", {}).items():
        known = framework_index.get(framework)
        if known is None:
            # Unknown framework key — covered by the frontmatter schema's
            # additionalProperties: false; no extra finding here.
            continue
        for value in values or []:
            if str(value) not in known:
                report.add(ValidationFinding(
                    code="TAG_UNKNOWN",
                    path=policy.path,
                    message=(
                        f"frameworks.{framework}: {value!r} is not in the "
                        f"canonical {framework} catalog"
                    ),
                    locator=f"frameworks/{framework}",
                ))
```

- [ ] **Step 4: Update the runner to load the catalog and pass it in**

Modify `tools/ggi_policy/validate/runner.py`. Add a catalog load near where CODEOWNERS is loaded:

Locate this block:

```python
    co_rules = codeowners.parse(config_root / ".github" / "CODEOWNERS")
    role_map = role_team_map.load(config_root / "schemas" / "role-team-mapping.yaml")
```

Add immediately after:

```python
    from ggi_policy import controls as controls_io
    catalog_path = config_root / "schemas" / "framework-controls.json"
    catalog = controls_io.load(catalog_path) if catalog_path.exists() else {"frameworks": {}}
```

Then change the `tags.check(policy, report)` call to:

```python
        tags.check(policy, catalog, report)
```

- [ ] **Step 5: Run the tag tests**

```bash
uv run pytest tools/tests/test_validate_tags.py tools/tests/test_validate_runner.py -v
```

Expected: 4 passed (2 tags + 2 runner).

- [ ] **Step 6: Run the full suite**

```bash
uv run pytest -q
uv run ggi-policy validate
```

Expected: all tests pass; validate reports OK.

- [ ] **Step 7: Update the existing valid policy fixture**

The Phase 1 fixture uses `nist_csf: [PR.AC-1, PR.AC-3]` — the OSCAL canonical IDs are `PR.AC-01` and `PR.AC-03` (zero-padded). After this task lands, the fixture's tags would fail membership validation against the live catalog. Update the valid fixture:

`tools/tests/fixtures/valid/policies/identity-and-access/group-naming.md` — change:
```yaml
  nist_csf:     [PR.AC-1, PR.AC-3]
```
to:
```yaml
  nist_csf:     [PR.AC-01, PR.AC-03]
```

(Adjust other framework IDs in this fixture if they too need re-canonicalization — verify by running `uv run ggi-policy validate --repo-root tools/tests/fixtures/valid` after copying CODEOWNERS in. The simplest check: run the tests; failures will indicate ID mismatches.)

- [ ] **Step 8: Re-run tests**

```bash
uv run pytest -q
```

Expected: all tests pass.

- [ ] **Step 9: Commit**

```bash
git add tools/ggi_policy/validate/tags.py tools/ggi_policy/validate/runner.py \
        tools/tests/test_validate_tags.py \
        tools/tests/fixtures/invalid/tags \
        tools/tests/fixtures/valid/policies/identity-and-access/group-naming.md
git commit -m "$(cat <<'EOF'
feat(validate): upgrade tags from format-only to canonical-membership

tags.py now reads framework-controls.json and emits TAG_UNKNOWN when a
policy cites a control ID that isn't in the canonical catalog. This
catches things like PR.AC-99 that pass the regex but don't exist.
The runner loads the catalog once and passes it into tags.check.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 14: End-to-end Phase 2 smoke

**Files:** none — verification only.

- [ ] **Step 1: Confirm catalog completeness**

```bash
jq '.frameworks | keys' schemas/framework-controls.json
jq '.frameworks | to_entries | map({key: .key, controls: (.value.controls | length)})' \
    schemas/framework-controls.json
```

Expected: keys list all six frameworks; each shows a non-zero control count.

- [ ] **Step 2: Confirm crosswalks regenerate cleanly**

```bash
uv run ggi-policy build-crosswalks
git diff --stat crosswalks/
```

Expected: no diff (running twice is a no-op).

- [ ] **Step 3: Author a fake `POL-IAM-GROUP-NAMING` policy with real CSF tags**

Copy `templates/policy.md` to `policies/identity-and-access/group-naming.md`, fill in the IAM frontmatter, and set:

```yaml
frameworks:
  nist_csf: [PR.AC-01, PR.AC-03]
```

Run:

```bash
uv run ggi-policy validate
uv run ggi-policy build-crosswalks
```

Open `crosswalks/nist-csf.md` and confirm the `PR.AC-01` row now reads `POL-IAM-GROUP-NAMING` in the Policies column, and that `PR.AC-01` is **not** in the gaps list.

- [ ] **Step 4: Test each Phase 2 defect category**

For each defect, mutate the policy, run validate, confirm the expected code, then revert:

| Defect | Expected code |
|--------|---------------|
| `nist_csf: [PR.AC-99]` (well-formed but unknown) | `TAG_UNKNOWN` |
| `cis: ["99.99"]` (well-formed but unknown) | `TAG_UNKNOWN` |
| `soc2: [CC6.99]` (well-formed but unknown) | `TAG_UNKNOWN` |

Confirm `TAG_FORMAT_INVALID` is **no longer** emitted (it was retired in Task 13).

- [ ] **Step 5: Test crosswalk drift detection**

While the smoke policy is in place, manually edit `crosswalks/nist-csf.md` to break the table content (e.g., delete a row inside the marker region). Run:

```bash
uv run ggi-policy build-crosswalks --check
```

Expected: exit 1 with the path listed. Then run without `--check` to repair, and confirm `--check` passes again.

- [ ] **Step 6: Remove the smoke files and verify clean state**

```bash
rm policies/identity-and-access/group-naming.md
uv run ggi-policy build-crosswalks
uv run ggi-policy validate
uv run ggi-policy build-crosswalks --check
```

Expected: validate OK; check OK.

- [ ] **Step 7: No commit**

The smoke files have been removed; nothing to commit.

---

## Self-review

**Spec coverage:** every Phase-2-relevant section of the design has a task implementing it.

| Spec section | Plan task |
|---|---|
| §6.4 Crosswalks | Tasks 10, 11, 12 |
| §8.3 Framework-controls fetcher (pluggable per-framework modules) | Tasks 1, 3, 4, 5, 6, 7, 8 |
| §8.3 Provenance per framework | Task 1 (schema) + Tasks 3-8 (Metadata fields) + Task 9 (catalog write) |
| §6.5 Reverse direction (per-policy frameworks list at bottom of rendered page) | **Deferred to Phase 3** (page rendering layer) |
| Tag membership validation | Task 13 |

**Placeholder scan:** no `TBD`/`TODO`/`FIXME` placeholders. The CIS and SOC 2 fetchers ship with a representative subset of controls; the snapshots are real (not placeholders) and refreshing is a documented PR-driven workflow. The fetcher version literals (`CSF 2.0`, `800-53 Rev 5`, `800-171 Rev 3`, `CIS v8`, `TSC-2017 (2022 points of focus)`, `2026-04-15` for HIPAA) are live values as of writing.

**Type consistency:** `Control(id, title, description="")`, `FrameworkData(metadata, controls)`, `Metadata(version, fetched_at, source_url, fetcher, notes="")` are introduced in Task 1 and used unchanged through Task 13. `controls.load(path) -> dict`, `controls.save(per_framework, path) -> None`, `controls.ids_for(framework, catalog) -> set[str]` are introduced in Task 9. `crosswalks.render(text, framework, catalog, coverage) -> str`, `crosswalks.build_coverage(policies, framework=...) -> dict[str, list[str]]`, `crosswalks.build_all(repo_root, check=False) -> tuple[bool, list[str]]` are introduced in Task 11.

**Ambiguity check:**
- The framework prefix names in `framework-controls.json` (`nist_csf`, `cis`, `soc2`, `hipaa`, `nist_800_53`, `nist_800_171`) match exactly the keys used in policy frontmatter `frameworks:` blocks. Verified against Task 13's `framework_index` build.
- The OSCAL ID-normalization for 800-53 (`ac-2` → `AC-2`, `ac-2.1` → `AC-2(1)`) is explicit in Task 4. The policy frontmatter regex from Phase 1 was `^[A-Z]{2}-\d+(\(\d+\))?$`, matching the citation form. After Phase 2's membership check replaces the regex (Task 13), policies must use the citation form to pass; the fixture is updated accordingly.
- HIPAA emits paragraph-level identifiers only (Task 6 explicitly excludes section roots). Policy authors citing `164.308(a)(4)` will match; citing `164.308` would (correctly) fail membership validation.
