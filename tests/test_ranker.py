from datetime import UTC, datetime, timedelta

from odisseo_signal_atlas.models import RepoRecord, TweetHit
from odisseo_signal_atlas.ranker import rank_repo


def _tweet(tweet_id: str) -> TweetHit:
    return TweetHit(
        tweet_id=tweet_id,
        text="repo",
        lang="en",
        created_at=datetime.now(UTC),
        public_metrics={"like_count": 1},
    )


def _repo(slug: str = "acme/memory-rag") -> RepoRecord:
    now = datetime.now(UTC)
    return RepoRecord(
        repo_url=f"https://github.com/{slug}",
        repo_slug=slug,
        stars=120,
        primary_language="Python",
        description="Advanced memory and RAG orchestration for multi-agent workflows.",
        topics=["mcp", "memory", "rag"],
        html_url=f"https://github.com/{slug}",
        updated_at=now,
        pushed_at=now - timedelta(days=7),
        source_languages=["en", "pt"],
        matched_topics=["memory", "agents"],
        source_tweets=[_tweet("1"), _tweet("2"), _tweet("3")],
    )


def test_rank_repo_scores_hidden_gem_and_polyglot_signals() -> None:
    ranked = rank_repo(_repo(), excluded_repos=set())

    assert ranked.score > 0
    assert "hidden gem" in ranked.rationale
    assert "polyglot" in ranked.rationale


def test_rank_repo_excludes_blacklisted_repository() -> None:
    ranked = rank_repo(_repo("anthropics/skills"), excluded_repos={"anthropics/skills"})

    assert ranked.score < 0
    assert "Excluded" in ranked.rationale


def test_rank_repo_avoids_substring_false_positives() -> None:
    repo = _repo("acme/storage-hub")
    repo.description = "Distributed storage engine for logs."
    repo.topics = ["storage"]
    repo.matched_topics = []
    repo.source_tweets = [_tweet("1")]

    ranked = rank_repo(repo, excluded_repos=set())

    assert "voice rag" not in ranked.rationale
