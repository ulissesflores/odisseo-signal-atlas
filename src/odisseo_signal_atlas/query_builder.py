"""Query generation for multilingual X discovery."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime, timedelta

from .models import QuerySpec, SearchLanguage

TOPIC_GROUPS: dict[str, tuple[str, ...]] = {
    "broad": (),
    "memory": ("memory", "memoria", "memoire", "context", "vector", "recall"),
    "agents": ("multi-agent", "agent", "agents", "swarm", "orchestration"),
    "protocols": ("mcp", "model context protocol", "hooks", "gossip", "p2p", "toon"),
    "voice_rag": ("voice", "speech", "audio", "rag", "retrieval"),
}


def build_queries(
    languages: Sequence[SearchLanguage],
    *,
    now: datetime | None = None,
    lookback_days: int = 3,
    window_hours: int = 12,
    allow_live_window: bool = True,
) -> list[QuerySpec]:
    """Build deterministic query specs across languages, topics, and time windows."""

    queries: list[QuerySpec] = []
    windows = _build_windows(
        now=now,
        lookback_days=lookback_days,
        window_hours=window_hours,
        allow_live_window=allow_live_window,
    )
    for language in languages:
        seed_block = "(" + " OR ".join(f'"{seed}"' for seed in language.seed_terms) + ")"
        github_block = '(github.com OR "github.com/")'
        for window in windows:
            for topic_label, topic_terms in TOPIC_GROUPS.items():
                query_parts = [
                    seed_block,
                    github_block,
                ]
                merged_terms = _merge_terms(topic_terms, language.topic_terms)
                if merged_terms:
                    topic_block = "(" + " OR ".join(f'"{term}"' for term in merged_terms) + ")"
                    query_parts.append(topic_block)
                query_parts.extend(
                    [
                        f"lang:{language.code}",
                        "-is:retweet",
                        "-is:reply",
                    ]
                )
                query = " ".join(query_parts)
                queries.append(
                    QuerySpec(
                        language=language,
                        topic_label=topic_label,
                        query=query,
                        window_label=_format_window_label(window[0], window[1]),
                        start_time=window[0],
                        end_time=window[1],
                        is_live_window=window[2],
                    )
                )
    return queries


def _merge_terms(primary: Sequence[str], secondary: Sequence[str]) -> list[str]:
    """Merge and deduplicate query terms while preserving order."""

    merged: list[str] = []
    for term in [*primary[:4], *secondary[:4]]:
        if term not in merged:
            merged.append(term)
    return merged


def _build_windows(
    *,
    now: datetime | None,
    lookback_days: int,
    window_hours: int,
    allow_live_window: bool,
) -> list[tuple[datetime, datetime, bool]]:
    """Build newest-first UTC windows for recent-search backfills."""

    if lookback_days < 1:
        raise ValueError("lookback_days must be >= 1")
    if window_hours < 1:
        raise ValueError("window_hours must be >= 1")

    current = (now or datetime.now(UTC)).astimezone(UTC)
    current_mark = current.replace(minute=0, second=0, microsecond=0)
    boundary_hour = (current_mark.hour // window_hours) * window_hours
    boundary = current_mark.replace(hour=boundary_hour)
    cutoff = current_mark - timedelta(days=lookback_days)
    windows: list[tuple[datetime, datetime, bool]] = []
    if allow_live_window and boundary < current_mark:
        windows.append((boundary, current_mark, True))

    end_time = boundary
    while end_time > cutoff:
        start_time = end_time - timedelta(hours=window_hours)
        if start_time < cutoff:
            start_time = cutoff
        windows.append((start_time, end_time, False))
        end_time = start_time
    return windows


def _format_window_label(start_time: datetime, end_time: datetime) -> str:
    """Format a stable cache-friendly window label."""

    return f"{start_time:%Y%m%dT%H%MZ}-{end_time:%Y%m%dT%H%MZ}"
