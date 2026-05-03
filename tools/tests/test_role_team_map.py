from ggi_policy import role_team_map


def test_load_and_resolve(fixtures_dir, tmp_path):  # type: ignore[no-untyped-def]
    f = tmp_path / "role-team-mapping.yaml"
    f.write_text("roles:\n  CISO: \"@ggenomics/ciso\"\n  IT Director: \"@ggenomics/it-director\"\n")
    mapping = role_team_map.load(f)
    assert mapping["CISO"] == "@ggenomics/ciso"
    assert mapping["IT Director"] == "@ggenomics/it-director"


def test_resolve_unknown_returns_none(tmp_path):  # type: ignore[no-untyped-def]
    f = tmp_path / "role-team-mapping.yaml"
    f.write_text("roles:\n  CISO: \"@ggenomics/ciso\"\n")
    mapping = role_team_map.load(f)
    assert mapping.get("Unknown") is None
