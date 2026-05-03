# GGI Policy

Canonical home for GGenomics company policies covering data and application
governance and cybersecurity.

- **Design:** [docs/superpowers/specs/2026-05-02-policy-doc-framework-design.md](docs/superpowers/specs/2026-05-02-policy-doc-framework-design.md)
- **Phase 1 plan:** [docs/superpowers/plans/2026-05-02-phase-1-foundation.md](docs/superpowers/plans/2026-05-02-phase-1-foundation.md)

This repo is in early bring-up. See `CLAUDE.md` for AI-agent guidance once it
is fleshed out (Phase 6).

## Contributing on Windows

The MkDocs site uses three symlinks under `docs/` (`policies`, `crosswalks`,
`glossary`) so existing root-level content paths render under the docs root.
Git for Windows does not materialize symlinks by default. Run this once before
cloning:

```sh
git config --global core.symlinks true
```

If you've already cloned, `git checkout main -- docs/` after enabling the
config will re-create the symlinks.
