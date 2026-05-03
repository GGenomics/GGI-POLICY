from datetime import date

from ggi_policy.fetchers._models import Control, FrameworkData, Metadata


def test_control_dataclass_round_trip() -> None:
    c = Control(id="PR.AC-01", title="Identities issued", description="long form")
    assert c.id == "PR.AC-01"
    assert c.description == "long form"


def test_control_description_optional() -> None:
    c = Control(id="X", title="Y")
    assert c.description == ""


def test_framework_data_to_json_round_trip() -> None:
    meta = Metadata(
        version="2.0",
        fetched_at=date(2026, 5, 2),
        source_url="https://example.com/x.json",
        fetcher="nist_csf",
    )
    fd = FrameworkData(metadata=meta, controls=[Control(id="A", title="B")])
    payload = fd.to_json()
    assert payload["metadata"]["version"] == "2.0"
    assert payload["metadata"]["fetched_at"] == "2026-05-02"
    assert payload["controls"] == [{"id": "A", "title": "B"}]


def test_framework_data_to_json_includes_description_when_set() -> None:
    meta = Metadata(version="2.0", fetched_at=date(2026, 5, 2),
                    source_url="https://x", fetcher="t")
    fd = FrameworkData(metadata=meta, controls=[Control(id="A", title="B", description="long")])
    payload = fd.to_json()
    assert payload["controls"][0]["description"] == "long"
