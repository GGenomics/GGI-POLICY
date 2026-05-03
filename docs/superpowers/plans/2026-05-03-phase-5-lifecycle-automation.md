# Phase 5: Lifecycle automation — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add three scheduled GitHub Actions that surface lifecycle events — overdue policy reviews (as Issues), effective-date arrivals (as Teams notifications), and exception expirations (as Teams notifications). Land a PR template that prompts the right review questions. Close out the engineering carry-forwards from Phase 2 + Phase 4 final reviews.

**Architecture:** Three pure-Python helpers in `tools/ggi_policy/lifecycle.py` compute "what's overdue / effective today / expiring soon," given the loaded policy + exception state and a `today` value. A `tools/ggi_policy/teams.py` posts Adaptive Cards to an incoming-webhook URL via `httpx.post`. Three new CLI subcommands (`check-reviews`, `notify-effective`, `check-exceptions`) wire the helpers; each takes `--dry-run` so local invocations don't side-effect. A single scheduled workflow `.github/workflows/lifecycle.yml` runs all three daily at 13:00 UTC (06:00 PT). Tests inject `today` and use `respx`-style monkeypatching of httpx + the GitHub API client so the suite stays offline. After the bots, the plan closes Phase-2 carry-forwards (HIPAA XML test coverage, deterministic catalog sort) and Phase-4 hardening (kubectl-kustomize CI step, ingress security headers, namespace NetworkPolicy).

**Tech Stack:** Python 3.12+ (`uv`-managed), `click` for CLI (existing), `httpx` for Teams webhooks (existing), `gh` CLI in CI for issue creation (no new Python dep — shell-out from the workflow), GitHub Actions cron triggers, Adaptive Cards for Teams.

---

## Prerequisites

- Phase 4 is merged (HEAD on `origin/main` ≥ `13dac41`). 84 unit tests pass; `deploy/` manifests render via `kubectl kustomize`; `validate-deploy` CLI exists.
- Reference: design doc at [docs/superpowers/specs/2026-05-02-policy-doc-framework-design.md](../specs/2026-05-02-policy-doc-framework-design.md) §7.4 (review cadence), §7.5 (exceptions), §7.6 (change workflow), §10 (open items).
- **Operator action required before Phase 5 fully functions** (the bots tolerate missing config — they print "skipped: TEAMS_POLICY_WEBHOOK not set" and exit 0):
  1. Create the `#policy-updates` Teams channel in the GGenomics tenant.
  2. From channel settings → **Connectors → Incoming Webhook**, register a webhook named `GGI Policy` and copy the URL.
  3. Add it as a repo-level Actions secret named `TEAMS_POLICY_WEBHOOK` at https://github.com/GGenomics/GGI-POLICY/settings/secrets/actions.
