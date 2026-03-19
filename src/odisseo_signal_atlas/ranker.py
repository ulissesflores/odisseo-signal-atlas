"""Repository scoring and rationale generation."""

from __future__ import annotations

import re
from datetime import UTC, datetime

from .models import RepoRecord
from .normalizers import compact_text

KEYWORD_BUCKETS = {
    "memory": {
        "memory",
        "memo",
        "vector",
        "context",
        "recall",
        "memoria",
        "メモリ",
        "记忆",
        "메모리",
    },
    "agents": {"agent", "agents", "orchestr", "swarm", "crew", "multi-agent"},
    "protocols": {"mcp", "hook", "hooks", "protocol", "toon", "p2p", "gossip"},
    "voice_rag": {"voice", "speech", "audio", "rag", "retrieval", "whisper"},
}

PRIORITY_TAGS = ["hidden_gem", "polyglot", "fresh", "strong_signal"]


def rank_repo(record: RepoRecord, excluded_repos: set[str]) -> RepoRecord:
    """Score a repository and generate a concise rationale."""

    haystack = " ".join(
        [
            record.repo_slug,
            record.description or "",
            " ".join(record.topics),
            " ".join(record.matched_topics),
        ]
    ).lower()

    if record.repo_slug in excluded_repos:
        record.score = -9999.0
        record.rationale = (
            "Excluded because the repository is already known, obvious, "
            "or intentionally blacklisted."
        )
        return record

    score = min(record.stars, 3000) / 100
    tags: list[str] = []

    for bucket, keywords in KEYWORD_BUCKETS.items():
        if any(_contains_keyword(haystack, keyword) for keyword in keywords):
            score += 20
            tags.append(bucket)

    if 5 <= record.stars <= 2000:
        score += 18
        tags.append("hidden_gem")
    elif record.stars > 20000:
        score -= 15

    if len(record.source_languages) >= 2:
        score += 12
        tags.append("polyglot")

    now = datetime.now(UTC)
    if record.pushed_at:
        age_days = (now - record.pushed_at).days
        if age_days <= 90:
            score += 14
            tags.append("fresh")
        elif age_days > 730:
            score -= 8

    if len(record.source_tweets) >= 3:
        score += 10
        tags.append("strong_signal")

    record.score = score
    record.rationale = _build_rationale(record, tags)
    return record


def _build_rationale(record: RepoRecord, tags: list[str]) -> str:
    """Build a public-facing rationale string without hype inflation."""

    ordered_tags = [tag for tag in PRIORITY_TAGS if tag in tags] + [
        tag for tag in tags if tag not in PRIORITY_TAGS
    ]
    label = ", ".join(tag.replace("_", " ") for tag in ordered_tags[:6]) or "weak signal"
    description = compact_text(
        record.description or "No GitHub description was provided.",
        max_length=120,
    )
    return (
        f"Signals detected: {label}. "
        "The repository intersects with the target frontier topics and appears "
        "less obvious than the mainstream hubs. "
        f"Base description: {description}"
    )


def _contains_keyword(haystack: str, keyword: str) -> bool:
    """Match ASCII keywords on token boundaries while preserving non-ASCII recall."""

    if not keyword.isascii():
        return keyword in haystack
    pattern = re.compile(rf"(?<![a-z0-9]){re.escape(keyword)}(?![a-z0-9])")
    return pattern.search(haystack) is not None
