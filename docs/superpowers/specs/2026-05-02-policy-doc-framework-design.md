# GGI Policy Documentation Framework — Design

- **Date:** 2026-05-02
- **Status:** Approved (design); pending implementation plan
- **Owner (proposed):** CISO + IT Director
- **Scope:** The documentation *framework* itself — file layout, schemas, lifecycle, tooling, and AI-agent contract — that future GGI policies will be authored against. Individual policies (group naming, RBAC, data classification, etc.) are out of scope for this design and will be authored as separate work items once the framework is in place.

---

## 1. Problem and goals

GGI needs a single, durable home for company policies covering data and application governance and cybersecurity. Today there is no canonical location, no naming or structural convention, and no mechanism by which AI agents (Copilot, internal scripts, future agents) can read and apply policy consistently.

The framework must support two audiences with one source of truth:

- **Employees** — readable, searchable, navigable; feels like a normal internal documentation site.
- **AI agents** — deterministic file paths, schema-validated structures, stable identifiers, and a small bootstrap surface so any agent can ground itself quickly.

The work also needs to support an active group-cleanup project that will produce GGI's first concrete policy (`POL-IAM-GROUP-NAMING`) shortly after the framework lands.

### Goals

1. A repository structure that is navigable by humans and AI agents, organized by domain with framework-control tags layered on top.
2. A per-policy file format with schema-validated frontmatter, optional sidecar machine-readable rules, and a fixed body skeleton.
3. Stable, slug-based policy IDs and rule sub-IDs that survive folder reorganizations.
4. Crosswalks from internal policies to NIST CSF 2.0, CIS Controls v8, SOC 2 TSC, HIPAA (45 CFR Part 164), NIST 800-53, and NIST 800-171.
5. A lightweight lifecycle model — draft / effective / superseded / retired — with semver versioning, CODEOWNERS-enforced approvers, review cadences, and exception tracking.
6. A Python-based tooling baseline that validates, renders, and publishes the docs, plus pluggable framework-control fetchers.
7. A static documentation site, deployed on-prem to k8s via the existing Flux GitOps stack, with Entra-SSO-fronted access and SharePoint/Teams iframe embedding.
8. A short, explicit contract telling AI agents exactly where to look, when a rule is enforceable, how to cite findings, and what they must not do.

### Non-goals

- Authoring any actual policies — that is downstream work.
- Building live audit/scan tools that compare running config (Entra/Intune/SharePoint state) against policy. The framework gives those tools a stable rule format to consume; the tools themselves are downstream.
- General employee-handbook content (PTO, benefits, conduct) — out of scope; that lives in the HRIS/handbook system.
- Heavy compliance-process tooling (digital signatures, RFC-style change control). Reserved for a later iteration if/when an audit demands it.

---

## 2. Audiences

| Audience | Read path | Their need |
|---|---|---|
| Employees | Rendered MkDocs site behind Entra SSO; pages embedded into SharePoint and Teams via iframe | Search, navigate by topic, understand the *why* |
| Approvers (CISO, IT Director, etc.) | GitHub PRs gated by CODEOWNERS | Review proposed changes, sign off |
| AI agents (Copilot, internal scripts, future agents) | Repo files directly via git read access — bootstrapping from `CLAUDE.md` / `AGENTS.md` | Deterministic structures, schema-validated rules, stable IDs |
| Auditors / customer-questionnaire respondents | Crosswalk pages on the rendered site | Map GGI policy to NIST/CIS/SOC 2/HIPAA/CMMC controls |

---

## 3. High-level decisions (summary)

