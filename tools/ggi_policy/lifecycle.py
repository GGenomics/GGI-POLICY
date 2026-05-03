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
