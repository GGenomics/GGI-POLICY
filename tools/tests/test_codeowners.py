from pathlib import Path

from ggi_policy import codeowners


def test_parse_simple(tmp_path: Path) -> None:
    f = tmp_path / "CODEOWNERS"
    f.write_text(
        "# comment\n"
        "/policies/data/   @ggenomics/ciso @ggenomics/data-steward\n"
        "/exceptions/      @ggenomics/ciso\n"
    )
    rules = codeowners.parse(f)
    assert rules == [
        ("/policies/data/", ["@ggenomics/ciso", "@ggenomics/data-steward"]),
        ("/exceptions/",    ["@ggenomics/ciso"]),
    ]


def test_owners_for_path_picks_longest_prefix(tmp_path: Path) -> None:
    f = tmp_path / "CODEOWNERS"
    f.write_text(
        "/policies/                    @ggenomics/everyone\n"
        "/policies/identity-and-access/ @ggenomics/ciso @ggenomics/it-director\n"
    )
    rules = codeowners.parse(f)
    owners = codeowners.owners_for("policies/identity-and-access/group-naming.md", rules)
    assert owners == ["@ggenomics/ciso", "@ggenomics/it-director"]


def test_owners_for_does_not_match_partial_path_segment(tmp_path: Path) -> None:
    """A pattern without a trailing slash must not match a path that merely shares a prefix
    within the same segment (e.g., `/policies/data` should not match `/policies/data-governance/`).
    """
    f = tmp_path / "CODEOWNERS"
    f.write_text("/policies/data    @ggenomics/data-team\n")  # NOTE: no trailing slash
    rules = codeowners.parse(f)
    assert codeowners.owners_for("policies/data-governance/foo.md", rules) == []
    # But it must still match the exact path or a child path
    assert codeowners.owners_for("policies/data", rules) == ["@ggenomics/data-team"]
    assert codeowners.owners_for("policies/data/foo.md", rules) == ["@ggenomics/data-team"]
