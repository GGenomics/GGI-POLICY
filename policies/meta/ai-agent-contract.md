---
id: POL-META-AI-AGENT-CONTRACT
title: AI Agent Contract
summary: >
  Defines what AI agents working with this repository can rely on, where to
  look first, when a rule is enforceable, how to cite findings, and what
  agents must not do. Written so any agent (Copilot, internal scripts, future
  agents) can ground itself by reading this single document.
domain: META
status: effective
version: 1.0.0
effective_date: 2026-05-03
last_reviewed: 2026-05-03
review_cycle: annual
owner: Policy Stewards
approvers: [CISO, IT Director, Policy Stewards]
applies_to:
  - All AI agents (Copilot, Claude Code, internal Python scripts, future agents)
  - All automated tooling that reads policy state
supersedes: []
related: [POL-META-DOC-FRAMEWORK]
frameworks:
  nist_csf:     [GV.PO-01, GV.RR-01, PR.AT-01]
  cis:          ["14"]
  soc2:         [CC1.4, CC2.1]
  hipaa:        ["164.316(a)"]
  nist_800_53:  [AT-1, PM-1]
  nist_800_171: ["3.2.1"]
external_references:
  - https://github.com/GGenomics/GGI-POLICY/blob/main/CLAUDE.md
---

## Purpose

GGI commits to building this policy library so that AI agents can read it,
cite it, validate against it, and generate compliant artifacts from it. That
commitment requires the agents themselves to operate predictably: read from
canonical paths, recognize when a rule applies, cite findings in a parseable
shape, and refrain from fabricating answers when grounding is missing.

This policy is the explicit contract. An agent that follows the rules below
is operating correctly; an agent that breaks them is operating outside its
authorization.

## Scope

In scope:

- Every AI agent or automation that reads files from this repository — for
  question-answering, validation, generation, audit, or authoring assistance.
- Tooling that interprets policy state on behalf of humans (Copilot in PRs,
  internal scripts in CI, future agentic systems).

Out of scope:

- Tooling that operates *only* on the rendered MkDocs site (e.g., search
  crawlers) without parsing source files. Those rely on the rendered output's
  own contracts, not this one.

## Policy Statements

**R1.** Authoritative entry points, in this read order:

1. `CLAUDE.md` and `AGENTS.md` at the repo root — bootstrap pointers
2. `schemas/*.schema.json` — data shapes
3. `schemas/framework-controls.json` — canonical framework control IDs
4. `glossary/terms.md` — controlled domain vocabulary
5. `policies/meta/doc-framework.md` — the framework as policy
6. `policies/meta/ai-agent-contract.md` — this contract
7. `policies/**/*.md` and `policies/**/*.rules.yaml` — policies + sidecars
8. `exceptions/*.md` — overrides

**R2.** Enforceability rule. A rule is enforceable IF AND ONLY IF:

1. Parent policy has `status: effective`, AND
2. Parent policy's `effective_date <= today`, AND
3. No active exception (`status: active` AND `expires >= today`) cites the
   rule's full sub-id.

Tooling exposes `is_enforceable(policy_id, rule_id) -> bool` and
`evaluate(rule_id, candidate) -> Result(verdict, citations[], exceptions[])`.
Agents MUST use these helpers; they MUST NOT re-implement the predicate.

**R3.** Citation format. Every machine-decidable finding MUST include a
square-bracketed sub-id anchor:

```
[POL-IAM-GROUP-NAMING.R1] <human-readable explanation>
Severity: required. Policy v1.0.0, effective 2026-06-01.
```

The bracketed `[POL-...-Rn]` is the parseable anchor — humans see it as a
tag, downstream systems extract it via regex.

**R4.** Five expected behaviors:

- **Q&A**: retrieve relevant policy prose; cite the policy ID; include
  `status` and `effective_date` so users know whether they are reading a
  current or future-dated policy.
- **Validation**: given a candidate (proposed group name, draft Conditional
  Access policy, etc.), evaluate against applicable rules; return
  `Result(verdict, citations[], exceptions[])`.
- **Generation**: produce compliant artifacts using the rule's `pattern`,
  `allowed_values`, or `decision_table`, plus examples; cite the rule
  sub-ids that constrained the generation.
- **Audit / drift**: given live state from Entra/Intune/SharePoint/etc.,
  walk all enforceable rules whose `applies_to.object_type` matches; emit
  findings with sub-id citations.
- **Authoring assistance**: when a user is drafting a new policy or
  exception, read the schema and template; suggest frontmatter and body
  content that conforms.

**R5.** Hard prohibitions:

- **Never invent rule IDs or framework tags.** If a citation cannot be
  grounded in a real `id` or schema-validated tag, the agent says
  "I do not have a rule for this" rather than fabricating one.
- **Never enforce a rule from a non-`effective` policy.** Drafts and
  superseded policies are read-only context, not enforceable.
- **Never silently elide an active exception.** If an exception applies to
  the rule being evaluated, the agent surfaces the exception ID and its
  expiration.
