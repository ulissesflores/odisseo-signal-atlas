"""GitHub API client for repository enrichment."""

from __future__ import annotations

from datetime import datetime

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from .exceptions import RemoteAPIError
from .models import RepoRecord, TweetHit


class GitHubClient:
    """Thin client around the GitHub repositories API."""

    def __init__(self, token: str | None = None, timeout: float = 30.0) -> None:
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "odisseo-signal-atlas/0.1",
        }
        if token:
            headers["Authorization"] = f"Bearer {token}"
        self.http = httpx.Client(timeout=timeout, headers=headers)

    def close(self) -> None:
        """Close the underlying HTTP client."""

        self.http.close()

    @retry(
        stop=stop_after_attempt(4),
        wait=wait_exponential(multiplier=1, min=1, max=20),
        retry=retry_if_exception_type(httpx.HTTPError),
        reraise=True,
    )
    def fetch_repo(self, owner: str, repo: str) -> dict:
        """Fetch a GitHub repository payload by owner and repo name."""

        response = self.http.get(f"https://api.github.com/repos/{owner}/{repo}")
        if response.status_code == 404:
            raise RemoteAPIError(f"GitHub repository not found: {owner}/{repo}")
        response.raise_for_status()
        return response.json()

    def build_record(
        self,
        repo_slug: str,
        source_languages: list[str],
        matched_topics: list[str],
        source_tweets: list[TweetHit],
    ) -> RepoRecord:
        """Build an enriched repository record from GitHub metadata."""

        owner, repo = repo_slug.split("/", 1)
        payload = self.fetch_repo(owner, repo)
        return RepoRecord(
            repo_url=payload["html_url"],
            repo_slug=repo_slug,
            stars=int(payload.get("stargazers_count", 0)),
            primary_language=payload.get("language"),
            description=payload.get("description") or "",
            topics=list(payload.get("topics", [])),
            html_url=payload["html_url"],
            updated_at=_parse_datetime(payload.get("updated_at")),
            pushed_at=_parse_datetime(payload.get("pushed_at")),
            source_languages=sorted(source_languages),
            matched_topics=sorted(matched_topics),
            source_tweets=list(source_tweets),
        )


def _parse_datetime(value: str | None) -> datetime | None:
    """Parse ISO datetimes returned by remote APIs."""

    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))