| Decision | Choice | Rationale |
|---|---|---|
| Layout | Hybrid: domain folders + crosswalks directory | Matches employee mental model; framework alignment via tags rather than folders |
| Frameworks tagged | NIST CSF 2.0, CIS v8, SOC 2 TSC, HIPAA, NIST 800-53, NIST 800-171 | Matches GGI's audit / customer-questionnaire / CMMC ambitions |
| Rule placement | Hybrid: simple rules in frontmatter; complex rules in sidecar `policy.rules.yaml`; examples inline | Avoids frontmatter bloat; gives AI agents a deterministic place to look |
| Identifiers | Domain-prefixed slugs (`POL-IAM-GROUP-NAMING`); rule sub-IDs (`.R1`, `.R2`) | Self-describing; stable across reorgs; greppable; never collides with framework control IDs |
| Lifecycle | Standard model: status, version (semver), effective_date, owner, approvers via CODEOWNERS, review_cycle, exceptions/ directory | Audit-ready backbone without heavy change-control |
| Severity levels | Two: `required`, `recommended` | Three levels rot; two stay honest |
| Exception caps | Tiered — `required` rules: max 6 months; `recommended`: max 18 months | Aligns review burden with rule importance |
| AI-agent use cases | All — Q&A, validation, generation, audit, authoring assistance | Justifies investing in the dual-audience format up front |
| Tooling language | Python 3.12+, managed with `uv` | MkDocs is Python; rich schema-validation libs; idiomatic for AI agents |
| Publishing | MkDocs Material → static site → containerized → on-prem k8s (Flux GitOps via `GGenomics/ggi_internals`) | Aligns with existing platform; avoids new cloud subscription |
| Access | Entra SSO via ingress-nginx + oauth2-proxy; iframe-embeddable in SharePoint and Teams | Reuses existing Entra session; consistent UX |
| Image registry | GHCR (`ghcr.io/ggenomics/ggi-policy-site`) | GitHub-native, no extra registry |
| Image promotion | Flux image automation (`image-reflector-controller` + `image-automation-controller`) | This repo never needs write access to `ggi_internals` |
| In-cluster secrets | HashiCorp Vault + Vault Secrets Operator (VSO) | Matches GGI's existing platform standard |

---

## 4. Repo layout and domain taxonomy

```
GGI-POLICY/
├── README.md                       # orientation: start here
├── CLAUDE.md                       # bootstrap for AI agents working IN the repo
├── AGENTS.md                       # symlink to CLAUDE.md (non-Claude agent compatibility)
├── mkdocs.yml                      # MkDocs Material configuration
├── pyproject.toml                  # tooling deps managed by uv
├── Dockerfile                      # FROM nginx:alpine; COPY built site/
│
├── policies/                       # all policies, organized by domain
│   ├── identity-and-access/        # IAM
│   ├── data/                       # DAT
│   ├── privacy/                    # PRV
│   ├── applications/               # APP
│   ├── endpoints/                  # END
│   ├── network/                    # NET
│   ├── incident-response/          # IR
│   ├── vendor-and-third-party/     # VND
│   ├── security-operations/        # SEC
│   ├── business-continuity/        # BCP
│   ├── human-resources/            # HR  (security-relevant HR only)
│   └── meta/                       # META
│
├── exceptions/                     # one file per exception, citing POL-…-Rn
├── crosswalks/                     # six framework crosswalks, part-prose part-generated
│   ├── nist-csf.md
│   ├── cis.md
│   ├── soc2.md
│   ├── hipaa.md
│   ├── nist-800-53.md
│   └── nist-800-171.md
│
├── templates/                      # copy-from-here for new artifacts
│   ├── policy.md
│   ├── policy.rules.yaml
│   └── exception.md
│
├── schemas/                        # JSON Schemas — single source of truth for AI + CI
│   ├── policy-frontmatter.schema.json
│   ├── policy-rules.schema.json
│   ├── exception.schema.json
│   └── framework-controls.json     # populated by tools/fetch-controls
│
├── glossary/terms.md               # controlled domain vocabulary
├── tools/                          # Python CLI: validate, build-crosswalks, fetch-controls, ...
│
├── docs/
│   └── superpowers/specs/          # design specs (this file)
│
└── .github/
    ├── CODEOWNERS                  # per-domain approver enforcement
    └── workflows/                  # CI: validate, build, publish image, link-check, etc.
```

