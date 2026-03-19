"""Main orchestration pipeline for discovery and export."""

from __future__ import annotations

import json
import logging
import math
import time
from collections import OrderedDict
from dataclasses import asdict
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from .config import Settings, load_settings
from .exceptions import RateLimitError
from .exporters import write_markdown
from .github_client import GitHubClient
from .models import PipelineReport, QuerySpec, RepoCandidate, RepoRecord, TweetHit
from .normalizers import extract_repo_urls, to_iso
from .query_builder import build_queries
from .query_state import QueryHistoryStore
from .ranker import rank_repo
from .x_client import XClient

LOGGER = logging.getLogger(__name__)


class OdisseoSignalAtlasPipeline:
    """Coordinate configuration, discovery, enrichment, ranking, and export."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.x_client = XClient(
            settings.x_bearer_token,
            settings.x_search_endpoint,
            min_request_interval_seconds=settings.x_min_request_interval_seconds,
        )
        self.github_client = GitHubClient(settings.github_token)

    @classmethod
    def from_env(cls, project_root: str | Path | None = None) -> OdisseoSignalAtlasPipeline:
        """Build a pipeline instance from layered environment files."""

        return cls(load_settings(project_root))

    def close(self) -> None:
        """Close all remote clients."""

        self.x_client.close()
        self.github_client.close()

    def run(self, target_repos: int | None = None) -> PipelineReport:
        """Run the full discovery pipeline and return a structured summary."""

        limit = target_repos or self.settings.target_repos
        candidate_target = self._target_candidate_count(limit)
        baseline_now = datetime.now(UTC)
        history = QueryHistoryStore.load(
            self.settings.query_history_file,
            retention_days=self.settings.query_history_retention_days,
        )
        candidates = self._load_candidates(self.settings.cache_dir / "candidates.json")
        cached_ranked = self._load_ranked(self.settings.cache_dir / "ranked.json")
        queries: list[QuerySpec] = []
        total_tweets = 0
        skipped_queries = 0
        executed_queries = 0
        days_scanned = 0
        self._write_report_snapshot(
            repos=cached_ranked[:limit],
            run_status="running",
            stats=self._build_report_stats(
                total_planned_queries=0,
                total_queries=0,
                total_skipped_queries=0,
                total_tweets=0,
                total_candidates=len(candidates),
                days_scanned=0,
                target_repos=limit,
            ),
            notes=["Run started. The report will be updated when the execution finishes."],
        )

        try:
            while (
                days_scanned < self.settings.x_max_backfill_days
                and len(candidates) < candidate_target
            ):
                batch_lookback_days = min(
                    self.settings.x_lookback_days,
                    self.settings.x_max_backfill_days - days_scanned,
                )
                batch_queries = build_queries(
                    self.settings.search_languages,
                    now=baseline_now - timedelta(days=days_scanned),
                    lookback_days=batch_lookback_days,
                    window_hours=self.settings.x_window_hours,
                    allow_live_window=days_scanned == 0,
                )
                queries.extend(batch_queries)
                self._write_json(
                    self.settings.cache_dir / "query_plan.json",
                    self._serialize_queries(queries),
                )

                for query_spec in batch_queries:
                    if history.should_skip(
                        query_spec,
                        refresh_live_window=self.settings.x_refresh_live_window,
                    ):
                        skipped_queries += 1
                        LOGGER.info(
                            "skipping language=%s topic=%s window=%s reason=query-history",
                            query_spec.language.code,
                            query_spec.topic_label,
                            query_spec.window_label,
                        )
                        continue
                    LOGGER.info(
                        "searching language=%s topic=%s window=%s",
                        query_spec.language.code,
                        query_spec.topic_label,
                        query_spec.window_label,
                    )
                    tweets = self._search_with_backoff(query_spec)
                    history.mark_complete(query_spec, len(tweets))
                    executed_queries += 1
                    total_tweets += len(tweets)
                    for tweet in tweets:
                        for repo_url, repo_slug in extract_repo_urls(
                            tweet.text,
                            tweet.expanded_urls,
                        ):
                            candidate = candidates.setdefault(
                                repo_slug,
                                RepoCandidate(repo_url=repo_url, repo_slug=repo_slug),
                            )
                            candidate.absorb(
                                tweet,
                                query_spec.topic_label,
                                query_spec.language.code,
                            )
                    self._persist_progress(history, candidates)

                days_scanned += batch_lookback_days
                self._write_report_snapshot(
                    repos=cached_ranked[:limit],
                    run_status="running",
                    stats=self._build_report_stats(
                        total_planned_queries=len(queries),
                        total_queries=executed_queries,
                        total_skipped_queries=skipped_queries,
                        total_tweets=total_tweets,
                        total_candidates=len(candidates),
                        days_scanned=days_scanned,
                        target_repos=limit,
                    ),
                    notes=[
                        (
                            "Progress snapshot. Ranked entries shown here come from the last "
                            "completed enrichment cache until the current run finishes."
                        ),
                    ],
                )
        except BaseException as exc:
            run_status = "interrupted" if isinstance(exc, KeyboardInterrupt) else "failed"
            self._write_report_snapshot(
                repos=cached_ranked[:limit],
                run_status=run_status,
                stats=self._build_report_stats(
                    total_planned_queries=len(queries),
                    total_queries=executed_queries,
                    total_skipped_queries=skipped_queries,
                    total_tweets=total_tweets,
                    total_candidates=len(candidates),
                    days_scanned=days_scanned,
                    target_repos=limit,
                ),
                notes=[
                    (
                        "The current run stopped before final enrichment. "
                        f"Reason: {exc or run_status}."
                    ),
                    "The ranked entries shown below come from the most recent completed cache.",
                ],
            )
            raise

        ranked = self._enrich_and_rank(candidates)
        ranked = ranked[:limit]
        target_reached = len(ranked) >= limit

        output_path = self._write_report_snapshot(
            repos=ranked,
            run_status="complete",
            stats=self._build_report_stats(
                total_planned_queries=len(queries),
                total_queries=executed_queries,
                total_skipped_queries=skipped_queries,
                total_tweets=total_tweets,
                total_candidates=len(candidates),
                days_scanned=days_scanned,
                target_repos=limit,
            ),
            notes=self._build_completion_notes(
                target_reached=target_reached,
                target_repos=limit,
                total_ranked=len(ranked),
                days_scanned=days_scanned,
            ),
        )
        self._write_json(
            self.settings.cache_dir / "candidates.json",
            self._serialize_candidates(candidates),
        )
        self._write_json(self.settings.cache_dir / "ranked.json", self._serialize_ranked(ranked))
        self._write_json(
            self.settings.cache_dir / "query_plan.json",
            self._serialize_queries(queries),
        )
        history.save()

        return PipelineReport(
            output_path=str(output_path),
            total_planned_queries=len(queries),
            total_queries=executed_queries,
            total_skipped_queries=skipped_queries,
            total_tweets=total_tweets,
            total_candidates=len(candidates),
            total_ranked=len(ranked),
            days_scanned=days_scanned,
            target_reached=target_reached,
            site_url=self.settings.site_url,
        )

    def _search_with_backoff(self, query_spec: QuerySpec) -> list[TweetHit]:
        """Execute a query and wait for the X reset window when rate-limited."""

        while True:
            try:
                return self.x_client.search(
                    query=query_spec.query,
                    max_results_per_page=self.settings.x_max_results_per_page,
                    max_pages=self.settings.x_pages_per_query,
                    start_time=query_spec.start_time,
                    end_time=query_spec.end_time,
                )
            except RateLimitError as exc:
                wait_seconds = max(
                    self.settings.x_rate_limit_default_wait_seconds,
                    exc.retry_after_seconds,
                )
                wait_seconds = min(wait_seconds, self.settings.x_rate_limit_max_wait_seconds)
                LOGGER.warning(
                    "rate limited language=%s topic=%s window=%s wait_seconds=%s reset_at=%s",
                    query_spec.language.code,
                    query_spec.topic_label,
                    query_spec.window_label,
                    wait_seconds,
                    to_iso(exc.reset_at),
                )
                time.sleep(wait_seconds)

    def _enrich_and_rank(self, candidates: OrderedDict[str, RepoCandidate]) -> list[RepoRecord]:
        """Enrich candidates with GitHub metadata and sort by score."""

        ranked: list[RepoRecord] = []
        for candidate in candidates.values():
            try:
                record = self.github_client.build_record(
                    repo_slug=candidate.repo_slug,
                    source_languages=sorted(candidate.source_languages),
                    matched_topics=sorted(candidate.matched_topics),
                    source_tweets=candidate.source_tweets,
                )
            except Exception as exc:
                LOGGER.warning("skipping repo_slug=%s reason=%s", candidate.repo_slug, exc)
                continue
            ranked.append(rank_repo(record, self.settings.excluded_repos))

        filtered = [repo for repo in ranked if repo.score > 0]
        filtered.sort(key=lambda repo: repo.score, reverse=True)
        return filtered

    def _load_candidates(self, path: Path) -> OrderedDict[str, RepoCandidate]:
        """Load previously discovered candidates so interrupted runs can resume."""

        candidates: OrderedDict[str, RepoCandidate] = OrderedDict()
        if not path.exists():
            return candidates

        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            return candidates

        for slug, value in payload.items():
            if not isinstance(slug, str) or not isinstance(value, dict):
                continue
            repo_url = value.get("repo_url")
            if not isinstance(repo_url, str) or not repo_url:
                continue
            source_tweets = [
                self._deserialize_tweet(item)
                for item in value.get("source_tweets", [])
                if isinstance(item, dict)
            ]
            candidates[slug] = RepoCandidate(
                repo_url=repo_url,
                repo_slug=slug,
                source_tweets=[tweet for tweet in source_tweets if tweet is not None],
                source_languages={
                    language
                    for language in value.get("source_languages", [])
                    if isinstance(language, str)
                },
                matched_topics={
                    topic for topic in value.get("matched_topics", []) if isinstance(topic, str)
                },
            )
        return candidates

    def _load_ranked(self, path: Path) -> list[RepoRecord]:
        """Load the last completed ranked output for fallback report rendering."""

        if not path.exists():
            return []
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, list):
            return []

        repos: list[RepoRecord] = []
        for item in payload:
            if not isinstance(item, dict):
                continue
            repo_slug = item.get("repo_slug")
            repo_url = item.get("repo_url")
            if not isinstance(repo_slug, str) or not isinstance(repo_url, str):
                continue
            description = item.get("description")
            html_url = item.get("html_url")
            rationale = item.get("rationale")
            repos.append(
                RepoRecord(
                    repo_url=repo_url,
                    repo_slug=repo_slug,
                    stars=int(item.get("stars", 0)),
                    primary_language=item.get("primary_language")
                    if isinstance(item.get("primary_language"), str)
                    else None,
                    description=description if isinstance(description, str) else "",
                    topics=[
                        topic for topic in item.get("topics", []) if isinstance(topic, str)
                    ],
                    html_url=html_url if isinstance(html_url, str) else repo_url,
                    updated_at=self._parse_cached_datetime(item.get("updated_at")),
                    pushed_at=self._parse_cached_datetime(item.get("pushed_at")),
                    source_languages=[
                        lang
                        for lang in item.get("source_languages", [])
                        if isinstance(lang, str)
                    ],
                    matched_topics=[
                        topic
                        for topic in item.get("matched_topics", [])
                        if isinstance(topic, str)
                    ],
                    source_tweets=[],
                    score=float(item.get("score", 0.0)),
                    rationale=rationale if isinstance(rationale, str) else "",
                )
            )
        return repos

    def _serialize_candidates(
        self,
        candidates: OrderedDict[str, RepoCandidate],
    ) -> dict[str, dict[str, Any]]:
        """Serialize candidate cache data into JSON-safe structures."""

        return {
            slug: {
                "repo_url": candidate.repo_url,
                "source_languages": sorted(candidate.source_languages),
                "matched_topics": sorted(candidate.matched_topics),
                "source_tweets": [
                    self._serialize_tweet(tweet) for tweet in candidate.source_tweets
                ],
            }
            for slug, candidate in candidates.items()
        }

    def _serialize_ranked(self, ranked: list[RepoRecord]) -> list[dict[str, Any]]:
        """Serialize ranked output into JSON-safe structures."""

        payload: list[dict[str, Any]] = []
        for repo in ranked:
            item = asdict(repo)
            item["updated_at"] = to_iso(repo.updated_at)
            item["pushed_at"] = to_iso(repo.pushed_at)
            item["source_tweets"] = [tweet.tweet_id for tweet in repo.source_tweets]
            payload.append(item)
        return payload

    def _serialize_queries(self, queries: list[QuerySpec]) -> list[dict[str, Any]]:
        """Serialize the concrete query plan for observability and debugging."""

        payload: list[dict[str, Any]] = []
        for query in queries:
            payload.append(
                {
                    "signature": query.signature,
                    "language": query.language.code,
                    "topic_label": query.topic_label,
                    "query": query.query,
                    "window_label": query.window_label,
                    "start_time": to_iso(query.start_time),
                    "end_time": to_iso(query.end_time),
                    "is_live_window": query.is_live_window,
                }
            )
        return payload

    def _write_json(self, path: Path, payload: dict[str, Any] | list[dict[str, Any]]) -> None:
        """Persist a cache artifact to disk."""

        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def _persist_progress(
        self,
        history: QueryHistoryStore,
        candidates: OrderedDict[str, RepoCandidate],
    ) -> None:
        """Persist resumable state after each completed query."""

        history.save()
        self._write_json(
            self.settings.cache_dir / "candidates.json",
            self._serialize_candidates(candidates),
        )

    def _serialize_tweet(self, tweet: TweetHit) -> dict[str, Any]:
        """Serialize a tweet hit for resumable candidate cache storage."""

        return {
            "tweet_id": tweet.tweet_id,
            "text": tweet.text,
            "lang": tweet.lang,
            "created_at": to_iso(tweet.created_at),
            "public_metrics": tweet.public_metrics,
            "author_username": tweet.author_username,
            "expanded_urls": tweet.expanded_urls,
            "matched_query": tweet.matched_query,
        }

    def _deserialize_tweet(self, payload: dict[str, Any]) -> TweetHit | None:
        """Rebuild a cached tweet hit from JSON-safe payload data."""

        tweet_id = payload.get("tweet_id")
        text = payload.get("text")
        if not isinstance(tweet_id, str) or not isinstance(text, str):
            return None
        created_at = payload.get("created_at")
        public_metrics_raw = payload.get("public_metrics")
        public_metrics = (
            {
                key: value
                for key, value in public_metrics_raw.items()
                if isinstance(key, str) and isinstance(value, int)
            }
            if isinstance(public_metrics_raw, dict)
            else {}
        )
        return TweetHit(
            tweet_id=tweet_id,
            text=text,
            lang=payload.get("lang") if isinstance(payload.get("lang"), str) else None,
            created_at=self._parse_cached_datetime(created_at),
            public_metrics=public_metrics,
            author_username=payload.get("author_username")
            if isinstance(payload.get("author_username"), str)
            else None,
            expanded_urls=[
                url for url in payload.get("expanded_urls", []) if isinstance(url, str)
            ],
            matched_query=payload.get("matched_query")
            if isinstance(payload.get("matched_query"), str)
            else None,
        )

    def _parse_cached_datetime(self, value: Any) -> datetime | None:
        """Parse an optional cached ISO datetime."""

        if not isinstance(value, str) or not value:
            return None
        return datetime.fromisoformat(value)

    def _target_candidate_count(self, target_repos: int) -> int:
        """Translate the export target into a candidate target with small buffer."""

        buffered_target = math.ceil(
            target_repos * self.settings.candidate_target_multiplier
        )
        return max(target_repos, buffered_target)

    def _build_report_stats(
        self,
        *,
        total_planned_queries: int,
        total_queries: int,
        total_skipped_queries: int,
        total_tweets: int,
        total_candidates: int,
        days_scanned: int,
        target_repos: int,
    ) -> dict[str, int]:
        """Build a stable stats payload for report snapshots."""

        return {
            "Target repositories": target_repos,
            "Queries planned": total_planned_queries,
            "Queries executed": total_queries,
            "Queries skipped from history": total_skipped_queries,
            "Tweets analyzed": total_tweets,
            "Candidates discovered": total_candidates,
            "Days scanned": days_scanned,
        }

    def _build_completion_notes(
        self,
        *,
        target_reached: bool,
        target_repos: int,
        total_ranked: int,
        days_scanned: int,
    ) -> list[str]:
        """Build completion notes for the final report snapshot."""

        if target_reached:
            return [f"Target reached with {total_ranked} ranked repositories."]
        return [
            (
                f"Target not reached. The run exported {total_ranked} repositories after "
                f"scanning {days_scanned} days."
            ),
            (
                "Increase ODISSEO_X_MAX_BACKFILL_DAYS, widen query seeds, or add a second "
                "source beyond X recent search to push toward 500."
            ),
        ]

    def _write_report_snapshot(
        self,
        *,
        repos: list[RepoRecord],
        run_status: str,
        stats: dict[str, int],
        notes: list[str],
    ) -> Path:
        """Write the public Markdown report for a running or completed snapshot."""

        return write_markdown(
            self.settings.output_file,
            repos,
            self.settings.site_url,
            run_status=run_status,
            stats=stats,
            notes=notes,
        )
