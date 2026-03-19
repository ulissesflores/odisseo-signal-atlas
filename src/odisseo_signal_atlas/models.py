"""Core dataclasses used by the discovery pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from hashlib import sha256


@dataclass(frozen=True, slots=True)
class SearchLanguage:
    """Language-specific seed terms used to build X queries."""

    code: str
    label: str
    seed_terms: tuple[str, ...]
    topic_terms: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class QuerySpec:
    """Concrete query generated for a language/topic combination."""

    language: SearchLanguage
    topic_label: str
    query: str
    window_label: str
    start_time: datetime
    end_time: datetime
    is_live_window: bool = False

    @property
    def signature(self) -> str:
        """Stable signature used for query history and deduplication."""

        payload = "|".join(
            [
                self.language.code,
                self.topic_label,
                self.query,
                self.window_label,
                self.start_time.isoformat(),
                self.end_time.isoformat(),
            ]
        )
        return sha256(payload.encode("utf-8")).hexdigest()


@dataclass(slots=True)
class TweetHit:
    """Normalized X API tweet record used by downstream ranking."""

    tweet_id: str
    text: str
    lang: str | None
    created_at: datetime | None
    public_metrics: dict[str, int]
    author_username: str | None = None
    expanded_urls: list[str] = field(default_factory=list)
    matched_query: str | None = None


@dataclass(slots=True)
class RepoCandidate:
    """Repository candidate extracted from one or more tweets."""

    repo_url: str
    repo_slug: str
    source_tweets: list[TweetHit] = field(default_factory=list)
    source_languages: set[str] = field(default_factory=set)
    matched_topics: set[str] = field(default_factory=set)

    def absorb(self, tweet: TweetHit, topic_label: str, language_code: str) -> None:
        """Merge a new discovery event into the candidate."""

        if tweet.tweet_id not in {item.tweet_id for item in self.source_tweets}:
            self.source_tweets.append(tweet)
        self.source_languages.add(language_code)
        self.matched_topics.add(topic_label)


@dataclass(slots=True)
class RepoRecord:
    """Enriched GitHub repository record ready for ranking and export."""

    repo_url: str
    repo_slug: str
    stars: int
    primary_language: str | None
    description: str
    topics: list[str]
    html_url: str
    updated_at: datetime | None
    pushed_at: datetime | None
    source_languages: list[str]
    matched_topics: list[str]
    source_tweets: list[TweetHit]
    score: float = 0.0
    rationale: str = ""


@dataclass(slots=True)
class PipelineReport:
    """Summary emitted after a pipeline execution."""

    output_path: str
    total_planned_queries: int
    total_queries: int
    total_skipped_queries: int
    total_tweets: int
    total_candidates: int
    total_ranked: int
    days_scanned: int
    target_reached: bool
    site_url: str


@dataclass(slots=True)
class RepoInspectionReport:
    """Summary emitted after inspecting one repository."""

    repo_slug: str
    output_path: str
    source_cache: str
    remaining_candidates: int
