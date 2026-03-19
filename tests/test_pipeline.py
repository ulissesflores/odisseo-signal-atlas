import json
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

import pytest

from odisseo_signal_atlas.config import Settings
from odisseo_signal_atlas.github_client import GitHubClient
from odisseo_signal_atlas.models import QuerySpec, RepoRecord, SearchLanguage, TweetHit
from odisseo_signal_atlas.pipeline import OdisseoSignalAtlasPipeline
from odisseo_signal_atlas.x_client import XClient


class DummyXClient:
    def search(
        self,
        query: str,
        max_results_per_page: int = 100,
        max_pages: int = 5,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> list[TweetHit]:
        if "memory" in query:
            return [
                TweetHit(
                    tweet_id="1",
                    text="check https://github.com/acme/odisseo-memory",
                    lang="en",
                    created_at=datetime.now(UTC),
                    public_metrics={},
                    expanded_urls=["https://github.com/acme/odisseo-memory"],
                )
            ]
        return [
            TweetHit(
                tweet_id="2",
                text="check https://github.com/anthropics/skills",
                lang="en",
                created_at=datetime.now(UTC),
                public_metrics={},
                expanded_urls=["https://github.com/anthropics/skills"],
            )
        ]

    def close(self) -> None:
        return None


class DummyGitHubClient:
    def build_record(
        self,
        repo_slug: str,
        source_languages: list[str],
        matched_topics: list[str],
        source_tweets: list[TweetHit],
    ) -> RepoRecord:
        return RepoRecord(
            repo_url=f"https://github.com/{repo_slug}",
            repo_slug=repo_slug,
            stars=120,
            primary_language="Python",
            description="Memory-first MCP stack for frontier repo discovery.",
            topics=["memory", "mcp"],
            html_url=f"https://github.com/{repo_slug}",
            updated_at=datetime.now(UTC),
            pushed_at=datetime.now(UTC),
            source_languages=source_languages,
            matched_topics=matched_topics,
            source_tweets=source_tweets,
        )

    def close(self) -> None:
        return None


def test_pipeline_runs_end_to_end_with_mocks(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    language = SearchLanguage("en", "English", ("Claude Code",), ("memory",))
    queries = [
        QuerySpec(
            language=language,
            topic_label="memory",
            query="memory query",
            window_label="20260318T0000Z-20260318T1200Z",
            start_time=datetime(2026, 3, 18, 0, 0, tzinfo=UTC),
            end_time=datetime(2026, 3, 18, 12, 0, tzinfo=UTC),
        ),
        QuerySpec(
            language=language,
            topic_label="agents",
            query="agents query",
            window_label="20260318T1200Z-20260319T0000Z",
            start_time=datetime(2026, 3, 18, 12, 0, tzinfo=UTC),
            end_time=datetime(2026, 3, 19, 0, 0, tzinfo=UTC),
            is_live_window=True,
        ),
    ]

    settings = Settings(
        app_name="Odisseo Signal Atlas",
        environment="test",
        project_root=tmp_path,
        cache_dir=tmp_path / "cache",
        output_dir=tmp_path / "output",
        output_file=tmp_path / "output/report.md",
        site_url="https://ulissesflores.com",
        x_bearer_token="token",
        github_token=None,
        x_search_endpoint="https://api.x.com/2/tweets/search/recent",
        x_max_results_per_page=10,
        x_pages_per_query=1,
        x_lookback_days=1,
        x_window_hours=12,
        x_refresh_live_window=True,
        target_repos=10,
        query_history_file=tmp_path / "cache/query_history.json",
        query_history_retention_days=30,
        excluded_repos={"anthropics/skills"},
        search_languages=[language],
    )

    monkeypatch.setattr(
        "odisseo_signal_atlas.pipeline.build_queries",
        lambda *_args, **_kwargs: queries,
    )
    pipeline = OdisseoSignalAtlasPipeline(settings)
    pipeline.x_client = cast(XClient, DummyXClient())
    pipeline.github_client = cast(GitHubClient, DummyGitHubClient())

    report = pipeline.run(target_repos=10)

    assert report.total_planned_queries == 2
    assert report.total_queries == 2
    assert report.total_skipped_queries == 0
    assert report.total_tweets == 2
    assert report.total_candidates == 2
    assert report.total_ranked == 1
    assert settings.output_file.exists()


def test_pipeline_skips_historical_query_windows_from_cache(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    language = SearchLanguage("en", "English", ("Claude Code",), ("memory",))
    archived_query = QuerySpec(
        language=language,
        topic_label="memory",
        query='("Claude Code") github.com lang:en',
        window_label="20260318T0000Z-20260318T1200Z",
        start_time=datetime(2026, 3, 18, 0, 0, tzinfo=UTC),
        end_time=datetime(2026, 3, 18, 12, 0, tzinfo=UTC),
        is_live_window=False,
    )
    live_query = QuerySpec(
        language=language,
        topic_label="memory",
        query='("Claude Code") github.com lang:en',
        window_label="20260318T1200Z-20260319T0000Z",
        start_time=datetime(2026, 3, 18, 12, 0, tzinfo=UTC),
        end_time=datetime(2026, 3, 19, 0, 0, tzinfo=UTC),
        is_live_window=True,
    )

    settings = Settings(
        app_name="Odisseo Signal Atlas",
        environment="test",
        project_root=tmp_path,
        cache_dir=tmp_path / "cache",
        output_dir=tmp_path / "output",
        output_file=tmp_path / "output/report.md",
        site_url="https://ulissesflores.com",
        x_bearer_token="token",
        github_token=None,
        x_search_endpoint="https://api.x.com/2/tweets/search/recent",
        x_max_results_per_page=10,
        x_pages_per_query=1,
        x_lookback_days=1,
        x_window_hours=12,
        x_refresh_live_window=True,
        target_repos=10,
        query_history_file=tmp_path / "cache/query_history.json",
        query_history_retention_days=30,
        excluded_repos=set(),
        search_languages=[language],
    )
    settings.query_history_file.parent.mkdir(parents=True, exist_ok=True)
    settings.query_history_file.write_text(
        json.dumps(
            {
                archived_query.signature: {
                    "executed_at": "2026-03-19T00:00:00+00:00",
                }
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        "odisseo_signal_atlas.pipeline.build_queries",
        lambda *_args, **_kwargs: [archived_query, live_query],
    )
    pipeline = OdisseoSignalAtlasPipeline(settings)
    pipeline.x_client = cast(XClient, DummyXClient())
    pipeline.github_client = cast(GitHubClient, DummyGitHubClient())

    report = pipeline.run(target_repos=10)

    assert report.total_planned_queries == 2
    assert report.total_queries == 1
    assert report.total_skipped_queries == 1
