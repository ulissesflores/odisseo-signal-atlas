"""Query generation for multilingual X discovery."""

from __future__ import annotations

from collections.abc import Sequence

from .models import QuerySpec, SearchLanguage

TOPIC_GROUPS: dict[str, tuple[str, ...]] = {
    "broad": (),
    "memory": ("memory", "memoria", "memoire", "context", "vector", "recall"),
    "agents": ("multi-agent", "agent", "agents", "swarm", "orchestration"),
    "protocols": ("mcp", "model context protocol", "hooks", "gossip", "p2p", "toon"),
    "voice_rag": ("voice", "speech", "audio", "rag", "retrieval"),
}


def build_queries(languages: Sequence[SearchLanguage]) -> list[QuerySpec]:
    """Build deterministic query specs across languages and topic groups."""

    queries: list[QuerySpec] = []
    for language in languages:
        seed_block = "(" + " OR ".join(f'"{seed}"' for seed in language.seed_terms) + ")"
        github_block = '(github.com OR "github.com/")'
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
            queries.append(QuerySpec(language=language, topic_label=topic_label, query=query))
    return queries


def _merge_terms(primary: Sequence[str], secondary: Sequence[str]) -> list[str]:
    """Merge and deduplicate query terms while preserving order."""

    merged: list[str] = []
    for term in [*primary[:4], *secondary[:4]]:
        if term not in merged:
            merged.append(term)
    return merged