### Domain → ID-prefix table

| Folder                    | Prefix | Example |
|---------------------------|--------|---------|
| identity-and-access/      | IAM    | `POL-IAM-GROUP-NAMING` |
| data/                     | DAT    | `POL-DAT-CLASSIFICATION` |
| privacy/                  | PRV    | `POL-PRV-DATA-SUBJECT-RIGHTS` |
| applications/             | APP    | `POL-APP-SAAS-ONBOARDING` |
| endpoints/                | END    | `POL-END-DEVICE-COMPLIANCE` |
| network/                  | NET    | `POL-NET-SEGMENTATION` |
| incident-response/        | IR     | `POL-IR-SEVERITY-CLASSIFICATION` |
| vendor-and-third-party/   | VND    | `POL-VND-RISK-ASSESSMENT` |
| security-operations/      | SEC    | `POL-SEC-LOGGING` |
| business-continuity/      | BCP    | `POL-BCP-BACKUP` |
| human-resources/          | HR     | `POL-HR-OFFBOARDING-DEPROVISIONING` |
| meta/                     | META   | `POL-META-DOC-FRAMEWORK` |

The HR folder's README explicitly scopes content to "HR policies that affect security posture" (onboarding/offboarding, role changes, security training, background checks, acceptable use, remote work, contractor access, insider-threat handling) and excludes general employee-handbook content.

---

## 5. Per-policy structure

Each policy is a single Markdown file with YAML frontmatter, optionally accompanied by a sidecar `policy.rules.yaml` when it has structured rules.

### 5.1 Frontmatter (validated by `schemas/policy-frontmatter.schema.json`)

```yaml
---
id: POL-IAM-GROUP-NAMING
title: Entra Group Naming Conventions
summary: >
  Defines naming conventions and type-selection rules for all groups in
  Entra ID, including security groups, M365 groups, distribution groups,
  mail-enabled security groups, and shared mailboxes.
domain: IAM
status: effective                   # draft | effective | superseded | retired
version: 1.0.0                      # semver
effective_date: 2026-06-01
last_reviewed: 2026-05-01
review_cycle: annual                # annual | biannual | triennial | event-driven
owner: IT Director
approvers: [CISO, IT Director]      # must be subset of CODEOWNERS for this path
applies_to:
  - All Entra ID groups (cloud and synced)
  - All shared mailboxes
supersedes: []
related: [POL-IAM-RBAC-MODEL, POL-IAM-ACCESS-LIFECYCLE]
frameworks:
  nist_csf:     [PR.AC-1, PR.AC-3, PR.AC-4]
  cis:          ["5.4", "6.1", "6.2"]
  soc2:         [CC6.1, CC6.2, CC6.3]
  hipaa:        ["164.308(a)(4)"]
  nist_800_53:  [AC-2, AC-3, AC-6]
  nist_800_171: ["3.1.1", "3.1.2", "3.1.5"]
external_references:
  - https://learn.microsoft.com/entra/identity/users/groups-naming-policy
---
```

The `frameworks` block is **nested by framework** rather than a flat prefixed list — strict, schema-friendly, and gives crosswalk tooling clean per-framework keys.

### 5.2 Body skeleton (fixed sections, in this order)

Empty sections are explicit (`*Not applicable.*`) so absence is intentional.

1. **Purpose** — the *why*
2. **Scope** — prose elaboration of `applies_to`
3. **Policy Statements** — normative claims, numbered `R1`, `R2`, `R3` … to match rule sub-IDs
4. **Rationale** — reasoning, references to incidents, framework requirements, threat model
5. **Examples** — compliant *and* non-compliant, in fenced code blocks
6. **Implementation Guidance** — runbooks, Entra/Intune/Defender configuration links
7. **Exceptions** — pointer to exception process; lists active exceptions
8. **References** — Microsoft docs, framework citations, related policies
9. **Revision History** — human-readable digest of major changes (git is the system of record)

### 5.3 Sidecar rules (`policy.rules.yaml`, validated by `schemas/policy-rules.schema.json`)

