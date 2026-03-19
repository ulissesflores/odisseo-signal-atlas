"""Main orchestration pipeline for discovery and export."""

from __future__ import annotations

import json
import logging
from collections import OrderedDict
from dataclasses import asdict
from pathlib import Path
from typing import Any

from .config import Settings, load_settings
from .exporters import write_markdown
from .github_client import GitHubClient
from .models import PipelineReport, RepoCandidate, RepoRecord
from .normalizers import extract_repo_urls, to_iso
from .query_builder import build_queries
from .ranker import rank_repo
from .x_client import XClient

LOGGER = logging.getLogger(__name__)


class OdisseoSignalAtlasPipeline:
    """Coordinate configuration, discovery, enrichment, ranking, and export."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.x_client = XClient(settings.x_bearer_token, settings.x_search_endpoint)
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

        queries = build_queries(self.settings.search_languages)
        candidates: OrderedDict[str, RepoCandidate] = OrderedDict()
        total_tweets = 0

        for query_spec in queries:
            LOGGER.info(
                "searching language=%s topic=%s",
                query_spec.language.code,
                query_spec.topic_label,
            )
            tweets = self.x_client.search(
                query=query_spec.query,
                max_results_per_page=self.settings.x_max_results_per_page,
                max_pages=self.settings.x_pages_per_query,
            )
            total_tweets += len(tweets)
            for tweet in tweets:
                for repo_url, repo_slug in extract_repo_urls(tweet.text, tweet.expanded_urls):
                    candidate = candidates.setdefault(
                        repo_slug,
                        RepoCandidate(repo_url=repo_url, repo_slug=repo_slug),
                    )
                    candidate.absorb(tweet, query_spec.topic_label, query_spec.language.code)

        ranked = self._enrich_and_rank(candidates)
        limit = target_repos or self.settings.target_repos
        ranked = ranked[:limit]

        output_path = write_markdown(
            self.settings.output_file,
            ranked,
            self.settings.site_url,
        )
        self._write_json(
            self.settings.cache_dir / "candidates.json",
            self._serialize_candidates(candidates),
        )
        self._write_json(self.settings.cache_dir / "ranked.json", self._serialize_ranked(ranked))

        return PipelineReport(
            output_path=str(output_path),
            total_queries=len(queries),
            total_tweets=total_tweets,
            total_candidates=len(candidates),
            total_ranked=len(ranked),
            site_url=self.settings.site_url,
        )

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
                "tweet_ids": [tweet.tweet_id for tweet in candidate.source_tweets],
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

    def _write_json(self, path: Path, payload: dict[str, Any] | list[dict[str, Any]]) -> None:
        """Persist a cache artifact to disk."""

        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
