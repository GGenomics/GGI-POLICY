"""Microsoft Teams Adaptive Card poster for the lifecycle bots."""

import httpx


_DEFAULT_TIMEOUT = httpx.Timeout(connect=5.0, read=15.0, write=5.0, pool=5.0)


def post_card(webhook_url: str, *, title: str, body: str, action_url: str | None = None) -> None:
    """Post an Adaptive Card with a title, body, and optional 'Open' action button.

    Raises httpx.HTTPStatusError on non-2xx responses.
    """
    card_body: list[dict] = [
        {
            "type": "TextBlock",
            "size": "Medium",
            "weight": "Bolder",
            "wrap": True,
            "text": title,
        },
        {
            "type": "TextBlock",
            "wrap": True,
            "text": body,
        },
    ]
    actions: list[dict] = []
    if action_url:
        actions.append({"type": "Action.OpenUrl", "title": "Open", "url": action_url})

    payload = {
        "type": "message",
        "attachments": [
            {
                "contentType": "application/vnd.microsoft.card.adaptive",
                "content": {
                    "type":    "AdaptiveCard",
                    "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                    "version": "1.5",
                    "body":    card_body,
                    "actions": actions,
                },
            }
        ],
    }
    resp = httpx.post(webhook_url, json=payload, timeout=_DEFAULT_TIMEOUT)
    resp.raise_for_status()