```yaml
policy_id: POL-IAM-GROUP-NAMING
rules:
  - id: R1
    statement: Security group names must match the prescribed pattern.
    type: pattern                   # flag | setting | pattern | decision_table | allowed_values | forbidden_values
    severity: required              # required | recommended
    applies_to:
      object_type: entra_security_group
    pattern: "^sg-(az|m365|ad)-[a-z0-9]+-[a-z0-9-]+$"
    examples:
      compliant:    [sg-az-prod-finance-readers, sg-m365-it-engineering-admins]
      non_compliant:
        - { value: "Marketing-Team-2024", reason: "Missing sg- prefix and structure" }
        - { value: "sg-Az-Prod-Finance",  reason: "Uppercase not permitted" }

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

Removed rules retain their numbers (`status: removed`, `removed_in: <version>`); numbers are never reused.

---

## 6. Identifiers, framework tags, and crosswalks

### 6.1 Policy ID rules

- **Format:** `POL-{DOMAIN}-{SLUG}` — uppercase end-to-end, hyphen-separated.
- **Filename binding:** `policies/{domain-folder}/{slug}.md`, where the filename slug is the lowercased kebab form of the ID slug. CI enforces this — moving or renaming a file without updating the `id` field fails the build.
- **Stability:** IDs are forever. Retired IDs are never reused.
  - Renaming a *title* is free.
  - Renaming a *slug* requires major version bump and `supersedes:` listing on the new policy.
  - Splitting one policy into two: original goes `superseded`; both new IDs list it under `supersedes:`.
  - Merging: same shape, with `superseded_by:` set on both originals.

### 6.2 Rule sub-IDs

- Format: `R1`, `R2`, ... assigned in order within `policy.rules.yaml`.
- Citation form: `POL-IAM-GROUP-NAMING.R1` (dot-separated).
- Numbers are never reused; removed rules keep their number with `status: removed`, `removed_in: <version>`.

### 6.3 Framework tag formats

Validated by per-framework regex in `policy-frontmatter.schema.json`; values cross-checked against `schemas/framework-controls.json` so typos like `PR.AC-99` get caught.

| Framework      | Format                          | Example |
|----------------|---------------------------------|---------|
| `nist_csf`     | `{Function}.{Category}-{Sub}` (CSF 2.0: GV, ID, PR, DE, RS, RC) | `PR.AC-1`, `GV.OC-01` |
| `cis`          | `{Control}.{Sub}` as string     | `"5.4"`, `"6.10"` |
| `soc2`         | `{Category}{N}.{N}`             | `CC6.1`, `A1.1`, `PI1.1`, `C1.1` |
| `hipaa`        | CFR citation                    | `"164.308(a)(4)"`, `"164.312(a)(1)"` |
| `nist_800_53`  | `{Family}-{N}` or `{F}-{N}({E})`| `AC-2`, `AC-2(1)` |
| `nist_800_171` | `{Family}.{N}` as string        | `"3.1.1"`, `"3.13.11"` |

### 6.4 Crosswalk files

Each of the six frameworks has one Markdown file in `crosswalks/`. Files are part-prose, part-generated. Generation markers fence the regenerable regions:

```markdown
<!-- BEGIN: crosswalk-table nist_csf -->
| Subcategory | Description | Policies |
| ... | ... | ... |
<!-- END: crosswalk-table nist_csf -->

