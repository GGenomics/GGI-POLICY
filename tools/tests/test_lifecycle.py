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
