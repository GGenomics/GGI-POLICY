from unittest.mock import MagicMock, patch

import pytest

from ggi_policy.fetchers import _http


def test_fetch_json_parses_a_response() -> None:
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"a": 1}
    mock_resp.raise_for_status = MagicMock()
    with patch("ggi_policy.fetchers._http.httpx.get", return_value=mock_resp) as get:
        out = _http.fetch_json("https://example.com/x")
    assert out == {"a": 1}
    get.assert_called_once()
    kwargs = get.call_args.kwargs
    assert kwargs.get("timeout") == _http.DEFAULT_TIMEOUT


def test_fetch_text_parses_a_response() -> None:
    mock_resp = MagicMock()
    mock_resp.text = "hello"
    mock_resp.raise_for_status = MagicMock()
    with patch("ggi_policy.fetchers._http.httpx.get", return_value=mock_resp):
        assert _http.fetch_text("https://example.com/x") == "hello"


def test_fetch_json_raises_on_http_error() -> None:
    import httpx
    mock_resp = MagicMock()
    mock_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
        "404", request=MagicMock(), response=MagicMock(status_code=404)
    )
    with patch("ggi_policy.fetchers._http.httpx.get", return_value=mock_resp):
        with pytest.raises(httpx.HTTPStatusError):
            _http.fetch_json("https://example.com/missing")
