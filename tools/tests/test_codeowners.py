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