- The GitHub teams (`@ggenomics/ciso`, `@ggenomics/it-director`, etc.) are already created with read access to the repo (per the user's confirmation). Phase 5 doesn't add or modify teams.

## File structure (locked-in decomposition)

```
GGI-POLICY/
├── tools/
│   ├── ggi_policy/
│   │   ├── lifecycle.py                       # NEW: pure logic for the 3 bots
│   │   ├── teams.py                           # NEW: Teams webhook poster
│   │   ├── controls.py                        # MODIFY: deterministic sort on save (Phase 2 carry)
│   │   ├── cli.py                             # MODIFY: add 3 lifecycle subcommands
│   │   └── fetchers/
│   │       └── hipaa.py                       # untouched (test-only addition below)
│   └── tests/
│       ├── test_lifecycle.py                  # NEW
│       ├── test_teams.py                      # NEW
│       ├── test_controls.py                   # MODIFY: add deterministic-sort test
│       ├── test_fetchers_hipaa.py             # MODIFY: add XML parser test
│       └── fixtures/
│           ├── lifecycle/                     # NEW: synthetic policy + exception trees
│           └── fetchers/
│               └── hipaa.ecfr.xml             # NEW: trimmed eCFR XML fixture
├── deploy/
│   └── apps/policy-docs/
│       ├── ingress.yaml                       # MODIFY: add security headers (Phase 4 carry)
│       └── network-policy.yaml                # NEW: deny-by-default + named allows
├── .github/
│   ├── PULL_REQUEST_TEMPLATE.md               # NEW
│   └── workflows/
│       ├── lifecycle.yml                      # NEW: 3 jobs, daily cron
│       └── validate.yml                       # MODIFY: add kubectl kustomize step (Phase 4 carry)
```

## Conventions

- **Commits:** Conventional Commits (`feat(lifecycle): ...`, `feat(teams): ...`, `chore(deploy): ...`, `test(hipaa): ...`).
- **TDD:** every helper in `lifecycle.py` and `teams.py` has paired tests with `today` injected as a parameter. No test calls real time, real GitHub API, or real Teams webhook.
- **`--dry-run` semantics:** every lifecycle subcommand accepts `--dry-run`. In dry-run mode, the bot prints what it would do (issue titles, Teams message bodies) and exits 0 without side-effects. Default is real-mode.
- **CI uses `gh` CLI for GitHub issues, `curl` for the Teams webhook fallback path; the Python code uses `httpx.post` directly.** Keeping the workflow shell-only for issue creation avoids a Python dep on `PyGithub`.
- **Scheduled cron: `0 13 * * *`** — 13:00 UTC = 06:00 PT (winter) / 07:00 PT (summer). Lands in the workday's first hour for an operator who's central to PT.

---

## Task 1: lifecycle helpers (shared logic)

**Files:**
- Create: `tools/ggi_policy/lifecycle.py`
- Create: `tools/tests/test_lifecycle.py`
- Create: `tools/tests/fixtures/lifecycle/policies/identity-and-access/sample.md`
- Create: `tools/tests/fixtures/lifecycle/policies/identity-and-access/sample.rules.yaml`
- Create: `tools/tests/fixtures/lifecycle/exceptions/EXC-2026-001-sample.md`

- [ ] **Step 1: Create the lifecycle policy fixture**

`tools/tests/fixtures/lifecycle/policies/identity-and-access/sample.md`:

```markdown
---
id: POL-IAM-SAMPLE
title: Sample policy for lifecycle tests
summary: Used by check-reviews and notify-effective tests.
domain: IAM
status: effective
version: 1.0.0
effective_date: 2026-06-01
last_reviewed: 2025-05-01
review_cycle: annual
owner: IT Director
approvers: [CISO, IT Director]
applies_to: [test scope]
supersedes: []
related: []
frameworks:
  nist_csf: [PR.AC-01]
external_references: []
---

## Purpose
Lifecycle tests reference this fixture.
```

`tools/tests/fixtures/lifecycle/policies/identity-and-access/sample.rules.yaml`:

```yaml
policy_id: POL-IAM-SAMPLE
rules:
  - { id: R1, statement: "test rule", type: flag, severity: required }
```

`tools/tests/fixtures/lifecycle/exceptions/EXC-2026-001-sample.md`:

```markdown
---
id: EXC-2026-001-SAMPLE
policy_ref: POL-IAM-SAMPLE.R1
requested_by: jane.doe@ggenomics.com
approver: CISO
approved_date: 2026-04-15
effective_date: 2026-04-15
expires: 2026-10-15
status: active
compensating_control: n/a
risk_acceptance: documented in RR-test
---

## Justification
test
```

- [ ] **Step 2: Write failing tests**

`tools/tests/test_lifecycle.py`:

```python
from datetime import date
from pathlib import Path

from ggi_policy import lifecycle


def test_overdue_reviews_includes_policy_past_review_cycle(fixtures_dir: Path) -> None:
    """sample.md has last_reviewed=2025-05-01 and review_cycle=annual.
    On 2026-05-15 (1 year + 14 days later), the policy is overdue."""
    policies_root = fixtures_dir / "lifecycle/policies"
    overdue = lifecycle.overdue_reviews(policies_root, today=date(2026, 5, 15))
    ids = [p["id"] for p in overdue]
    assert "POL-IAM-SAMPLE" in ids
    sample = next(p for p in overdue if p["id"] == "POL-IAM-SAMPLE")
    assert sample["owner"] == "IT Director"
    assert sample["last_reviewed"] == "2025-05-01"


def test_overdue_reviews_excludes_recently_reviewed(fixtures_dir: Path) -> None:
    """Same fixture, evaluated on 2026-04-30 (just before the 1-year mark) — not overdue."""
    policies_root = fixtures_dir / "lifecycle/policies"
    overdue = lifecycle.overdue_reviews(policies_root, today=date(2026, 4, 30))
    ids = [p["id"] for p in overdue]
    assert "POL-IAM-SAMPLE" not in ids


def test_overdue_reviews_skips_event_driven(fixtures_dir: Path, tmp_path: Path) -> None:
    """Policies with review_cycle: event-driven are never date-overdue."""
    src = (fixtures_dir / "lifecycle/policies/identity-and-access/sample.md").read_text()
    target = tmp_path / "policies/identity-and-access/sample.md"
    target.parent.mkdir(parents=True)
    target.write_text(src.replace("review_cycle: annual", "review_cycle: event-driven"))
    overdue = lifecycle.overdue_reviews(tmp_path / "policies", today=date(2030, 1, 1))
    assert overdue == []


def test_overdue_reviews_excludes_non_effective(fixtures_dir: Path, tmp_path: Path) -> None:
    """Draft / superseded / retired policies don't count as overdue."""
    src = (fixtures_dir / "lifecycle/policies/identity-and-access/sample.md").read_text()
    target = tmp_path / "policies/identity-and-access/sample.md"
    target.parent.mkdir(parents=True)
    target.write_text(src.replace("status: effective", "status: draft"))
    overdue = lifecycle.overdue_reviews(tmp_path / "policies", today=date(2030, 1, 1))
    assert overdue == []


def test_effective_today_returns_policies_whose_date_matches(fixtures_dir: Path) -> None:
    policies_root = fixtures_dir / "lifecycle/policies"
    effective = lifecycle.effective_today(policies_root, today=date(2026, 6, 1))
    ids = [p["id"] for p in effective]
    assert "POL-IAM-SAMPLE" in ids


def test_effective_today_excludes_other_dates(fixtures_dir: Path) -> None:
    policies_root = fixtures_dir / "lifecycle/policies"
    effective = lifecycle.effective_today(policies_root, today=date(2026, 5, 31))
    assert effective == []


def test_expiring_exceptions_at_30_day_milestone(fixtures_dir: Path) -> None:
    """sample exception expires=2026-10-15. On 2026-09-15 (30 days before) it shows up."""
    exceptions_root = fixtures_dir / "lifecycle/exceptions"
    notices = lifecycle.expiring_exceptions(exceptions_root, today=date(2026, 9, 15))
    ids = [n["id"] for n in notices]
    assert "EXC-2026-001-SAMPLE" in ids
    notice = next(n for n in notices if n["id"] == "EXC-2026-001-SAMPLE")
    assert notice["days_until_expiry"] == 30


def test_expiring_exceptions_skips_non_milestone_days(fixtures_dir: Path) -> None:
    """29 days before — not a milestone. Skip."""
    exceptions_root = fixtures_dir / "lifecycle/exceptions"
    notices = lifecycle.expiring_exceptions(exceptions_root, today=date(2026, 9, 16))
    assert notices == []


def test_expiring_exceptions_after_expiry_continues_daily(fixtures_dir: Path) -> None:
    """Day after expiry: still flagged."""
    exceptions_root = fixtures_dir / "lifecycle/exceptions"
    notices = lifecycle.expiring_exceptions(exceptions_root, today=date(2026, 10, 16))
    ids = [n["id"] for n in notices]
    assert "EXC-2026-001-SAMPLE" in ids
    n = notices[0]
    assert n["days_until_expiry"] == -1
    assert n["expired"] is True


def test_expiring_exceptions_skips_revoked(fixtures_dir: Path, tmp_path: Path) -> None:
    src = (fixtures_dir / "lifecycle/exceptions/EXC-2026-001-sample.md").read_text()
    target = tmp_path / "exceptions/EXC-2026-001-sample.md"
    target.parent.mkdir(parents=True)
    target.write_text(src.replace("status: active", "status: revoked"))
    notices = lifecycle.expiring_exceptions(tmp_path / "exceptions", today=date(2026, 9, 15))
    assert notices == []
```

Run: `uv run pytest tools/tests/test_lifecycle.py -v`
Expected: import error for `ggi_policy.lifecycle`.

- [ ] **Step 3: Implement `lifecycle.py`**

`tools/ggi_policy/lifecycle.py`:

```python
"""Pure logic for the three scheduled lifecycle bots.

Each function takes ``today`` as a parameter so tests can inject any date
without freezing real time.
"""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

from ggi_policy import io


_REVIEW_CYCLE_DAYS = {
    "annual":    365,
    "biannual":  182,   # half a year
    "triennial": 1095,  # 3 years
}


_EXCEPTION_MILESTONES = {30, 14, 7, 3, 1, 0}


def _as_date(value) -> date | None:
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return datetime.strptime(value, "%Y-%m-%d").date()
        except ValueError:
            return None
    return None


def overdue_reviews(policies_root: Path, *, today: date) -> list[dict]:
    """Return one dict per effective policy whose last_reviewed + review_cycle < today.
    Each dict has: id, title, owner, last_reviewed, review_cycle, path."""
    if not policies_root.exists():
        return []
    out: list[dict] = []
    for policy in io.iter_policies(policies_root):
        meta = policy.metadata
        if meta.get("status") != "effective":
            continue
        cycle = meta.get("review_cycle")
        cycle_days = _REVIEW_CYCLE_DAYS.get(cycle)
        if cycle_days is None:
            continue  # event-driven or unrecognized
        last_reviewed = _as_date(meta.get("last_reviewed"))
        if last_reviewed is None:
            continue
        if (today - last_reviewed).days <= cycle_days:
            continue
        out.append({
            "id":            meta.get("id", ""),
            "title":         meta.get("title", ""),
            "owner":         meta.get("owner", ""),
            "last_reviewed": meta.get("last_reviewed", ""),
            "review_cycle":  cycle,
            "path":          str(policy.path),
        })
    return out


def effective_today(policies_root: Path, *, today: date) -> list[dict]:
    """Return one dict per effective policy whose effective_date == today."""
    if not policies_root.exists():
        return []
    out: list[dict] = []
    for policy in io.iter_policies(policies_root):
        meta = policy.metadata
        if meta.get("status") != "effective":
            continue
        eff = _as_date(meta.get("effective_date"))
        if eff != today:
            continue
        out.append({
            "id":             meta.get("id", ""),
            "title":          meta.get("title", ""),
            "owner":          meta.get("owner", ""),
            "version":        meta.get("version", ""),
            "effective_date": meta.get("effective_date", ""),
            "path":           str(policy.path),
        })
    return out


def expiring_exceptions(exceptions_root: Path, *, today: date) -> list[dict]:
    """Return one dict per active exception that hits a notification milestone today.

    Notification triggers (days_until_expiry):
      - In {30, 14, 7, 3, 1, 0}: scheduled milestone
      - Less than 0 (already expired): every day until status changes
    """
    if not exceptions_root.exists():
        return []
    out: list[dict] = []
    for exc in io.iter_exceptions(exceptions_root):
        meta = exc.metadata
        if meta.get("status") != "active":
            continue
        expires = _as_date(meta.get("expires"))
        if expires is None:
            continue
        delta = (expires - today).days
        if not (delta in _EXCEPTION_MILESTONES or delta < 0):
            continue
        out.append({
            "id":                 meta.get("id", ""),
            "policy_ref":         meta.get("policy_ref", ""),
            "approver":           meta.get("approver", ""),
            "expires":            meta.get("expires", ""),
            "days_until_expiry":  delta,
            "expired":            delta < 0,
            "path":               str(exc.path),
        })
    return out
```

- [ ] **Step 4: Run tests**

```bash
uv run pytest tools/tests/test_lifecycle.py -v
```

Expected: 10 passed.

- [ ] **Step 5: Run full suite**

```bash
uv run pytest -q
```

Expected: 94 passed (84 prior + 10 new).

- [ ] **Step 6: Commit**

```bash
git add tools/ggi_policy/lifecycle.py tools/tests/test_lifecycle.py \
        tools/tests/fixtures/lifecycle
git commit -m "$(cat <<'EOF'
feat(lifecycle): pure helpers for the 3 scheduled bots

overdue_reviews(): effective policies whose last_reviewed + review_cycle
 has passed. Skips event-driven and non-effective.

effective_today(): effective policies whose effective_date is today.

expiring_exceptions(): active exceptions at notification milestones
 (30/14/7/3/1/0 days) AND every day after expiry until status changes.

Each function takes `today` as a parameter so tests can inject dates
without freezing real time. 10 tests cover the matrix.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 2: Teams webhook poster

**Files:**
- Create: `tools/ggi_policy/teams.py`
- Create: `tools/tests/test_teams.py`

- [ ] **Step 1: Write failing tests**

`tools/tests/test_teams.py`:

```python
from unittest.mock import MagicMock, patch

import httpx
import pytest

from ggi_policy import teams


def test_post_card_sends_adaptive_card_payload() -> None:
    mock_resp = MagicMock(); mock_resp.raise_for_status = MagicMock()
    with patch("ggi_policy.teams.httpx.post", return_value=mock_resp) as p:
        teams.post_card("https://outlook.office.com/webhook/xyz", title="t", body="b")
    p.assert_called_once()
    kwargs = p.call_args.kwargs
    payload = kwargs["json"]
    assert payload["type"] == "message"
    cards = payload["attachments"]
    assert len(cards) == 1
    card = cards[0]["content"]
    assert card["type"] == "AdaptiveCard"
    bodies = [b for b in card["body"]]
    # Title is in the first TextBlock, body text in the second
    assert any("t" in b.get("text", "") for b in bodies)
    assert any("b" in b.get("text", "") for b in bodies)


def test_post_card_raises_on_non_2xx() -> None:
    mock_resp = MagicMock()
    mock_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
        "500", request=MagicMock(), response=MagicMock(status_code=500)
    )
    with patch("ggi_policy.teams.httpx.post", return_value=mock_resp):
        with pytest.raises(httpx.HTTPStatusError):
            teams.post_card("https://x", title="t", body="b")


