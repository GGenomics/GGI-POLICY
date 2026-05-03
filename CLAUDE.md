# CLAUDE.md

Bootstrap for AI agents working in this repository. Read this file first.
For full detail see [POL-META-AI-AGENT-CONTRACT](policies/meta/ai-agent-contract.md).

## What this repo is

A policy library for General Genomics, Inc. (GGI / ggenomics.com / ggenomics.internal)
covering data and application governance and cybersecurity. Every policy is authored 
against the framework defined by [POL-META-DOC-FRAMEWORK](policies/meta/doc-framework.md). 
Agents that read, cite, validate, or generate against this library follow the AI-agent contract.

## Authoritative read order

1. **This file** — bootstrap pointers (you are here)
2. [`schemas/`](schemas/) — JSON Schemas for frontmatter, rules, exceptions,
   role-team-mapping, and the framework controls catalog
3. [`schemas/framework-controls.json`](schemas/framework-controls.json) —
   canonical control IDs for NIST CSF 2.0, CIS Controls v8, SOC 2 TSC,
   HIPAA 45 CFR Part 164, NIST 800-53 Rev 5, NIST 800-171 Rev 3
4. [`glossary/terms.md`](glossary/terms.md) — controlled domain vocabulary
5. [`policies/meta/doc-framework.md`](policies/meta/doc-framework.md) — the
   framework, written as a policy
6. [`policies/meta/ai-agent-contract.md`](policies/meta/ai-agent-contract.md) —
   this contract, full detail
7. [`policies/`](policies/) — domain-organized policies; `*.rules.yaml`
   sidecars carry machine-checkable rules
8. [`exceptions/`](exceptions/) — overrides; check before declaring a
   violation

## Enforceability rule

A rule is enforceable IF AND ONLY IF:

1. Parent policy has `status: effective`, AND
2. Parent policy's `effective_date <= today`, AND
3. No active exception (`status: active` AND `expires >= today`) cites the
   rule's full sub-id.

Use the helpers — do not re-implement the predicate:

```python
from ggi_policy.enforce import is_enforceable, evaluate
from ggi_policy.repo import repo_root

# Is a specific rule enforceable today?
ok = is_enforceable(repo_root(), "POL-IAM-GROUP-NAMING", "R1")

# Evaluate a candidate against a rule. Returns EvaluationResult with:
#   verdict: "compliant" | "non_compliant" | "skipped" | "unknown_rule"
#   severity, citation, exceptions
result = evaluate(repo_root(), "POL-IAM-GROUP-NAMING.R1", "sg-az-prod-finance-readers")
print(result.verdict)
print(result.citation)   # "[POL-IAM-GROUP-NAMING.R1] ..."
```

For batch / repo-wide validation (frontmatter, sidecar shape, consistency,
approvers, etc., not per-rule evaluation), use the runner:

```python
from ggi_policy.validate.runner import run
report = run(repo_root=repo_root())
# report.findings is a list of ValidationFinding(code, path, message, locator)
```

## Citation format

Every machine-decidable finding includes a square-bracketed sub-id anchor:

```
[POL-IAM-GROUP-NAMING.R1] <explanation>
Severity: required. Policy v1.0.0, effective 2026-06-01.
```

## Hard prohibitions

- Never fabricate rule IDs or framework tags.
- Never enforce a rule from a non-`effective` policy.
- Never silently elide an active exception.
- Never edit `policies/`, `schemas/`, `exceptions/`, or `crosswalks/` outside
  the PR workflow.

## Quick links

- Design doc:
  [`docs/superpowers/specs/2026-05-02-policy-doc-framework-design.md`](docs/superpowers/specs/2026-05-02-policy-doc-framework-design.md)
- Templates: [`templates/`](templates/) (copy when authoring new artifacts)
- CLI: `uv run ggi-policy {validate,fetch-controls,build-crosswalks,build-site,validate-deploy,check-reviews,notify-effective,check-exceptions}`
