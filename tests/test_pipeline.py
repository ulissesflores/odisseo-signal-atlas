import json
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

import pytest

from odisseo_signal_atlas.config import Settings
from odisseo_signal_atlas.exceptions import RateLimitError
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
        x_min_request_interval_seconds=0.0,
        x_lookback_days=1,
        x_max_backfill_days=1,
        x_window_hours=12,
        x_refresh_live_window=True,
        x_rate_limit_default_wait_seconds=60,
        x_rate_limit_max_wait_seconds=900,
        target_repos=10,
        candidate_target_multiplier=1.15,
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
    assert report.days_scanned == 1
    assert report.target_reached is False
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
        x_min_request_interval_seconds=0.0,
        x_lookback_days=1,
        x_max_backfill_days=1,
        x_window_hours=12,
        x_refresh_live_window=True,
        x_rate_limit_default_wait_seconds=60,
        x_rate_limit_max_wait_seconds=900,
        target_repos=10,
        candidate_target_multiplier=1.15,
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


def test_pipeline_retries_after_rate_limit_and_persists_resume_state(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    language = SearchLanguage("en", "English", ("Claude Code",), ("memory",))
    query = QuerySpec(
        language=language,
        topic_label="memory",
        query="memory query",
        window_label="20260318T0000Z-20260318T1200Z",
        start_time=datetime(2026, 3, 18, 0, 0, tzinfo=UTC),
        end_time=datetime(2026, 3, 18, 12, 0, tzinfo=UTC),
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
        x_min_request_interval_seconds=0.0,
        x_lookback_days=1,
        x_max_backfill_days=1,
        x_window_hours=12,
        x_refresh_live_window=True,
        x_rate_limit_default_wait_seconds=5,
        x_rate_limit_max_wait_seconds=30,
        target_repos=10,
        candidate_target_multiplier=1.15,
        query_history_file=tmp_path / "cache/query_history.json",
        query_history_retention_days=30,
        excluded_repos=set(),
        search_languages=[language],
    )

    calls = {"count": 0}

    class RateLimitedXClient:
        def search(
            self,
            query: str,
            max_results_per_page: int = 100,
            max_pages: int = 5,
            start_time: datetime | None = None,
            end_time: datetime | None = None,
        ) -> list[TweetHit]:
            calls["count"] += 1
            if calls["count"] == 1:
                raise RateLimitError("rate limited", retry_after_seconds=3)
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

        def close(self) -> None:
            return None

    monkeypatch.setattr(
        "odisseo_signal_atlas.pipeline.build_queries",
        lambda *_args, **_kwargs: [query],
    )
    slept: list[int] = []
    monkeypatch.setattr("odisseo_signal_atlas.pipeline.time.sleep", slept.append)

    pipeline = OdisseoSignalAtlasPipeline(settings)
    pipeline.x_client = cast(XClient, RateLimitedXClient())
    pipeline.github_client = cast(GitHubClient, DummyGitHubClient())

    report = pipeline.run(target_repos=10)

    assert slept == [5]
    assert calls["count"] == 2
    assert report.total_queries == 1
    assert settings.query_history_file.exists()
    assert (settings.cache_dir / "candidates.json").exists()


def test_pipeline_loads_candidates_from_cache_for_resume(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    language = SearchLanguage("en", "English", ("Claude Code",), ("memory",))
    query = QuerySpec(
        language=language,
        topic_label="memory",
        query="memory query",
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
        x_min_request_interval_seconds=0.0,
        x_lookback_days=1,
        x_max_backfill_days=1,
        x_window_hours=12,
        x_refresh_live_window=True,
        x_rate_limit_default_wait_seconds=60,
        x_rate_limit_max_wait_seconds=900,
        target_repos=10,
        candidate_target_multiplier=1.15,
        query_history_file=tmp_path / "cache/query_history.json",
        query_history_retention_days=30,
        excluded_repos=set(),
        search_languages=[language],
    )
    settings.cache_dir.mkdir(parents=True, exist_ok=True)
    (settings.cache_dir / "candidates.json").write_text(
        json.dumps(
            {
                "acme/from-cache": {
                    "repo_url": "https://github.com/acme/from-cache",
                    "source_languages": ["en"],
                    "matched_topics": ["memory"],
                    "source_tweets": [
                        {
                            "tweet_id": "cached-1",
                            "text": "cached https://github.com/acme/from-cache",
                            "lang": "en",
                            "created_at": "2026-03-19T00:00:00+00:00",
                            "public_metrics": {},
                            "author_username": "alice",
                            "expanded_urls": ["https://github.com/acme/from-cache"],
                            "matched_query": "memory query",
                        }
                    ],
                }
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        "odisseo_signal_atlas.pipeline.build_queries",
        lambda *_args, **_kwargs: [query],
    )
    pipeline = OdisseoSignalAtlasPipeline(settings)
    pipeline.x_client = cast(XClient, DummyXClient())
    pipeline.github_client = cast(GitHubClient, DummyGitHubClient())

    report = pipeline.run(target_repos=10)
    ranked = json.loads((settings.cache_dir / "ranked.json").read_text(encoding="utf-8"))
    slugs = {item["repo_slug"] for item in ranked}

    assert report.total_candidates == 2
    assert {"acme/from-cache", "acme/odisseo-memory"}.issubset(slugs)


def test_pipeline_backfills_older_windows_until_candidate_target(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    language = SearchLanguage("en", "English", ("Claude Code",), ("memory",))
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
        x_min_request_interval_seconds=0.0,
        x_lookback_days=1,
        x_max_backfill_days=2,
        x_window_hours=24,
        x_refresh_live_window=True,
        x_rate_limit_default_wait_seconds=60,
        x_rate_limit_max_wait_seconds=900,
        target_repos=2,
        candidate_target_multiplier=1.0,
        query_history_file=tmp_path / "cache/query_history.json",
        query_history_retention_days=30,
        excluded_repos=set(),
        search_languages=[language],
    )

    calls: list[datetime] = []

    def fake_build_queries(
        _languages: list[SearchLanguage],
        *,
        now: datetime | None = None,
        lookback_days: int = 1,
        window_hours: int = 24,
        allow_live_window: bool = True,
    ) -> list[QuerySpec]:
        assert now is not None
        calls.append(now)
        query_id = f"{now:%Y%m%d}"
        return [
            QuerySpec(
                language=language,
                topic_label="memory",
                query=f"memory query {query_id}",
                window_label=f"{query_id}-window",
                start_time=now,
                end_time=now,
                is_live_window=allow_live_window,
            )
        ]

    class BackfillXClient:
        def search(
            self,
            query: str,
            max_results_per_page: int = 100,
            max_pages: int = 5,
            start_time: datetime | None = None,
            end_time: datetime | None = None,
        ) -> list[TweetHit]:
            slug = query.split()[-1]
            return [
                TweetHit(
                    tweet_id=slug,
                    text=f"https://github.com/acme/{slug}",
                    lang="en",
                    created_at=datetime.now(UTC),
                    public_metrics={},
                    expanded_urls=[f"https://github.com/acme/{slug}"],
                )
            ]

        def close(self) -> None:
            return None

    monkeypatch.setattr("odisseo_signal_atlas.pipeline.build_queries", fake_build_queries)
    pipeline = OdisseoSignalAtlasPipeline(settings)
    pipeline.x_client = cast(XClient, BackfillXClient())
    pipeline.github_client = cast(GitHubClient, DummyGitHubClient())

    report = pipeline.run(target_repos=2)

    assert len(calls) == 2
    assert report.days_scanned == 2
    assert report.total_candidates == 2
    assert report.target_reached is True


def test_pipeline_skips_known_recent_windows_and_continues_backwards(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    language = SearchLanguage("en", "English", ("Claude Code",), ("memory",))
    recent_now = datetime(2026, 3, 19, 12, 0, tzinfo=UTC)
    older_now = datetime(2026, 3, 18, 12, 0, tzinfo=UTC)

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
        x_min_request_interval_seconds=0.0,
        x_lookback_days=1,
        x_max_backfill_days=2,
        x_window_hours=24,
        x_refresh_live_window=False,
        x_rate_limit_default_wait_seconds=60,
        x_rate_limit_max_wait_seconds=900,
        target_repos=2,
        candidate_target_multiplier=1.0,
        query_history_file=tmp_path / "cache/query_history.json",
        query_history_retention_days=30,
        excluded_repos=set(),
        search_languages=[language],
    )

    calls: list[str] = []

    def fake_build_queries(
        _languages: list[SearchLanguage],
        *,
        now: datetime | None = None,
        lookback_days: int = 1,
        window_hours: int = 24,
        allow_live_window: bool = True,
    ) -> list[QuerySpec]:
        assert now is not None
        return [
            QuerySpec(
                language=language,
                topic_label="memory",
                query=f"memory query {now:%Y%m%d}",
                window_label=f"{now:%Y%m%d}-window",
                start_time=now,
                end_time=now,
                is_live_window=allow_live_window,
            )
        ]

    recent_query = QuerySpec(
        language=language,
        topic_label="memory",
        query=f"memory query {recent_now:%Y%m%d}",
        window_label=f"{recent_now:%Y%m%d}-window",
        start_time=recent_now,
        end_time=recent_now,
        is_live_window=False,
    )
    settings.query_history_file.parent.mkdir(parents=True, exist_ok=True)
    settings.query_history_file.write_text(
        json.dumps(
            {
                recent_query.signature: {
                    "executed_at": "2026-03-19T00:00:00+00:00",
                }
            }
        ),
        encoding="utf-8",
    )

    class SkipThenBackfillXClient:
        def search(
            self,
            query: str,
            max_results_per_page: int = 100,
            max_pages: int = 5,
            start_time: datetime | None = None,
            end_time: datetime | None = None,
        ) -> list[TweetHit]:
            calls.append(query)
            return [
                TweetHit(
                    tweet_id="older-hit",
                    text="https://github.com/acme/older-window-repo",
                    lang="en",
                    created_at=datetime.now(UTC),
                    public_metrics={},
                    expanded_urls=["https://github.com/acme/older-window-repo"],
                )
            ]

        def close(self) -> None:
            return None

    baseline_times = [recent_now, older_now]

    monkeypatch.setattr(
        "odisseo_signal_atlas.pipeline.datetime",
        type(
            "FakeDateTime",
            (),
            {
                "now": staticmethod(
                    lambda tz=None: baseline_times[0]
                ),
                "fromisoformat": staticmethod(datetime.fromisoformat),
            },
        ),
    )
    monkeypatch.setattr("odisseo_signal_atlas.pipeline.build_queries", fake_build_queries)

    pipeline = OdisseoSignalAtlasPipeline(settings)
    pipeline.x_client = cast(XClient, SkipThenBackfillXClient())
    pipeline.github_client = cast(GitHubClient, DummyGitHubClient())

    report = pipeline.run(target_repos=2)

    assert report.total_skipped_queries == 1
    assert report.total_queries == 1
    assert report.days_scanned == 2
    assert calls == [f"memory query {older_now:%Y%m%d}"]


def test_pipeline_writes_interrupted_report_from_ranked_cache(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    language = SearchLanguage("en", "English", ("Claude Code",), ("memory",))
    query = QuerySpec(
        language=language,
        topic_label="memory",
        query="memory query",
        window_label="20260318T0000Z-20260318T1200Z",
        start_time=datetime(2026, 3, 18, 0, 0, tzinfo=UTC),
        end_time=datetime(2026, 3, 18, 12, 0, tzinfo=UTC),
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
        x_min_request_interval_seconds=0.0,
        x_lookback_days=1,
        x_max_backfill_days=1,
        x_window_hours=12,
        x_refresh_live_window=True,
        x_rate_limit_default_wait_seconds=60,
        x_rate_limit_max_wait_seconds=900,
        target_repos=10,
        candidate_target_multiplier=1.15,
        query_history_file=tmp_path / "cache/query_history.json",
        query_history_retention_days=30,
        excluded_repos=set(),
        search_languages=[language],
    )
    settings.cache_dir.mkdir(parents=True, exist_ok=True)
    (settings.cache_dir / "ranked.json").write_text(
        json.dumps(
            [
                {
                    "repo_url": "https://github.com/acme/from-ranked-cache",
                    "repo_slug": "acme/from-ranked-cache",
                    "stars": 42,
                    "primary_language": "Python",
                    "description": "cached ranking",
                    "topics": ["memory"],
                    "html_url": "https://github.com/acme/from-ranked-cache",
                    "updated_at": "2026-03-19T00:00:00+00:00",
                    "pushed_at": "2026-03-19T00:00:00+00:00",
                    "source_languages": ["en"],
                    "matched_topics": ["memory"],
                    "source_tweets": [],
                    "score": 10,
                    "rationale": "Signals detected: cached.",
                }
            ]
        ),
        encoding="utf-8",
    )

    class InterruptingXClient:
        def search(
            self,
            query: str,
            max_results_per_page: int = 100,
            max_pages: int = 5,
            start_time: datetime | None = None,
            end_time: datetime | None = None,
        ) -> list[TweetHit]:
            raise KeyboardInterrupt()

        def close(self) -> None:
            return None

    monkeypatch.setattr(
        "odisseo_signal_atlas.pipeline.build_queries",
        lambda *_args, **_kwargs: [query],
    )

    pipeline = OdisseoSignalAtlasPipeline(settings)
    pipeline.x_client = cast(XClient, InterruptingXClient())
    pipeline.github_client = cast(GitHubClient, DummyGitHubClient())

    with pytest.raises(KeyboardInterrupt):
        pipeline.run(target_repos=10)

    content = settings.output_file.read_text(encoding="utf-8")
    assert "**Run status:** interrupted" in content
    assert "acme/from-ranked-cache" in content
