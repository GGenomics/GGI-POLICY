## Change type

- [ ] **Rule change** — adds, removes, or tightens a rule (`R1`, `R2`, …)
- [ ] **Scope change** — adjusts `applies_to`, `frameworks`, or `domain`
- [ ] **Prose change** — clarification, typo, example
- [ ] **New policy**
- [ ] **Exception** — new or renewal
- [ ] **Framework / catalog refresh** — `fetch-controls` re-run
- [ ] **Tooling / framework infrastructure** — `tools/`, `schemas/`, CI

## Version bump rationale

If a policy is being modified, which semver bump applies and why?

- [ ] **MAJOR** — tightens or removes an existing rule (breaking change)
- [ ] **MINOR** — additive: new rule, new tag, expanded scope
- [ ] **PATCH** — prose / typo / clarification only
- [ ] **N/A** — not a policy change

## Communication plan (MAJOR changes only)

If this is a MAJOR change, what is the future `effective_date` and how
will downstream consumers be notified before that date?

## Validation

- [ ] `uv run pytest` passes locally
- [ ] `uv run ggi-policy validate` reports OK
- [ ] `uv run ggi-policy build-crosswalks --check` reports OK
- [ ] `uv run ggi-policy validate-deploy` reports OK (if `deploy/` was touched)

## Reviewer checklist

- [ ] Approvers in frontmatter match CODEOWNERS for the path
- [ ] Framework tags resolve against `framework-controls.json`
- [ ] If breaking, `effective_date` gives at least N days advance notice
- [ ] Revision history at the bottom of the policy is updated