def test_post_card_uses_bounded_timeout() -> None:
    mock_resp = MagicMock(); mock_resp.raise_for_status = MagicMock()
    with patch("ggi_policy.teams.httpx.post", return_value=mock_resp) as p:
        teams.post_card("https://x", title="t", body="b")
    assert p.call_args.kwargs.get("timeout") is not None
```

- [ ] **Step 2: Implement `teams.py`**

`tools/ggi_policy/teams.py`:

```python
"""Microsoft Teams Adaptive Card poster for the lifecycle bots."""

import httpx


_DEFAULT_TIMEOUT = httpx.Timeout(connect=5.0, read=15.0, write=5.0, pool=5.0)


def post_card(webhook_url: str, *, title: str, body: str, action_url: str | None = None) -> None:
    """Post an Adaptive Card with a title, body, and optional 'Open' action button.

    Raises httpx.HTTPStatusError on non-2xx responses.
    """
    card_body: list[dict] = [
        {
            "type": "TextBlock",
            "size": "Medium",
            "weight": "Bolder",
            "wrap": True,
            "text": title,
        },
        {
            "type": "TextBlock",
            "wrap": True,
            "text": body,
        },
    ]
    actions: list[dict] = []
    if action_url:
        actions.append({"type": "Action.OpenUrl", "title": "Open", "url": action_url})

    payload = {
        "type": "message",
        "attachments": [
            {
                "contentType": "application/vnd.microsoft.card.adaptive",
                "content": {
                    "type":    "AdaptiveCard",
                    "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                    "version": "1.5",
                    "body":    card_body,
                    "actions": actions,
                },
            }
        ],
    }
    resp = httpx.post(webhook_url, json=payload, timeout=_DEFAULT_TIMEOUT)
    resp.raise_for_status()