<!-- BEGIN: crosswalk-gaps nist_csf -->
- DE.AE-02 — Detected events analyzed (no policy)
<!-- END: crosswalk-gaps nist_csf -->
```

The `tools/build-crosswalks` script:

1. Loads every `policies/**/*.md` frontmatter.
2. Inverts the per-policy `frameworks` map into per-framework `control → [policy IDs]`.
3. Loads `schemas/framework-controls.json` for the canonical control list and descriptions.
4. Renders the table and gaps regions inside the markers; idempotent.

CI runs the script in `--check` mode; a diff fails the build with a hint to run locally and commit.

Coverage gaps are surfaced **internally** — the rendered site is behind Entra SSO and visible to all GGI staff. Nothing is exposed externally.

### 6.5 Reverse direction

Not duplicated as a separate file. Each rendered policy page includes an auto-generated table of its `frameworks:` block at the bottom, with each entry hyperlinked to the relevant crosswalk page. The frontmatter remains the single source of truth.

---

## 7. Lifecycle and governance

### 7.1 Lifecycle states

| Status        | Meaning                                                      | AI-enforce? |
|---------------|--------------------------------------------------------------|-------------|
| `draft`       | Author working on it; PR may be open as `[WIP]`              | No |
| `effective`   | Merged. Authoritative once `effective_date <= today`         | Yes — only after `effective_date` |
| `superseded`  | Replaced. Kept for history and audit traceability            | No |
| `retired`     | Discontinued; topic no longer applies. Kept for history      | No |

The single rule for AI agents and validators: **enforce a rule only if `status == effective AND effective_date <= today`.** Tooling exposes `is_enforceable(policy_id, rule_id) -> bool` so this is not re-implemented in every consumer.

### 7.2 Versioning (semver)

- **MAJOR** — tightens, removes, or otherwise breaks an existing rule. Requires future-dated `effective_date` for advance notice.
- **MINOR** — additive: new rule, expanded scope, additional framework tag, more examples.
- **PATCH** — prose, typos, clarifications only; no rule change.

Drafts use `0.x.y`. First effective version is `1.0.0`. Major bumps trigger an automatic PR comment reminding the author about advance notice and migration documentation.

### 7.3 Approvers — CODEOWNERS

Per-path mapping in `.github/CODEOWNERS`:

```
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

A CI lint enforces that each policy's `approvers:` field is a subset of (or equal to) the CODEOWNERS for its path.

**Role-name ↔ team-handle mapping.** Policy frontmatter uses human-readable role names (`CISO`, `IT Director`); CODEOWNERS uses GitHub team handles (`@ggenomics/ciso`). The mapping lives in a small config file `schemas/role-team-mapping.yaml`:

```yaml
roles:
  CISO:             "@ggenomics/ciso"
  IT Director:      "@ggenomics/it-director"
  Data Steward:     "@ggenomics/data-steward"
  HR Director:      "@ggenomics/hr-director"
  Privacy Officer:  "@ggenomics/privacy-officer"
  Policy Stewards:  "@ggenomics/policy-stewards"
```

The `validate` subcommand reads this file when reconciling `approvers:` lists against CODEOWNERS. New roles are added by editing this file (which itself is gated by CODEOWNERS for `/schemas/`).

The teams in this mapping do not yet exist in the GitHub org; they will be created as empty placeholders during implementation, with members added before the first dependent PR.

### 7.4 Reviews

`review_cycle: annual | biannual | triennial | event-driven`. A scheduled GitHub Action runs daily; for any `effective` policy where `last_reviewed + review_cycle < today`, it opens or refreshes a "Review Due" issue assigned to the listed owner. `event-driven` policies don't trigger date reminders — their text names triggers (e.g., "review after any incident classified P0/P1"). Reviewing means the owner opens a PR bumping `last_reviewed`, even if no other change is needed.

### 7.5 Exceptions

One file per exception: `exceptions/EXC-{YYYY}-{NNN}-{slug}.md`.

```yaml
---
id: EXC-2026-001-FINANCE-LEGACY-GROUP
policy_ref: POL-IAM-GROUP-NAMING.R1
requested_by: jane.doe@ggenomics.com
approver: CISO
approved_date: 2026-04-15
effective_date: 2026-04-15
expires: 2026-10-15
status: active                      # active | expired | revoked
compensating_control: >
  Conditional Access policy CAP-23 requires MFA + compliant device for any
  access to the Finance-Legacy group. Sign-in logs forwarded to Sentinel.
risk_acceptance: Accepted by CISO; documented in risk register RR-2026-014.
---

## Justification
…why the policy cannot be followed in this case…

## Renewal plan
…what work must complete before this exception can be retired…
```

