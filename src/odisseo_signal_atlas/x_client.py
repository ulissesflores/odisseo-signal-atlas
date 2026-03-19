"""X API client for repository discovery."""

from __future__ import annotations

from datetime import datetime

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from .exceptions import RemoteAPIError
from .models import TweetHit


class XClient:
    """Thin client around the X recent search API."""

    def __init__(self, bearer_token: str, endpoint: str, timeout: float = 30.0) -> None:
        self.endpoint = endpoint
        self.http = httpx.Client(
            timeout=timeout,
            headers={
                "Authorization": f"Bearer {bearer_token}",
                "User-Agent": "odisseo-signal-atlas/0.1",
            },
        )

    def close(self) -> None:
        """Close the underlying HTTP client."""

        self.http.close()

    @retry(
        stop=stop_after_attempt(4),
        wait=wait_exponential(multiplier=1, min=1, max=20),
        retry=retry_if_exception_type(httpx.HTTPError),
        reraise=True,
    )
    def _request(self, params: dict[str, str | int]) -> dict:
        response = self.http.get(self.endpoint, params=params)
        if response.status_code in {401, 403}:
            raise RemoteAPIError(f"X API authentication failed: {response.text[:300]}")
        response.raise_for_status()
        return response.json()

    def search(
        self,
        query: str,
        max_results_per_page: int = 100,
        max_pages: int = 5,
    ) -> list[TweetHit]:
        """Search X and normalize returned tweets into ``TweetHit`` objects."""

        collected: list[TweetHit] = []
        next_token: str | None = None

        for _ in range(max_pages):
            params: dict[str, str | int] = {
                "query": query,
                "max_results": min(max_results_per_page, 100),
                "tweet.fields": "created_at,lang,public_metrics,entities",
                "expansions": "author_id",
                "user.fields": "username",
            }
            if next_token:
                params["next_token"] = next_token

            payload = self._request(params)
            includes = payload.get("includes", {})
            users = {user["id"]: user for user in includes.get("users", [])}

            for tweet in payload.get("data", []):
                entities = tweet.get("entities", {})
                urls = [
                    item.get("expanded_url") or item.get("url")
                    for item in entities.get("urls", [])
                ]
                author = users.get(tweet.get("author_id"), {})
                collected.append(
                    TweetHit(
                        tweet_id=tweet["id"],
                        text=tweet.get("text", ""),
                        lang=tweet.get("lang"),
                        created_at=_parse_datetime(tweet.get("created_at")),
                        public_metrics=tweet.get("public_metrics", {}),
                        author_username=author.get("username"),
                        expanded_urls=[url for url in urls if url],
                        matched_query=query,
                    )
                )

            next_token = payload.get("meta", {}).get("next_token")
            if not next_token:
                break

        return collected


def _parse_datetime(value: str | None) -> datetime | None:
    """Parse ISO datetimes returned by remote APIs."""

    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))