```

- [ ] **Step 3: Run tests + suite**

```bash
uv run pytest tools/tests/test_teams.py -v
uv run pytest -q
```

Expected: 3 passed for teams; 97 total.

- [ ] **Step 4: Commit**

```bash
git add tools/ggi_policy/teams.py tools/tests/test_teams.py
git commit -m "$(cat <<'EOF'
feat(teams): Adaptive Card webhook poster

Posts a Teams Adaptive Card to an incoming-webhook URL. Three tests
cover payload shape, error handling, and timeout. notify-effective
and check-exceptions both use this; check-reviews uses gh issue create
in the workflow itself.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 3: `check-reviews` CLI subcommand

**Files:**
- Modify: `tools/ggi_policy/cli.py`
- Modify: `tools/tests/test_cli.py`

- [ ] **Step 1: Wire the CLI subcommand**

Read `tools/ggi_policy/cli.py`. Append a new command after `validate-deploy` but before `if __name__ == "__main__":`:

```python
@main.command("check-reviews")
@click.option("--today", "today_opt", type=click.DateTime(formats=["%Y-%m-%d"]),
              default=None, help="Override today (default: actual date).")
@click.option("--dry-run", is_flag=True, default=False)
@click.option("--repo-root", "repo_root_opt",
              type=click.Path(exists=True, file_okay=False, path_type=Path),
              default=None)
def check_reviews(today_opt, dry_run: bool, repo_root_opt: Path | None) -> None:
    """List effective policies whose review_cycle has elapsed.

    The CI workflow pipes this output to `gh issue create` to file Issues.
    """
    from datetime import date as _date

    from ggi_policy import lifecycle

    root = (repo_root_opt or repo_root()).resolve()
    today = today_opt.date() if today_opt else _date.today()
    overdue = lifecycle.overdue_reviews(root / "policies", today=today)

    if not overdue:
        click.echo(f"OK: no overdue reviews on {today.isoformat()}")
        return

    for entry in overdue:
        title = f"Review Due: {entry['id']}"
        body = (
            f"Policy {entry['id']} (\"{entry['title']}\") was last reviewed "
            f"on {entry['last_reviewed']} with a {entry['review_cycle']} review cycle. "
            f"Owner: {entry['owner']}. "
            f"Open a PR that bumps last_reviewed (re-attestation)."
        )
        if dry_run:
            click.echo(f"[dry-run] would create issue: {title}")
        else:
            # Tab-separated so the workflow can `awk` cleanly.
            click.echo(f"OVERDUE\t{title}\t{entry['owner']}\t{body}")
```

- [ ] **Step 2: Add CLI test**

Append to `tools/tests/test_cli.py`:

```python
def test_check_reviews_dry_run_outputs_titles(fixtures_dir: Path) -> None:
    """The fixture's sample.md is overdue on 2026-05-15. --dry-run prints a
    'would create issue' line and exits 0."""
    runner = CliRunner()
    result = runner.invoke(main, [
        "check-reviews",
        "--repo-root", str(fixtures_dir / "lifecycle"),
        "--today", "2026-05-15",
        "--dry-run",
    ])
    assert result.exit_code == 0, result.output
    assert "[dry-run] would create issue: Review Due: POL-IAM-SAMPLE" in result.output


def test_check_reviews_clean_when_nothing_overdue(fixtures_dir: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(main, [
        "check-reviews",
        "--repo-root", str(fixtures_dir / "lifecycle"),
        "--today", "2026-04-30",
        "--dry-run",
    ])
    assert result.exit_code == 0
    assert "OK: no overdue reviews" in result.output
```

- [ ] **Step 3: Run tests**

```bash
uv run pytest tools/tests/test_cli.py -v
uv run pytest -q
```

Expected: 7 passed for test_cli (5 prior + 2 new); 99 total.

- [ ] **Step 4: Commit**

```bash
git add tools/ggi_policy/cli.py tools/tests/test_cli.py
git commit -m "$(cat <<'EOF'
feat(cli): check-reviews subcommand

Lists overdue policy reviews. In dry-run mode, prints 'would create
issue: Review Due: POL-...' lines. In real mode, emits tab-separated
records the GHA workflow pipes to `gh issue create`.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 4: `notify-effective` CLI subcommand

**Files:**
- Modify: `tools/ggi_policy/cli.py`
- Modify: `tools/tests/test_cli.py`

- [ ] **Step 1: Wire the CLI**

In `tools/ggi_policy/cli.py`, append after `check-reviews`:

```python
@main.command("notify-effective")
@click.option("--today", "today_opt", type=click.DateTime(formats=["%Y-%m-%d"]),
              default=None)
@click.option("--dry-run", is_flag=True, default=False)
@click.option("--repo-root", "repo_root_opt",
              type=click.Path(exists=True, file_okay=False, path_type=Path),
              default=None)
@click.option("--webhook-url", "webhook_url_opt",
              envvar="TEAMS_POLICY_WEBHOOK", default=None,
              help="Teams incoming-webhook URL (defaults to $TEAMS_POLICY_WEBHOOK).")
def notify_effective(today_opt, dry_run: bool, repo_root_opt: Path | None,
                     webhook_url_opt: str | None) -> None:
    """Post a Teams notification for each policy whose effective_date is today."""
    from datetime import date as _date

    from ggi_policy import lifecycle, teams

    root = (repo_root_opt or repo_root()).resolve()
    today = today_opt.date() if today_opt else _date.today()
    arriving = lifecycle.effective_today(root / "policies", today=today)

    if not arriving:
        click.echo(f"OK: no policies become effective on {today.isoformat()}")
        return

    if not webhook_url_opt and not dry_run:
        click.echo("skipped: TEAMS_POLICY_WEBHOOK not set", err=True)
        return

    for entry in arriving:
        title = f"Policy now effective: {entry['id']}"
        body = (
            f"**{entry['title']}** (v{entry['version']}) is effective as of "
            f"{entry['effective_date']}. Owner: {entry['owner']}."
        )
        if dry_run:
            click.echo(f"[dry-run] would post: {title} | {body}")
        else:
            teams.post_card(webhook_url_opt, title=title, body=body)
            click.echo(f"posted: {title}")
