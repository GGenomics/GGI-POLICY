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
