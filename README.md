# GGI Policy

Canonical home for General Genomics company policies covering data and application
governance and cybersecurity. Every policy in this repo is authored against
the framework defined by [POL-META-DOC-FRAMEWORK](policies/meta/doc-framework.md);
AI agents follow [POL-META-AI-AGENT-CONTRACT](policies/meta/ai-agent-contract.md);
human contributors start here.

## What's here

- **`policies/`** — domain-organized policy files. Each policy declares
  framework alignment via frontmatter and (optionally) machine-checkable
  rules in a sidecar `*.rules.yaml`.
- **`exceptions/`** — time-bound deviations from a specific rule, gated
  by an approver and a compensating control.
- **`crosswalks/`** — auto-generated coverage tables mapping NIST CSF 2.0,
  CIS Controls v8, SOC 2 TSC, HIPAA 45 CFR Part 164, NIST 800-53 Rev 5,
  and NIST 800-171 Rev 3 to GGI policies. Regenerated on every PR.
- **`glossary/`** — controlled domain vocabulary.
- **`templates/`** — copy-from-here for new policies, sidecars, exceptions.
- **`schemas/`** — JSON Schemas (the public contract for AI agents and CI)
  plus the populated framework-controls catalog.
- **`tools/`** — Python (`uv`-managed) tooling: validate, fetch catalog,
  build crosswalks, build site, validate manifests, and the three
  scheduled lifecycle bots.
- **`deploy/`** — kustomize manifests + Flux image-automation CRs for
  the on-prem k8s deployment, ready to promote to `ggi_internals`.
- **`docs/superpowers/`** — design spec and per-phase implementation plans
  (development reference, not published to the rendered site).

## Authoring a new policy

```bash
# 1. Copy templates into the right domain folder.
cp templates/policy.md policies/identity-and-access/your-slug.md
cp templates/policy.rules.yaml policies/identity-and-access/your-slug.rules.yaml

# 2. Fill in frontmatter and the nine body sections.

# 3. Run the local pipeline before opening a PR.
uv sync
uv run pytest
uv run ggi-policy validate
uv run ggi-policy build-crosswalks
```

The PR template will prompt for change type, version-bump rationale, and
(if MAJOR) a communication plan.

## Tooling commands

```bash
uv run ggi-policy validate            # repo-wide schema + consistency checks
uv run ggi-policy fetch-controls      # refresh schemas/framework-controls.json
uv run ggi-policy build-crosswalks    # regenerate crosswalks/<framework>.md
uv run ggi-policy build-crosswalks --check   # CI: fail if regen would change anything
uv run ggi-policy build-site          # render MkDocs site to site/
uv run ggi-policy validate-deploy     # structural validation of deploy/ kustomize
uv run ggi-policy check-reviews       # find policies past their review_cycle
uv run ggi-policy notify-effective    # post Teams cards for today's effective_date arrivals
uv run ggi-policy check-exceptions    # post Teams cards for expiring exceptions
```

## Operator setup checklist

The framework is fully functional with no operator configuration; the
following steps unlock the production deployment and the lifecycle bots.

### Phase 4 — Production deployment to k8s

- [ ] **Entra app registration** — create `ggi-policy-docs` in Azure portal
      with redirect URI `https://policy.ggenomics.internal/oauth2/callback`
      ([deploy/README.md §1](deploy/README.md#1-entra-app-registration))
- [ ] **DNS** — allocate `policy.ggenomics.internal` → ingress-nginx
      LoadBalancer IP
- [ ] **Vault entry** — `vault kv put secret/policy-docs/oauth2-proxy
      tenant_id=… client_id=… client_secret=… cookie_secret=…`
- [ ] **Promote to `ggi_internals`** — `cp -r deploy/apps/policy-docs
      ../ggi_internals/GitOps/k8s/prod/apps/policy-docs` and Flux
      image-automation CRs to wherever your cluster's bootstrap CRs live
- [ ] **Confirm `TODO(operator)` markers** — `grep -rn "TODO(operator)"
      deploy/` — six placeholders to verify against the airflow pattern

### Phase 5 — Lifecycle automation

- [ ] **Teams channel** — create `#policy-updates` and an incoming webhook
- [ ] **Repo Actions secret** — add `TEAMS_POLICY_WEBHOOK` at
      https://github.com/GGenomics/GGI-POLICY/settings/secrets/actions

The `review-due` GitHub label is auto-bootstrapped by the workflow on
first run; no manual `gh label create` is needed.

## Windows contributors

The MkDocs site uses three symlinks under `docs/` (`policies`, `crosswalks`,
`glossary`); plus `AGENTS.md` is a symlink to `CLAUDE.md`. Git for Windows
does not materialize symlinks by default. Run this once before cloning:

```sh
git config --global core.symlinks true
```

If you've already cloned, `git checkout main -- AGENTS.md docs/` after
enabling the config will recreate the symlinks.

## Design and plans

- **Design specification:**
  [`docs/superpowers/specs/2026-05-02-policy-doc-framework-design.md`](docs/superpowers/specs/2026-05-02-policy-doc-framework-design.md)
- **Implementation plans (Phase 1–6):**
  [`docs/superpowers/plans/`](docs/superpowers/plans/)

## License

Internal General Genomics, Inc. resource. Contact the CISO for access or use questions.
