from datetime import UTC, datetime
from pathlib import Path

from odisseo_signal_atlas.exporters import write_markdown
from odisseo_signal_atlas.models import RepoRecord, TweetHit


def test_write_markdown_contains_canonical_site_link(tmp_path: Path) -> None:
    repo = RepoRecord(
        repo_url="https://github.com/acme/atlas",
        repo_slug="acme/atlas",
        stars=99,
        primary_language="Python",
        description="Multilingual signal discovery engine.",
        topics=["mcp", "memory"],
        html_url="https://github.com/acme/atlas",
        updated_at=datetime.now(UTC),
        pushed_at=datetime.now(UTC),
        source_languages=["en", "pt"],
        matched_topics=["memory"],
        source_tweets=[
            TweetHit(
                tweet_id="1",
                text="tweet",
                lang="en",
                created_at=datetime.now(UTC),
                public_metrics={},
            )
        ],
        score=10,
        rationale="Signals detected: hidden gem.",
    )

    output = write_markdown(tmp_path / "report.md", [repo], "https://ulissesflores.com")
    content = output.read_text(encoding="utf-8")

    assert "Ulisses Flores" in content
    assert "https://ulissesflores.com" in content
    assert "Full GitHub link" in content