- **Never edit `policies/`, `schemas/`, `exceptions/`, or `crosswalks/`
  outside the PR workflow.** Direct writes bypass CODEOWNERS, CI, and the
  approval contract.

**R6.** Bootstrap discipline. An agent dropped into the repo cold MUST
read `CLAUDE.md` first. That file is intentionally tiny and links to this
contract for full detail. An agent that skips the bootstrap will produce
output inconsistent with the contract.

## Rationale

The dual-audience constraint of this framework — humans and AI agents
both reading the same source — is what made every other design decision
possible: stable IDs, schema-validated structures, the citation format,
the deterministic file layout. None of those help if agents don't actually
follow them. This policy is the conscious agreement.

The five expected behaviors (R4) are not an exhaustive catalog of what
agents *can* do; they are the behaviors the framework was *designed to
support*. An agent doing something outside this list (e.g., generating
free-form analytical reports about the policy library) is using the
framework, not betraying it; the policy doesn't prohibit such uses.

The hard prohibitions (R5) all serve the same goal: the framework's
authoritativeness. If agents fabricate citations, the citations stop
meaning anything. If agents enforce drafts, the lifecycle stops meaning
anything. If agents bypass exceptions, the exception process stops
meaning anything. The prohibitions are the integrity contract.

## Examples

**Compliant Q&A response:**

> Group naming follows POL-IAM-GROUP-NAMING.R1 (status: effective, v1.0.0,
> effective 2026-06-01): security group names must match the pattern
> `^sg-(az|m365|ad)-[a-z0-9]+-[a-z0-9-]+$`. Example: `sg-az-prod-finance-readers`.

**Compliant validation finding:**

```
[POL-IAM-GROUP-NAMING.R1] Group name 'Marketing-Team-2024' does not match
the required pattern '^sg-(az|m365|ad)-[a-z0-9]+-[a-z0-9-]+$'.
Suggested compliant name: 'sg-m365-marketing-general'.
Severity: required. Policy v1.0.0, effective 2026-06-01.
```

**Non-compliant counter-examples:**

```
# R5 — fabricated rule ID
[POL-IAM-GROUP-NAMING.R99] Group must be approved by IT before creation.
# (POL-IAM-GROUP-NAMING.R99 does not exist — this violates R5.)

# R5 — enforcing a draft policy
"You can't do that — POL-DAT-CLASSIFICATION.R3 requires you to..."
# (If POL-DAT-CLASSIFICATION is in `status: draft`, this violates R2 + R5.)

# R5 — silently eliding an exception
"Your group 'Finance-Legacy' violates POL-IAM-GROUP-NAMING.R1."
# (If EXC-2026-001 is active and cites POL-IAM-GROUP-NAMING.R1 for this
# group, the agent must surface that, not pretend it does not exist.)
```

## Implementation Guidance

**Reading the repo cold:**

1. Read `CLAUDE.md` (small, deterministic).
2. Skim `schemas/policy-frontmatter.schema.json` to know the required
   fields and shapes.
3. Skim `glossary/terms.md` to map domain vocabulary.
4. Read this contract for the full agent expectations.
5. Walk `policies/**/*.md` for content; consult `policies/**/*.rules.yaml`
   when machine-checkable rules apply.
6. Cross-check against `exceptions/*.md` before declaring a violation.

**Programmatic access (Python):**

```python
from ggi_policy import controls, io
from ggi_policy.repo import repo_root

# Walk every effective rule:
catalog = controls.load(repo_root() / "schemas/framework-controls.json")
for policy in io.iter_policies(repo_root() / "policies"):
    if policy.metadata["status"] != "effective":
        continue
    rules = io.load_rules(policy.path)
    for rule in (rules or {}).get("rules", []):
        # rule_id = f"{policy.metadata['id']}.{rule['id']}"
        # Use is_enforceable(...) before treating as authoritative.
        ...
```

**Authoring assistance:** when a user asks the agent to draft a new policy,
the agent SHOULD copy `templates/policy.md` and fill in the placeholders;
SHOULD validate schema constraints as the user types; SHOULD suggest
framework tags by querying `schemas/framework-controls.json`.

## Exceptions

This policy admits no exceptions. AI agents that operate on this
repository must comply with the rules above without exception. (An agent
that *cannot* comply — e.g., it cannot read schemas — should refuse to
operate at all rather than partially comply.)

## References

- POL-META-DOC-FRAMEWORK (companion: the framework definition)
- Design specification §9 (AI-agent contract):
  `docs/superpowers/specs/2026-05-02-policy-doc-framework-design.md`
- Bootstrap files: `CLAUDE.md`, `AGENTS.md`
- Schemas: `schemas/policy-frontmatter.schema.json`,
  `schemas/policy-rules.schema.json`, `schemas/exception.schema.json`,
  `schemas/framework-controls.schema.json`

## Revision History

- **1.0.0 (2026-05-03)** — Initial release. Translates design §9 into a
  real policy that AI agents read alongside human-facing documentation.
