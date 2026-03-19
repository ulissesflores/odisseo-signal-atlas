from __future__ import annotations

from datetime import UTC, datetime

import httpx
import pytest

from odisseo_signal_atlas.exceptions import RateLimitError, RemoteAPIError
from odisseo_signal_atlas.x_client import XClient


class DummyResponse:
    def __init__(
        self,
        status_code: int,
        payload: dict,
        text: str = "",
        headers: dict[str, str] | None = None,
    ) -> None:
        self.status_code = status_code
        self._payload = payload
        self.text = text or str(payload)
        self.headers = headers or {}

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            request = httpx.Request("GET", "https://api.x.com/2/tweets/search/recent")
            response = httpx.Response(self.status_code, request=request)
            raise httpx.HTTPStatusError("boom", request=request, response=response)

    def json(self) -> dict:
        return self._payload


def test_request_raises_on_auth_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    client = XClient("token", "https://api.x.com/2/tweets/search/recent")
    monkeypatch.setattr(
        client.http,
        "get",
        lambda url, params: DummyResponse(401, {"error": "denied"}, text="denied"),
    )

    with pytest.raises(RemoteAPIError, match="authentication failed"):
        client._request({"query": "test"})

    client.close()


def test_search_parses_tweets_and_paginates(monkeypatch: pytest.MonkeyPatch) -> None:
    payloads = [
        {
            "data": [
                {
                    "id": "1",
                    "text": "look https://github.com/acme/project",
                    "lang": "en",
                    "created_at": "2026-03-19T00:00:00Z",
                    "author_id": "u1",
                    "public_metrics": {"like_count": 5},
                    "entities": {
                        "urls": [
                            {
                                "expanded_url": "https://github.com/acme/project",
                                "url": "https://t.co/1",
                            }
                        ]
                    },
                }
            ],
            "includes": {"users": [{"id": "u1", "username": "alice"}]},
            "meta": {"next_token": "next"},
        },
        {
            "data": [
                {
                    "id": "2",
                    "text": "look https://github.com/acme/other",
                    "lang": "pt",
                    "created_at": "2026-03-19T01:00:00Z",
                    "author_id": "u2",
                    "public_metrics": {"like_count": 2},
                    "entities": {"urls": []},
                }
            ],
            "includes": {"users": [{"id": "u2", "username": "bruno"}]},
            "meta": {},
        },
    ]

    client = XClient("token", "https://api.x.com/2/tweets/search/recent")
    monkeypatch.setattr(client, "_request", lambda params: payloads.pop(0))

    tweets = client.search("query", max_results_per_page=10, max_pages=2)

    assert len(tweets) == 2
    assert tweets[0].author_username == "alice"
    assert tweets[0].expanded_urls == ["https://github.com/acme/project"]
    assert tweets[0].matched_query == "query"
    assert tweets[1].author_username == "bruno"
    assert tweets[1].created_at is not None
    client.close()


def test_search_passes_time_window_to_request(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: list[dict[str, str | int]] = []
    client = XClient("token", "https://api.x.com/2/tweets/search/recent")

    def fake_request(params: dict[str, str | int]) -> dict:
        captured.append(params)
        return {"data": [], "meta": {}}

    monkeypatch.setattr(client, "_request", fake_request)

    client.search(
        "query",
        max_results_per_page=10,
        max_pages=1,
        start_time=datetime(2026, 3, 18, 0, 0, tzinfo=UTC),
        end_time=datetime(2026, 3, 18, 12, 0, tzinfo=UTC),
    )

    assert captured
    assert captured[0]["max_results"] == 10
    assert "start_time" in captured[0]
    assert "end_time" in captured[0]
    client.close()


def test_request_raises_structured_rate_limit_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = XClient("token", "https://api.x.com/2/tweets/search/recent")
    monkeypatch.setattr(
        client.http,
        "get",
        lambda url, params: DummyResponse(
            429,
            {"error": "too_many_requests"},
            headers={"retry-after": "7"},
        ),
    )

    with pytest.raises(RateLimitError) as exc:
        client._request({"query": "test"})

    assert exc.value.retry_after_seconds == 7
    client.close()
