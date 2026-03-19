from odisseo_signal_atlas.models import SearchLanguage
from odisseo_signal_atlas.query_builder import TOPIC_GROUPS, build_queries


def test_build_queries_uses_language_terms_and_topic_groups() -> None:
    languages = [
        SearchLanguage(
            code="pt",
            label="Portuguese",
            seed_terms=("Claude Code", "Claude MCP"),
            topic_terms=("memoria", "voz", "multiagente", "rag"),
        )
    ]

    queries = build_queries(languages)

    assert len(queries) == len(TOPIC_GROUPS)
    assert all("lang:pt" in query.query for query in queries)
    assert any('"memoria"' in query.query for query in queries)
    assert any('"voz"' in query.query for query in queries)

