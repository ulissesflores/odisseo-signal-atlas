from datetime import UTC, datetime

from odisseo_signal_atlas.normalizers import (
    canonicalize_repo_url,
    compact_text,
    extract_repo_urls,
    to_iso,
)


def test_canonicalize_repo_url_normalizes_trailing_noise() -> None:
    normalized = canonicalize_repo_url("https://github.com/example/project.git),")
    assert normalized is not None
    canonical, slug = normalized
    assert canonical == "https://github.com/example/project"
    assert slug == "example/project"


def test_extract_repo_urls_deduplicates_text_and_expanded_links() -> None:
    results = extract_repo_urls(
        "hidden https://github.com/acme/atlas repeated https://github.com/acme/atlas?ref=x",
        ["https://github.com/acme/atlas", "https://github.com/other/repo"],
    )

    assert results == [
        ("https://github.com/acme/atlas", "acme/atlas"),
        ("https://github.com/other/repo", "other/repo"),
    ]


def test_canonicalize_repo_url_ignores_truncated_links() -> None:
    assert canonicalize_repo_url("https://github.com/acme/atl…") is None
    assert canonicalize_repo_url("https://github.com/acme/atl...") is None


def test_compact_text_and_to_iso_cover_public_output_helpers() -> None:
    assert compact_text("alpha    beta", max_length=20) == "alpha beta"
    assert compact_text("x" * 20, max_length=10) == "xxxxxxx..."
    assert to_iso(datetime(2026, 3, 19, tzinfo=UTC)) == "2026-03-19T00:00:00+00:00"
    assert to_iso(None) is None


def test_canonicalize_repo_url_rejects_github_topic_pages() -> None:
    assert canonicalize_repo_url("https://github.com/topics/ai-coding-tools") is None


def test_extract_repo_urls_prefers_expanded_urls_over_truncated_text() -> None:
    results = extract_repo_urls(
        "truncated https://github.com/thedotmack/cla",
        ["https://github.com/thedotmack/claude-mem"],
    )

    assert results == [("https://github.com/thedotmack/claude-mem", "thedotmack/claude-mem")]
