"""Thin wrapper around httpx so fetchers don't all carry duplicate timeout config."""

import httpx

DEFAULT_TIMEOUT = httpx.Timeout(connect=10.0, read=30.0, write=10.0, pool=10.0)


def fetch_text(url: str) -> str:
    """GET `url`, raise on non-2xx, return body as text."""
    resp = httpx.get(url, follow_redirects=True, timeout=DEFAULT_TIMEOUT)
    resp.raise_for_status()
    return resp.text


def fetch_json(url: str) -> dict:
    """GET `url`, raise on non-2xx, return body parsed as JSON."""
    resp = httpx.get(url, follow_redirects=True, timeout=DEFAULT_TIMEOUT)
    resp.raise_for_status()
    return resp.json()
