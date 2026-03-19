from datetime import UTC, datetime

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

    queries = build_queries(
        languages,
        now=datetime(2026, 3, 19, 15, 45, tzinfo=UTC),
        lookback_days=1,
        window_hours=12,
    )

    assert len(queries) == len(TOPIC_GROUPS) * 3
    assert all("lang:pt" in query.query for query in queries)
    assert any('"memoria"' in query.query for query in queries)
    assert any('"voz"' in query.query for query in queries)
    assert all(query.start_time < query.end_time for query in queries)
    assert any(query.is_live_window for query in queries)


def test_build_queries_can_disable_live_window_flag() -> None:
    queries = build_queries(
        [SearchLanguage("en", "English", ("Claude Code",), ("memory",))],
        now=datetime(2026, 3, 19, 15, 45, tzinfo=UTC),
        lookback_days=1,
        window_hours=12,
        allow_live_window=False,
    )

    assert queries
    assert all(query.is_live_window is False for query in queries)


def test_build_queries_keeps_completed_windows_stable_across_hour_changes() -> None:
    language = SearchLanguage("en", "English", ("Claude Code",), ("memory",))

    queries_at_1915 = build_queries(
        [language],
        now=datetime(2026, 3, 19, 19, 15, tzinfo=UTC),
        lookback_days=1,
        window_hours=12,
    )
    queries_at_2015 = build_queries(
        [language],
        now=datetime(2026, 3, 19, 20, 15, tzinfo=UTC),
        lookback_days=1,
        window_hours=12,
    )

    historical_1915 = {query.window_label for query in queries_at_1915 if not query.is_live_window}
    historical_2015 = {query.window_label for query in queries_at_2015 if not query.is_live_window}

    assert "20260319T0000Z-20260319T1200Z" in historical_1915
    assert "20260319T0000Z-20260319T1200Z" in historical_2015