```

- [ ] **Step 2: Add CLI tests**

Append to `tools/tests/test_cli.py`:

```python
def test_notify_effective_dry_run(fixtures_dir: Path) -> None:
    """Sample fixture has effective_date 2026-06-01."""
    runner = CliRunner()
    result = runner.invoke(main, [
        "notify-effective",
        "--repo-root", str(fixtures_dir / "lifecycle"),
        "--today", "2026-06-01",
        "--dry-run",
    ])
    assert result.exit_code == 0, result.output
    assert "[dry-run] would post" in result.output
    assert "POL-IAM-SAMPLE" in result.output


def test_notify_effective_skipped_without_webhook(fixtures_dir: Path) -> None:
    """No webhook URL, not dry-run: log and exit 0 (no traceback)."""
    runner = CliRunner()
    # Explicitly clear env so the test doesn't pick up a real webhook.
    result = runner.invoke(main, [
        "notify-effective",
        "--repo-root", str(fixtures_dir / "lifecycle"),
        "--today", "2026-06-01",
    ], env={"TEAMS_POLICY_WEBHOOK": ""})
    assert result.exit_code == 0
    assert "skipped" in result.output


def test_notify_effective_clean_when_no_match(fixtures_dir: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(main, [
        "notify-effective",
        "--repo-root", str(fixtures_dir / "lifecycle"),
        "--today", "2026-06-02",
        "--dry-run",
    ])
    assert result.exit_code == 0
    assert "no policies become effective" in result.output
```

- [ ] **Step 3: Run + commit**

```bash
uv run pytest -q
git add tools/ggi_policy/cli.py tools/tests/test_cli.py
git commit -m "$(cat <<'EOF'
feat(cli): notify-effective subcommand

Posts a Teams Adaptive Card per policy whose effective_date matches
today. --webhook-url defaults to $TEAMS_POLICY_WEBHOOK. If no webhook
is configured and not in dry-run mode, the bot logs 'skipped' and
exits 0 — keeps the workflow green when the operator hasn't set up
Teams yet.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

Expected: 102 passed (99 prior + 3 new).

---

## Task 5: `check-exceptions` CLI subcommand

**Files:**
- Modify: `tools/ggi_policy/cli.py`
- Modify: `tools/tests/test_cli.py`

- [ ] **Step 1: Wire the CLI**

Append to `tools/ggi_policy/cli.py` after `notify-effective`:

```python
@main.command("check-exceptions")
@click.option("--today", "today_opt", type=click.DateTime(formats=["%Y-%m-%d"]),
              default=None)
@click.option("--dry-run", is_flag=True, default=False)
@click.option("--repo-root", "repo_root_opt",
              type=click.Path(exists=True, file_okay=False, path_type=Path),
              default=None)
@click.option("--webhook-url", "webhook_url_opt",
              envvar="TEAMS_POLICY_WEBHOOK", default=None)
def check_exceptions(today_opt, dry_run: bool, repo_root_opt: Path | None,
                     webhook_url_opt: str | None) -> None:
    """Post a Teams notification for active exceptions hitting an expiration milestone."""
    from datetime import date as _date

    from ggi_policy import lifecycle, teams

    root = (repo_root_opt or repo_root()).resolve()
    today = today_opt.date() if today_opt else _date.today()
    notices = lifecycle.expiring_exceptions(root / "exceptions", today=today)

    if not notices:
        click.echo(f"OK: no exception notifications for {today.isoformat()}")
        return

    if not webhook_url_opt and not dry_run:
        click.echo("skipped: TEAMS_POLICY_WEBHOOK not set", err=True)
        return

    for n in notices:
        if n["expired"]:
            title = f"Exception EXPIRED: {n['id']}"
            body = (
                f"Cites {n['policy_ref']}. Approver: {n['approver']}. "
                f"Expired on {n['expires']} ({-n['days_until_expiry']} day(s) ago). "
                f"This exception must be renewed via PR or revoked."
            )
        else:
            title = f"Exception expiring in {n['days_until_expiry']} day(s): {n['id']}"
            body = (
                f"Cites {n['policy_ref']}. Approver: {n['approver']}. "
                f"Expires on {n['expires']}."
            )
        if dry_run:
            click.echo(f"[dry-run] would post: {title} | {body}")
        else:
            teams.post_card(webhook_url_opt, title=title, body=body)
            click.echo(f"posted: {title}")
```

- [ ] **Step 2: Add CLI tests**

Append to `tools/tests/test_cli.py`:

```python
def test_check_exceptions_at_30_day_milestone(fixtures_dir: Path) -> None:
    """Sample exception expires 2026-10-15. On 2026-09-15 it's the 30-day milestone."""
    runner = CliRunner()
    result = runner.invoke(main, [
        "check-exceptions",
        "--repo-root", str(fixtures_dir / "lifecycle"),
        "--today", "2026-09-15",
        "--dry-run",
    ])
    assert result.exit_code == 0, result.output
    assert "expiring in 30 day(s)" in result.output
    assert "EXC-2026-001-SAMPLE" in result.output


def test_check_exceptions_after_expiry(fixtures_dir: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(main, [
        "check-exceptions",
        "--repo-root", str(fixtures_dir / "lifecycle"),
        "--today", "2026-10-16",
        "--dry-run",
    ])
    assert result.exit_code == 0, result.output
    assert "EXPIRED" in result.output


def test_check_exceptions_silent_on_non_milestone_day(fixtures_dir: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(main, [
        "check-exceptions",
        "--repo-root", str(fixtures_dir / "lifecycle"),
        "--today", "2026-09-16",
        "--dry-run",
    ])
    assert result.exit_code == 0
    assert "no exception notifications" in result.output
```

- [ ] **Step 3: Run + commit**

```bash
uv run pytest -q
git add tools/ggi_policy/cli.py tools/tests/test_cli.py
git commit -m "$(cat <<'EOF'
feat(cli): check-exceptions subcommand

Posts a Teams card per active exception hitting a notification
milestone (30/14/7/3/1/0 days before expiry, then daily until status
changes). EXPIRED exceptions get an attention-grabbing title.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

Expected: 105 passed (102 prior + 3 new).

---

## Task 6: Scheduled lifecycle workflow

**Files:**
- Create: `.github/workflows/lifecycle.yml`

One workflow, three jobs running in parallel daily at 13:00 UTC.

- [ ] **Step 1: Create the workflow**

`.github/workflows/lifecycle.yml`:

```yaml
name: lifecycle

on:
  schedule:
    - cron: "0 13 * * *"   # 13:00 UTC = 06:00 PT (winter) / 07:00 PT (summer)
  workflow_dispatch:        # let an operator trigger manually too

permissions:
  contents: read
  issues: write             # check-reviews creates issues

jobs:
  check-reviews:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v3
        with: { version: "latest" }
      - run: uv python install 3.12
      - run: uv sync --frozen
      - name: Find overdue reviews
        id: find
        run: uv run ggi-policy check-reviews > overdue.tsv
      - name: Open issues
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          if [[ ! -s overdue.tsv ]] || ! grep -q '^OVERDUE' overdue.tsv; then
            echo "no overdue reviews"
            exit 0
          fi
          while IFS=$'\t' read -r kind title owner body; do
            [[ "$kind" != "OVERDUE" ]] && continue
            existing=$(gh issue list --state open --search "in:title \"$title\"" --json number --jq '.[0].number' || true)
            if [[ -n "$existing" ]]; then
              echo "issue already open: #$existing — $title"
              continue
            fi
            gh issue create \
              --title "$title" \
              --body "$body" \
              --label "review-due"
          done < overdue.tsv

  notify-effective:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v3
        with: { version: "latest" }
      - run: uv python install 3.12
      - run: uv sync --frozen
      - name: Notify effective-date arrivals
        env:
          TEAMS_POLICY_WEBHOOK: ${{ secrets.TEAMS_POLICY_WEBHOOK }}
        run: uv run ggi-policy notify-effective

  check-exceptions:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v3
        with: { version: "latest" }
      - run: uv python install 3.12
      - run: uv sync --frozen
      - name: Notify exception expirations
        env:
          TEAMS_POLICY_WEBHOOK: ${{ secrets.TEAMS_POLICY_WEBHOOK }}
        run: uv run ggi-policy check-exceptions
```

The `review-due` label needs to exist on the repo for `gh issue create --label review-due` to attach it. The first run of `check-reviews` will fail with `gh: could not add label: 'review-due' not found`. Operator action: create the label once via `gh label create review-due --color D93F0B --description "Policy review past its review_cycle"` (one-time setup).

- [ ] **Step 2: Verify workflow YAML**

```bash
uv run python -c "import yaml; list(yaml.safe_load_all(open('.github/workflows/lifecycle.yml'))); print('OK')"
```

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/lifecycle.yml
git commit -m "$(cat <<'EOF'
ci(lifecycle): daily workflow for the 3 scheduled bots

Runs at 13:00 UTC daily. Three parallel jobs:
- check-reviews: shells out to `gh issue create` for each overdue policy,
  guarding against duplicates by searching existing open issues.
- notify-effective: posts Teams cards for policies whose effective_date
  is today.
- check-exceptions: posts Teams cards at expiration milestones.

Operator one-time action: `gh label create review-due --color D93F0B`
on the repo so the issue creation can attach the label. The workflow
is also workflow_dispatch-able for manual ad-hoc runs.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 7: PR template

**Files:**
- Create: `.github/PULL_REQUEST_TEMPLATE.md`

- [ ] **Step 1: Create the template**

`.github/PULL_REQUEST_TEMPLATE.md`:

```markdown
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
```

- [ ] **Step 2: Commit**

```bash
git add .github/PULL_REQUEST_TEMPLATE.md
git commit -m "$(cat <<'EOF'
docs(pr-template): prompt change-type, version bump, and validation status

Standardizes the questions every policy/exception/tooling PR answers.
GitHub auto-populates PR descriptions from this file.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 8: Phase 2 carry-forward — deterministic catalog sort

**Files:**
- Modify: `tools/ggi_policy/controls.py`
- Modify: `tools/tests/test_controls.py`
- Modify: `schemas/framework-controls.json` (regenerated after change)

`controls.save()` currently uses `sort_keys=False`, leaving framework + control ordering at the mercy of the fetcher. Sorting controls by `id` per framework gives reviewable diffs when refreshing the catalog.

- [ ] **Step 1: Modify `save()`**

Read `tools/ggi_policy/controls.py`. The current `save` is:

```python
def save(per_framework: dict[str, FrameworkData], path: Path) -> None:
    """Write the merged catalog to `path`. Overwrites existing content."""
    payload = {"frameworks": {name: fd.to_json() for name, fd in per_framework.items()}}
    path.write_text(json.dumps(payload, indent=2, sort_keys=False) + "\n")
```

Replace with:

```python
def save(per_framework: dict[str, FrameworkData], path: Path) -> None:
    """Write the merged catalog to `path`. Overwrites existing content.

    Frameworks appear in REGISTRY order (insertion-stable for Python 3.7+).
    Within each framework, controls are sorted by id so refresh PRs produce
    reviewable diffs even when an upstream fetcher re-orders entries.
    """
    out_frameworks: dict[str, dict] = {}
    for name, fd in per_framework.items():
        framework_json = fd.to_json()
        framework_json["controls"] = sorted(framework_json["controls"], key=lambda c: c["id"])
        out_frameworks[name] = framework_json
    payload = {"frameworks": out_frameworks}
    path.write_text(json.dumps(payload, indent=2, sort_keys=False) + "\n")
```

- [ ] **Step 2: Add a test**

Append to `tools/tests/test_controls.py`:

```python
def test_save_sorts_controls_by_id_within_framework(tmp_path: Path) -> None:
    from datetime import date

    from ggi_policy.fetchers._models import Control, FrameworkData, Metadata

    fd = FrameworkData(
        metadata=Metadata(
            version="1", fetched_at=date(2026, 5, 2),
            source_url="https://x", fetcher="cis",
        ),
        controls=[Control(id="6.10", title="z"), Control(id="5.4", title="a"), Control(id="6.1", title="b")],
    )
    target = tmp_path / "fc.json"
    controls.save({"cis": fd}, target)
    loaded = controls.load(target)
    ids = [c["id"] for c in loaded["frameworks"]["cis"]["controls"]]
    assert ids == ["5.4", "6.1", "6.10"]
```

- [ ] **Step 3: Run tests**

```bash
uv run pytest tools/tests/test_controls.py -v
```

Expected: 6 passed (5 prior + 1 new).

- [ ] **Step 4: Refresh the committed catalog**

```bash
uv run ggi-policy fetch-controls
uv run ggi-policy build-crosswalks
uv run pytest -q
```

Expected: tests still pass; the diff on `schemas/framework-controls.json` should now show controls in sorted order, and `crosswalks/*.md` files should be regenerated to match.

- [ ] **Step 5: Commit**

```bash
git add tools/ggi_policy/controls.py tools/tests/test_controls.py \
        schemas/framework-controls.json crosswalks/
git commit -m "$(cat <<'EOF'
fix(controls): deterministic sort of controls within each framework

controls.save() now sorts controls by id before serializing. Refresh
PRs (fetch-controls re-run) will produce reviewable diffs even when
upstream fetchers shuffle ordering.

Catalog regenerated; six crosswalk pages re-rendered to match the new
sort order.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 9: Phase 2 carry-forward — HIPAA XML test coverage

**Files:**
- Create: `tools/tests/fixtures/fetchers/hipaa.ecfr.xml`
- Modify: `tools/tests/test_fetchers_hipaa.py`

The HIPAA fetcher's live `fetch()` consumes XML from the eCFR API, but only the JSON path (`fetch_from_text`) had unit tests. This task adds an XML fixture and tests for `fetch_from_xml`.

- [ ] **Step 1: Create the XML fixture**

`tools/tests/fixtures/fetchers/hipaa.ecfr.xml`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<DLPSTEXTCLASS>
  <DIV5 TYPE="CHAPTER" N="A" NODE="45:1.0.1">
    <DIV6 TYPE="SUBCHAP" N="C">
      <DIV7 TYPE="PART" N="164">
        <HEAD>PART 164—SECURITY AND PRIVACY</HEAD>
        <DIV8 TYPE="SECTION" N="164.308">
          <HEAD>§ 164.308 Administrative safeguards.</HEAD>
          <P>(a) <I>Standards.</I></P>
          <P>(a)(1) <I>Security management process.</I> Implement policies and procedures.</P>
          <P>(a)(4) <I>Information access management.</I> Implement policies and procedures for authorizing access to electronic protected health information.</P>
        </DIV8>
        <DIV8 TYPE="SECTION" N="164.312">
          <HEAD>§ 164.312 Technical safeguards.</HEAD>
          <P>(a)(1) <I>Access control.</I> Implement technical policies and procedures.</P>
          <P>(a)(2)(i) <I>Unique user identification.</I> Assign a unique name and/or number for identifying and tracking user identity.</P>
        </DIV8>
      </DIV7>
    </DIV6>
  </DIV5>
</DLPSTEXTCLASS>
```

- [ ] **Step 2: Add tests**

Append to `tools/tests/test_fetchers_hipaa.py`:

```python
def test_fetch_from_xml_parses_paragraph_ids(fixtures_dir: Path) -> None:
    from ggi_policy.fetchers import hipaa

    text = (fixtures_dir / "fetchers/hipaa.ecfr.xml").read_text()
    fd = hipaa.fetch_from_xml(text, fetched_at=date(2026, 5, 2))
    ids = {c.id for c in fd.controls}
    assert "164.308(a)(1)" in ids
    assert "164.308(a)(4)" in ids
    assert "164.312(a)(2)(i)" in ids


def test_fetch_from_xml_titles_come_from_italic_headers(fixtures_dir: Path) -> None:
    from ggi_policy.fetchers import hipaa

    text = (fixtures_dir / "fetchers/hipaa.ecfr.xml").read_text()
    fd = hipaa.fetch_from_xml(text, fetched_at=date(2026, 5, 2))
    by_id = {c.id: c.title for c in fd.controls}
    assert "Information access management" in by_id["164.308(a)(4)"]


def test_fetch_from_xml_dedups_duplicate_paragraph_ids(fixtures_dir: Path, tmp_path: Path) -> None:
    """Sections that emit the same paragraph id more than once (e.g., parallel
    definitions in §164.501) are dedup'd: first occurrence wins."""
    from ggi_policy.fetchers import hipaa

    xml_with_dup = """<?xml version="1.0" encoding="UTF-8"?>
<DLPSTEXTCLASS>
  <DIV7 TYPE="PART" N="164">
    <DIV8 TYPE="SECTION" N="164.501">
      <HEAD>§ 164.501 Definitions.</HEAD>
      <P>(1) <I>First definition.</I></P>
      <P>(2) <I>Second definition.</I></P>
      <P>(1) <I>Third definition (parallel structure).</I></P>
    </DIV8>
  </DIV7>
</DLPSTEXTCLASS>"""
    fd = hipaa.fetch_from_xml(xml_with_dup, fetched_at=date(2026, 5, 2))
    ids = [c.id for c in fd.controls]
    # First occurrence wins for "164.501(1)"; the second-occurrence "Third
    # definition" is dropped.
    assert ids.count("164.501(1)") == 1
    assert "164.501(2)" in ids
```

- [ ] **Step 3: Run tests**

```bash
uv run pytest tools/tests/test_fetchers_hipaa.py -v
```

Expected: 6 passed (3 prior + 3 new).

- [ ] **Step 4: Commit**

```bash
git add tools/tests/fixtures/fetchers/hipaa.ecfr.xml tools/tests/test_fetchers_hipaa.py
git commit -m "$(cat <<'EOF'
test(hipaa): XML parser test coverage (Phase 2 carry)

Phase 2 review flagged the HIPAA fetcher's live fetch() (XML path) as
untested — only fetch_from_text (JSON, deprecated upstream) had tests.
Add a trimmed eCFR XML fixture and three tests covering paragraph-id
extraction, italic-header titles, and within-section deduplication.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 10: Phase 4 carry-forward — kubectl-kustomize CI step + Ingress security headers + NetworkPolicy

**Files:**
- Modify: `.github/workflows/validate.yml`
- Modify: `deploy/apps/policy-docs/ingress.yaml`
- Create: `deploy/apps/policy-docs/network-policy.yaml`
- Modify: `deploy/apps/policy-docs/kustomization.yaml`

- [ ] **Step 1: Add kubectl + kustomize step to CI**

In `.github/workflows/validate.yml`, after the `Validate deployment manifests` step, append:

```yaml
      - name: Set up kubectl
        uses: azure/setup-kubectl@v4
      - name: kubectl kustomize (apps)
        run: kubectl kustomize deploy/apps/policy-docs/ > /dev/null
      - name: kubectl kustomize (flux)
        run: kubectl kustomize deploy/flux/image-automation/ > /dev/null
```

The `> /dev/null` discards the rendered output (we don't need to inspect it; we just need the build to succeed, which means kustomize parsed every manifest reference).

- [ ] **Step 2: Add security headers to the Ingress**

Read `deploy/apps/policy-docs/ingress.yaml`. In the `metadata.annotations` block, after `auth-snippet:`, append:

```yaml
    # Defensive headers for the rendered site. frame-ancestors permits the
    # GGenomics SharePoint and Teams hosts so the policy site can be
    # iframe-embedded there; everywhere else is denied.
    nginx.ingress.kubernetes.io/configuration-snippet: |
      more_set_headers "X-Content-Type-Options: nosniff";
      more_set_headers "Referrer-Policy: strict-origin-when-cross-origin";
      more_set_headers "Content-Security-Policy: frame-ancestors 'self' https://*.sharepoint.com https://*.teams.microsoft.com https://teams.microsoft.com";
```

CSP `frame-ancestors` supersedes `X-Frame-Options` for embedding control; combining both is harmless and survives older clients.

- [ ] **Step 3: Add a NetworkPolicy**

`deploy/apps/policy-docs/network-policy.yaml`:

```yaml
# Default-deny ingress; explicit allow from ingress-nginx.
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: deny-all-ingress
  namespace: policy-docs
  labels:
    app.kubernetes.io/part-of: ggi-policy
spec:
  podSelector: {}
  policyTypes:
    - Ingress
---
# Allow ingress-nginx → policy-docs nginx + oauth2-proxy.
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-ingress-nginx
  namespace: policy-docs
  labels:
    app.kubernetes.io/part-of: ggi-policy
spec:
  podSelector:
    matchExpressions:
      - key: app.kubernetes.io/name
        operator: In
        values: [policy-docs, oauth2-proxy]
  policyTypes:
    - Ingress
  ingress:
    - from:
        - namespaceSelector:
            matchLabels:
              # TODO(operator): confirm the ingress-nginx namespace label.
              # Most installations label `ingress-nginx` with
              # `kubernetes.io/metadata.name: ingress-nginx`.
              kubernetes.io/metadata.name: ingress-nginx
      ports:
        - protocol: TCP
          port: 8080   # policy-docs nginx
        - protocol: TCP
          port: 4180   # oauth2-proxy
```

- [ ] **Step 4: Add the NetworkPolicy to kustomization**

Read `deploy/apps/policy-docs/kustomization.yaml`. In the `resources:` list, add `- network-policy.yaml` after `- ingress.yaml`.

- [ ] **Step 5: Verify everything builds**

```bash
uv run python -c "
import yaml, glob
for f in sorted(glob.glob('deploy/apps/policy-docs/*.yaml')):
    list(yaml.safe_load_all(open(f)))
    print(f, 'OK')
"
kubectl kustomize deploy/apps/policy-docs/ | grep -cE "^kind: "
```

Expected: every YAML parses; the kustomize render now produces 12 kinds (10 prior + 2 NetworkPolicies).

- [ ] **Step 6: Run full suite**

```bash
uv run pytest -q
uv run ggi-policy validate
uv run ggi-policy build-crosswalks --check
uv run ggi-policy validate-deploy
```

Expected: all green.

- [ ] **Step 7: Commit**

```bash
git add .github/workflows/validate.yml \
        deploy/apps/policy-docs/ingress.yaml \
        deploy/apps/policy-docs/network-policy.yaml \
        deploy/apps/policy-docs/kustomization.yaml
git commit -m "$(cat <<'EOF'
chore(deploy): Phase 4 carry-forward hardening

Three items from the Phase 4 final review:

1. CI: `kubectl kustomize` runs after the structural validator. Catches
   manifest issues the YAML walker can't (dangling resources references,
   bad patches, unresolvable images).

