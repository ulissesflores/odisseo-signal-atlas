from __future__ import annotations

from datetime import UTC, datetime

import httpx
import pytest

from odisseo_signal_atlas.exceptions import RemoteAPIError
from odisseo_signal_atlas.github_client import GitHubClient
from odisseo_signal_atlas.models import TweetHit


class DummyResponse:
    def __init__(self, status_code: int, payload: dict, text: str = "") -> None:
        self.status_code = status_code
        self._payload = payload
        self.text = text or str(payload)

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            request = httpx.Request("GET", "https://api.github.com/repos/acme/project")
            response = httpx.Response(self.status_code, request=request)
            raise httpx.HTTPStatusError("boom", request=request, response=response)

    def json(self) -> dict:
        return self._payload


def test_fetch_repo_returns_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    client = GitHubClient(token=None)
    monkeypatch.setattr(
        client.http,
        "get",
        lambda url: DummyResponse(200, {"html_url": "https://github.com/acme/project"}),
    )

    payload = client.fetch_repo("acme", "project")

    assert payload["html_url"] == "https://github.com/acme/project"
    client.close()


def test_github_client_enables_redirect_following() -> None:
    client = GitHubClient(token=None)

    assert client.http.follow_redirects is True
    client.close()


def test_fetch_repo_raises_on_missing_repository(monkeypatch: pytest.MonkeyPatch) -> None:
    client = GitHubClient(token=None)
    monkeypatch.setattr(
        client.http,
        "get",
        lambda url: DummyResponse(404, {"message": "Not Found"}, text="missing"),
    )

    with pytest.raises(RemoteAPIError, match="GitHub repository not found"):
        client.fetch_repo("acme", "missing")

    client.close()


def test_build_record_maps_enriched_fields(monkeypatch: pytest.MonkeyPatch) -> None:
    client = GitHubClient(token=None)
    monkeypatch.setattr(
        client,
        "fetch_repo",
        lambda owner, repo: {
            "html_url": "https://github.com/acme/project",
            "stargazers_count": 33,
            "language": "Python",
            "description": "Discovery engine",
            "topics": ["mcp", "memory"],
            "updated_at": "2026-03-19T00:00:00Z",
            "pushed_at": "2026-03-18T00:00:00Z",
        },
    )

    record = client.build_record(
        repo_slug="acme/project",
        source_languages=["pt", "en"],
        matched_topics=["memory"],
        source_tweets=[
            TweetHit(
                tweet_id="1",
                text="repo",
                lang="en",
                created_at=datetime.now(UTC),
                public_metrics={},
            )
        ],
    )

    assert record.repo_slug == "acme/project"
    assert record.stars == 33
    assert record.primary_language == "Python"
    assert record.source_languages == ["en", "pt"]
    assert record.topics == ["mcp", "memory"]
    client.close()
