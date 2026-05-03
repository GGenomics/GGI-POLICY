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