2. Ingress: defensive HTTP response headers via configuration-snippet —
   X-Content-Type-Options, Referrer-Policy, and CSP frame-ancestors that
   permits iframe embedding from GGenomics SharePoint and Teams hosts
   only.

3. NetworkPolicy: default-deny-ingress + explicit allow from the
   ingress-nginx namespace to ports 8080 (policy-docs) and 4180
   (oauth2-proxy). TODO(operator) flagged for the ingress-nginx
   namespace label.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Self-review

**Spec coverage:** every Phase-5-relevant section of the design has a task implementing it.

| Spec section | Plan task |
|---|---|
| §7.4 Review cadence (`check-reviews` GH Action) | Tasks 1, 3, 6 |
| §7.5 Exception expiration (Teams notifications) | Tasks 1, 5, 6 |
| §7.6 Change workflow PR template | Task 7 |
| §8.2 `notify-effective` CLI subcommand | Tasks 1, 4, 6 |
| §8.2 `check-reviews` CLI subcommand | Tasks 1, 3, 6 |
| §8.2 `check-exceptions` CLI subcommand | Tasks 1, 5, 6 |
| Phase 2 carry: HIPAA XML test coverage | Task 9 |
| Phase 2 carry: deterministic catalog sort | Task 8 |
| Phase 4 carry: kubectl kustomize CI step | Task 10 |
| Phase 4 carry: ingress security headers | Task 10 |
| Phase 4 carry: NetworkPolicy | Task 10 |

