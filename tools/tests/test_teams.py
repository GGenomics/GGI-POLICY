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
