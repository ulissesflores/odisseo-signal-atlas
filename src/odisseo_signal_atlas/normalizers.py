"""Normalization helpers for text and GitHub URLs."""

from __future__ import annotations

import re
from datetime import datetime
from urllib.parse import urlparse

GITHUB_REPO_RE = re.compile(r"https?://github\.com/([\w.-]+)/([\w.-]+)", re.IGNORECASE)
NON_REPO_ROOTS = {
    "collections",
    "events",
    "features",
    "issues",
    "login",
    "marketplace",
    "notifications",
    "organizations",
    "orgs",
    "pulls",
    "search",
    "settings",
    "sponsors",
    "topics",
    "users",
}


def canonicalize_repo_url(url: str) -> tuple[str, str] | None:
    """Convert a GitHub URL into its canonical repository URL and slug."""

    raw = url.strip()
    if "…" in raw or raw.endswith("..."):
        return None
    cleaned = raw.rstrip(").,;!?")
    match = GITHUB_REPO_RE.search(cleaned)
    if match:
        owner, repo = match.group(1), match.group(2)
        if owner.lower() in NON_REPO_ROOTS:
            return None
    else:
        parsed = urlparse(cleaned)
        if parsed.netloc.lower() != "github.com":
            return None
        path_parts = [part for part in parsed.path.split("/") if part]
        if len(path_parts) < 2:
            return None
        if path_parts[0].lower() in NON_REPO_ROOTS:
            return None
        owner, repo = path_parts[0], path_parts[1]

    repo = repo.removesuffix(".git")
    slug = f"{owner}/{repo}"
    return f"https://github.com/{slug}", slug


def extract_repo_urls(text: str, expanded_urls: list[str]) -> list[tuple[str, str]]:
    """Extract and deduplicate canonical GitHub repository URLs."""

    found: list[tuple[str, str]] = []
    for candidate in expanded_urls:
        normalized = canonicalize_repo_url(candidate)
        if normalized and normalized not in found:
            found.append(normalized)
    if found:
        return found
    for candidate in re.findall(r"https?://\S+", text):
        normalized = canonicalize_repo_url(candidate)
        if normalized and normalized not in found:
            found.append(normalized)
    return found


def compact_text(text: str, max_length: int = 180) -> str:
    """Collapse whitespace and trim long text for report output."""

    normalized = " ".join(text.split())
    if len(normalized) <= max_length:
        return normalized
    return normalized[: max_length - 3].rstrip() + "..."


def to_iso(value: datetime | None) -> str | None:
    """Serialize optional datetimes for caches and reports."""

    return None if value is None else value.isoformat()