Phase 4 carry items NOT included (deferred to Phase 5+ cleanup or beyond):
- oauth2-proxy image digest pinning (low priority; nightly re-pull is fine for an internal site)
- Renovate/Dependabot config (operator's call; can be added after Phase 6)
- Validator coverage gaps (deployment-with-no-containers test, subdir-walking test) — nice-to-have

**Placeholder scan:** no `TBD`/`TODO`/`FIXME` placeholders. Two `TODO(operator)` markers added (NetworkPolicy ingress-nginx namespace label, plus the existing five from Phase 4 are unchanged).

**Type / signature consistency:**
- `lifecycle.overdue_reviews(policies_root: Path, *, today: date) -> list[dict]` — Task 1, used in Task 3.
- `lifecycle.effective_today(policies_root: Path, *, today: date) -> list[dict]` — Task 1, used in Task 4.
- `lifecycle.expiring_exceptions(exceptions_root: Path, *, today: date) -> list[dict]` — Task 1, used in Task 5.
- `teams.post_card(webhook_url: str, *, title: str, body: str, action_url: str | None = None) -> None` — Task 2, used in Tasks 4 + 5.
- All three CLI subcommands accept `--today`, `--dry-run`, `--repo-root`. `notify-effective` and `check-exceptions` additionally accept `--webhook-url` (envvar `TEAMS_POLICY_WEBHOOK`).

**Ambiguity:**
- `check-reviews` currently emits TSV output that a shell `while read` parses. If a policy `id` ever contains a tab character, the parsing would break — but the schema regex (`^POL-[A-Z]+-[A-Z0-9-]+$`) prohibits tabs, so this is safe by construction.
- `notify-effective`'s "skipped: TEAMS_POLICY_WEBHOOK not set" exits 0 (not an error). This is deliberate: until the operator creates the webhook, the workflow should be green not red. Once `TEAMS_POLICY_WEBHOOK` is set, the bot delivers cards.
- The `review-due` GitHub label must be created once by the operator. The plan documents this in Task 6 Step 1 commentary; the README should be updated by Phase 6 (which fleshes out CLAUDE.md / README.md anyway) to include this one-time setup.

**Carry-forward to Phase 6:**
- README.md and CLAUDE.md / AGENTS.md need substantial fleshing out (Phase 6's primary deliverable).
- The `review-due` label setup needs to be in the README.
- `POL-META-DOC-FRAMEWORK` and `POL-META-AI-AGENT-CONTRACT` policies — first real users of the framework, eat the dog food.
- `glossary/terms.md` populated with IAM controlled vocabulary in time for the first non-meta policy (`POL-IAM-GROUP-NAMING`).
