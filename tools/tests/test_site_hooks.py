"""Tests for the docs/_hooks/policy_page.py MkDocs hook.

The hook lives outside the Python package layout (under `docs/_hooks/`) so
it has to be imported via importlib rather than `from ggi_policy import ...`.
"""

import importlib.util
from pathlib import Path

_HOOK_PATH = Path(__file__).resolve().parent.parent.parent / "docs" / "_hooks" / "policy_page.py"
_spec = importlib.util.spec_from_file_location("policy_page", _HOOK_PATH)
policy_page = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(policy_page)


def test_policy_page_renders_metadata_strip_and_framework_table(fixtures_dir: Path) -> None:
    src = (fixtures_dir / "site/policy-input.md").read_text()
    expected = (fixtures_dir / "site/policy-expected.md").read_text()
    out = policy_page.transform(src, None, page_path="policies/identity-and-access/group-naming.md")
    assert out.strip() == expected.strip()


def test_non_policy_page_passes_through() -> None:
    plain = "# Plain page\n\nNo frontmatter here.\n"
    out = policy_page.transform(plain, None, page_path="some/page.md")
    assert out == plain


def test_page_with_frontmatter_but_no_pol_id_does_not_get_policy_treatment() -> None:
    src = "---\ntitle: Crosswalks\n---\n\n# Crosswalks index\n"
    out = policy_page.transform(src, None, page_path="crosswalks/index.md")
    # No metadata strip and no framework table; the body remains.
    assert "!!! info" not in out
    assert "Framework alignment" not in out
    assert "# Crosswalks index" in out


def test_relative_crosswalk_path_depth_for_top_level_meta_policy() -> None:
    src = (
        "---\n"
        "id: POL-META-DOC-FRAMEWORK\n"
        "title: t\nsummary: s\ndomain: META\nstatus: effective\nversion: 1.0.0\n"
        "effective_date: 2026-01-01\nlast_reviewed: 2026-01-01\nreview_cycle: annual\n"
        "owner: x\napprovers: [x]\napplies_to: [x]\nsupersedes: []\nrelated: []\n"
        "frameworks:\n  nist_csf: [GV.OC-01]\n"
        "external_references: []\n"
        "---\n# Body\n"
    )
    out = policy_page.transform(src, None, page_path="policies/meta/doc-framework.md")
    assert "(../../crosswalks/nist-csf.md)" in out


def test_skip_frameworks_with_empty_lists() -> None:
    src = (
        "---\n"
        "id: POL-IAM-X\n"
        "title: t\nsummary: s\ndomain: IAM\nstatus: draft\nversion: 0.1.0\n"
        "effective_date: 2026-01-01\nlast_reviewed: 2026-01-01\nreview_cycle: annual\n"
        "owner: x\napprovers: [x]\napplies_to: [x]\nsupersedes: []\nrelated: []\n"
        "frameworks:\n  nist_csf: [PR.AC-01]\n  cis: []\n"
        "external_references: []\n"
        "---\n# Body\n"
    )
    out = policy_page.transform(src, None, page_path="policies/identity-and-access/x.md")
    assert "NIST CSF 2.0" in out
    assert "CIS Controls v8" not in out