**Tiered max duration**, derived by looking up the referenced rule's severity:

- `severity: required` → max 6 months
- `severity: recommended` → max 18 months

CI checks:

- `policy_ref` resolves to a real, enforceable rule sub-ID.
- `expires - effective_date` is within the cap for the referenced rule's severity.
- Active exceptions with `expires < today` are flagged in the build.
- A scheduled action surfaces upcoming expirations 30 days out via the `#policy-updates` Teams channel.
- No auto-renewal; renewals are fresh PRs through the same approval flow.

The exception file is the system of record. State is not duplicated into ticketing or spreadsheets.

### 7.6 Change workflow

1. Author opens a PR (branch convention: `policy/POL-IAM-GROUP-NAMING-vN.M.P-short-desc`).
2. PR template prompts for: change type (rule / scope / prose), version-bump rationale, communication plan if MAJOR.
3. CI runs: frontmatter schema validation; ID↔filename↔folder consistency; framework tag validation; sidecar rules schema validation; crosswalk regeneration check (`--check`); link checking; exception cap and expiration checks; CODEOWNERS↔approvers reconciliation.
4. CODEOWNERS gates approver review.
5. On merge: CI builds the site, builds and pushes the container image to GHCR, Flux image automation reconciles the new tag into `ggi_internals`, the cluster pulls and serves the new version.
6. If `effective_date` is in the future, a scheduled GitHub Action posts notice into `#policy-updates` on the effective date.

---

## 8. Tooling baseline

### 8.1 Language and runtime

Python 3.12+, managed with `uv`. Single `pyproject.toml` at the repo root. CI and humans run `uv sync`; both use the same versions. Future *live* Entra audit tools (which scan running config) may be in PowerShell with Microsoft.Graph; they are downstream and not part of this framework.

### 8.2 CLI components

All exposed via `uv run ggi-policy <subcommand>`:

| Subcommand | Purpose |
|-----------|---------|
| `validate` | Frontmatter schema; ID↔filename↔folder consistency; framework tag validation; sidecar rules schema; CODEOWNERS↔approvers reconciliation; cross-reference integrity; tiered exception cap enforcement (6 mo for `required`, 18 mo for `recommended`). |
| `build-crosswalks` | Regenerates table + gaps regions in `crosswalks/*.md`. Idempotent. `--check` mode for CI. |
| `fetch-controls` | Pulls canonical framework control IDs into `schemas/framework-controls.json` via pluggable per-framework fetchers. |
| `build-site` | Wraps `mkdocs build` with pre-render hooks (per-policy frameworks tables, exception link counts). |
| `check-reviews` | Daily GH Action: opens "Review Due" issues for overdue effective policies. |
| `notify-effective` | Daily GH Action: posts to `#policy-updates` Teams channel when a policy's `effective_date == today`. |
| `check-exceptions` | Surfaces upcoming exception expirations 30 days out; flags expired-but-still-active in CI. |

### 8.3 Framework-controls fetcher (pluggable)

Each framework gets a module under `tools/fetchers/{framework}.py`, each exposing `fetch() -> List[Control]`. A registry pattern means adding a new framework = adding one file. Initial sources:

| Framework      | Source                                          | Fidelity |
|----------------|-------------------------------------------------|----------|
| `nist_csf`     | NIST OSCAL CSF 2.0 catalog (JSON)               | High |
| `nist_800_53`  | NIST OSCAL 800-53 catalog                       | High |
| `nist_800_171` | NIST OSCAL 800-171 catalog                      | High |
| `cis`          | CIS Workbench export, periodic manual refresh   | Medium |
| `soc2`         | AICPA TSC, manually maintained from PDF         | Low — provenance flagged |
| `hipaa`        | eCFR API for 45 CFR Part 164                    | High |

`schemas/framework-controls.json` carries per-framework provenance (source URL, version, fetched date). CI warns if any framework's data is older than 12 months.

