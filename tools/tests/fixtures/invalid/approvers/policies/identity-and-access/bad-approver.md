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
approvers: [Unknown Role]
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