### 8.4 Site hosting (on-prem k8s, cross-repo)

**Two-repo model:**

- **`GGenomics/GGI-POLICY`** (this repo): content + `Dockerfile` + CI that builds the site and pushes a versioned image to GHCR (`ghcr.io/ggenomics/ggi-policy-site`).
- **`GGenomics/ggi_internals`** at `GitOps/k8s/prod/apps/policy-docs/`: kustomize manifests; Flux reconciles to the cluster.

Flux **image automation** (`image-reflector-controller` + `image-automation-controller`, already present in the cluster) watches GHCR; an `ImagePolicy` constrains auto-updates to a chosen tag range; an `ImageUpdateAutomation` writes the tag back into the manifest as a commit on `ggi_internals`. This repo never needs write access to `ggi_internals`.

**Authentication:**

- New Entra app registration (`ggi-policy-docs`) with redirect URI `https://policy.internal.ggenomics.com/oauth2/callback`.
- ingress-nginx + oauth2-proxy bound to the Entra OIDC issuer.
- ingress annotations route requests through oauth2-proxy:
  ```yaml
  nginx.ingress.kubernetes.io/auth-url: "https://oauth2-proxy.<ns>.svc.cluster.local/oauth2/auth"
  nginx.ingress.kubernetes.io/auth-signin: "https://policy.internal.ggenomics.com/oauth2/start?rd=$escaped_request_uri"
  ```
- SharePoint and Teams iframe embeds piggyback on the existing Entra session — no extra sign-in.

**Secrets:**

- oauth2-proxy `client_id`, `client_secret`, and `cookie_secret`: HashiCorp Vault, surfaced via Vault Secrets Operator (VSO) using `VaultStaticSecret` CRDs. Mirrors the established `airflow` pattern under `GitOps/k8s/prod/apps/`.
- `#policy-updates` Teams webhook URL: GitHub Actions secret on this repo (`TEAMS_POLICY_WEBHOOK`). Not stored in `ggi_internals`.

### 8.5 Out of scope for the framework

These belong to specific *policies*, not the framework:

- Group-name validators (belong to `POL-IAM-GROUP-NAMING` once authored).
- Live Entra/Intune/SharePoint scanners.

The framework's job is to make those tools easy to write by giving them a stable, schema-validated rule format.

---

## 9. AI-agent contract

This is itself a policy in the META domain: `policies/meta/POL-META-AI-AGENT-CONTRACT.md`, written using the framework it describes.

### 9.1 Authoritative entry points (read in this order)

1. `CLAUDE.md` and `AGENTS.md` at the repo root — bootstrap pointers
2. `schemas/*.schema.json`
3. `schemas/framework-controls.json`
4. `glossary/terms.md`
5. `policies/meta/POL-META-DOC-FRAMEWORK.md`
6. `policies/meta/POL-META-AI-AGENT-CONTRACT.md`
7. `policies/**/*.md` and `policies/**/*.rules.yaml`
8. `exceptions/*.md`

### 9.2 Enforceability rule

A rule is enforceable IF AND ONLY IF:

1. Parent policy has `status: effective`, AND
2. Parent policy's `effective_date <= today`, AND
3. No active exception (`status: active` AND `expires >= today`) cites the rule's full sub-ID.

Tooling exposes:

- `is_enforceable(policy_id, rule_id) -> bool`
- `evaluate(rule_id, candidate) -> Result(verdict, citations[], exceptions[])`

### 9.3 Citation format

Every machine-decidable finding includes a square-bracketed sub-ID anchor:

```
[POL-IAM-GROUP-NAMING.R1] Group name 'Marketing-Team-2024' does not match
the required pattern '^sg-(az|m365|ad)-[a-z0-9]+-[a-z0-9-]+$'.
Suggested compliant name: 'sg-m365-marketing-general'.
Severity: required. Policy v1.0.0, effective 2026-06-01.
```

### 9.4 Five expected behaviors

1. **Q&A** — retrieve relevant policy prose, cite the policy ID, include `status` and `effective_date`.
2. **Validation** — given a candidate, evaluate against applicable rules; return `Result(verdict, citations[], exceptions[])`.
3. **Generation** — produce compliant artifacts using the rule's `pattern` / `allowed_values` / `decision_table` plus examples; cite the rule sub-IDs that constrained generation.
4. **Audit / drift** — given live state, walk all enforceable rules whose `applies_to.object_type` matches; emit findings with sub-ID citations.
5. **Authoring assistance** — read schema + template; suggest frontmatter and body content that conforms.

### 9.5 Hard prohibitions

- Never invent rule IDs or framework tags. Unfindable citation = "I don't have a rule for this," never a fabrication.
- Never enforce a rule from a non-`effective` policy. Drafts and superseded policies are read-only context.
- Never silently elide an active exception. Surface its ID and expiration.
- Never edit `policies/`, `schemas/`, `exceptions/`, or `crosswalks/` outside the PR workflow. Direct writes bypass CODEOWNERS, CI, and the approval contract.

### 9.6 `CLAUDE.md` / `AGENTS.md` bootstrap

A short file at the repo root containing the entry-points list (9.1), the enforceability rule (9.2), the citation format (9.3), and a pointer to `POL-META-AI-AGENT-CONTRACT.md` for full detail. Intentionally tiny so cold-started agents have a deterministic, low-cost ground.

---

## 10. Open items and known gaps

These are tracked here so they don't get lost when implementation begins:

1. **GitHub teams creation.** Six teams under `@ggenomics/` (`ciso`, `it-director`, `data-steward`, `hr-director`, `privacy-officer`, `policy-stewards`) need to be created and populated before the first PR depending on CODEOWNERS lands.
2. **Entra app registration** for `ggi-policy-docs` must be created in the GGI tenant with the correct redirect URI and group claims, and its credentials placed in Vault under a path matching the `airflow` pattern.
3. **SharePoint/Teams embed pages.** Locations and ownership of the SharePoint and Teams pages that will host iframes referencing `https://policy.internal.ggenomics.com` need to be decided with stakeholders.
4. **External `#policy-updates` Teams channel.** Channel must exist and a webhook must be issued; the URL goes into the `TEAMS_POLICY_WEBHOOK` GitHub Actions secret on this repo.
5. **Glossary seeding.** `glossary/terms.md` needs an initial set of controlled terms (M365 Group, Distribution Group, Mail-enabled Security Group, Security Group, Shared Mailbox, Conditional Access, PIM, etc.) to anchor the first wave of policies.
6. **DNS for `policy.ggenomics.internal`** must be allocated and pointed at the cluster ingress.
7. **TLS issuance** for that hostname (cert-manager + internal CA, or whatever pattern matches the airflow deployment).
8. **First policy after the framework lands** is expected to be `POL-IAM-GROUP-NAMING`. The framework must be adequate to support it without changes; its authoring will validate the framework.

---

## 11. Success criteria

The framework is successful when all of the following are true:

1. A new policy can be authored from a template, validated locally with `uv run ggi-policy validate`, and merged through a CODEOWNERS-gated PR — and is automatically reflected on the rendered site within minutes of merge.
2. An AI agent given only `CLAUDE.md` plus repo read access can answer "is this group name compliant with our policies?" by locating the relevant rule, evaluating, and citing in the prescribed format.
3. The crosswalk pages show non-trivial coverage of NIST CSF / CIS / SOC 2 / HIPAA / NIST 800-53 / NIST 800-171 controls based on tags in actual policies, with a coverage-gaps section that drives the policy backlog.
4. An exception can be filed, approved, expire, and renew — with CI failing the build if any of the integrity rules (severity-cap, real `policy_ref`, expiration) are violated.
5. Updating a single policy file results in an automatic image build to GHCR, an automated `ggi_internals` commit by Flux image automation, and a cluster reconcile — with no human intervention in the deployment path.
