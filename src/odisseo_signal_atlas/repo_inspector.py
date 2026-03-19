"""Sequential repository inspection workflow."""

from __future__ import annotations

import json
from collections import OrderedDict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .config import Settings, load_settings
from .exceptions import OdisseoError
from .github_client import GitHubClient
from .models import RepoInspectionReport, RepoRecord
from .normalizers import canonicalize_repo_url, compact_text, to_iso
from .ranker import rank_repo


class RepoInspector:
    """Inspect repositories one by one using cached discovery results."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.github_client = GitHubClient(settings.github_token)

    @classmethod
    def from_env(cls, project_root: str | Path | None = None) -> RepoInspector:
        """Build an inspector instance from environment configuration."""

        return cls(load_settings(project_root))

    def close(self) -> None:
        """Close remote clients."""

        self.github_client.close()

    def inspect_repo(self, repo_ref: str) -> RepoInspectionReport:
        """Inspect a specific GitHub repository reference or URL."""

        repo_url, repo_slug = _resolve_repo_ref(repo_ref)
        ranked_cache = self._load_ranked_cache()
        cached_entry = ranked_cache.get(repo_slug, {})
        owner, repo = repo_slug.split("/", 1)
        payload = self.github_client.fetch_repo(owner, repo)
        readme = self.github_client.fetch_readme(owner, repo)
        languages = self.github_client.fetch_languages(owner, repo)
        record = rank_repo(
            RepoRecord(
                repo_url=payload["html_url"],
                repo_slug=repo_slug,
                stars=int(payload.get("stargazers_count", 0)),
                primary_language=payload.get("language"),
                description=payload.get("description") or "",
                topics=list(payload.get("topics", [])),
                html_url=payload["html_url"],
                updated_at=_parse_datetime(payload.get("updated_at")),
                pushed_at=_parse_datetime(payload.get("pushed_at")),
                source_languages=_list_str(cached_entry.get("source_languages")),
                matched_topics=_list_str(cached_entry.get("matched_topics")),
                source_tweets=[],
            ),
            self.settings.excluded_repos,
        )
        output_path = self._write_repo_markdown(
            payload=payload,
            record=record,
            readme=readme,
            languages=languages,
            source_cache="ranked" if cached_entry else "direct",
            fallback_repo_url=repo_url,
        )
        state = self._load_inspection_state()
        completed = state.setdefault("completed", {})
        completed[repo_slug] = {
            "output_path": str(output_path),
            "analyzed_at": to_iso(datetime.now(UTC)),
            "source_cache": "ranked" if cached_entry else "direct",
        }
        self._save_inspection_state(state)

        remaining = len([slug for slug in ranked_cache if slug not in completed])
        return RepoInspectionReport(
            repo_slug=repo_slug,
            output_path=str(output_path),
            source_cache="ranked" if cached_entry else "direct",
            remaining_candidates=max(0, remaining),
        )

    def inspect_next(self) -> RepoInspectionReport:
        """Inspect the next unseen repository from the ranked cache."""

        ranked_cache = self._load_ranked_cache()
        if not ranked_cache:
            raise OdisseoError("No ranked cache is available yet. Run discovery first.")
        state = self._load_inspection_state()
        completed = state.get("completed", {})

        for repo_slug in ranked_cache:
            if repo_slug not in completed:
                return self.inspect_repo(repo_slug)

        raise OdisseoError("Every ranked repository has already been inspected.")

    def _load_ranked_cache(self) -> OrderedDict[str, dict[str, Any]]:
        """Load ranked repositories as an ordered slug-to-payload mapping."""

        path = self.settings.cache_dir / "ranked.json"
        if not path.exists():
            return OrderedDict()
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, list):
            return OrderedDict()
        ranked: OrderedDict[str, dict[str, Any]] = OrderedDict()
        for item in payload:
            if not isinstance(item, dict):
                continue
            repo_slug = item.get("repo_slug")
            if isinstance(repo_slug, str):
                ranked[repo_slug] = item
        return ranked

    def _load_inspection_state(self) -> dict[str, Any]:
        """Load the sequential inspection state file."""

        path = self.settings.inspection_state_file
        if not path.exists():
            return {"completed": {}}
        payload = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(payload, dict):
            completed = payload.get("completed")
            if isinstance(completed, dict):
                return {"completed": completed}
        return {"completed": {}}

    def _save_inspection_state(self, payload: dict[str, Any]) -> None:
        """Persist the inspection state file."""

        path = self.settings.inspection_state_file
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def _write_repo_markdown(
        self,
        *,
        payload: dict[str, Any],
        record: RepoRecord,
        readme: str | None,
        languages: dict[str, int],
        source_cache: str,
        fallback_repo_url: str,
    ) -> Path:
        """Write a detailed repository investigation report."""

        output_path = self.settings.repo_insights_dir / (
            record.repo_slug.replace("/", "--") + ".md"
        )
        output_path.parent.mkdir(parents=True, exist_ok=True)
        top_languages = sorted(
            languages.items(),
            key=lambda item: item[1],
            reverse=True,
        )[:8]
        language_breakdown = ", ".join(
            f"{name}: {count}" for name, count in top_languages
        ) or "not available"
        readme_flags = _detect_readme_flags(readme or "")
        notes = _build_investigation_notes(payload, record, readme_flags)
        description = compact_text(
            record.description or "No description.",
            max_length=220,
        )
        discovery_languages = ", ".join(record.source_languages) or "not present in ranked cache"
        matched_topics = ", ".join(record.matched_topics) or "not present in ranked cache"

        lines = [
            f"# Repo Investigation: {record.repo_slug}",
            "",
            f"Generated by [Ulisses Flores]({self.settings.site_url}).",
            "",
            f"**Generated at:** {datetime.now().isoformat(timespec='seconds')}",
            f"**Source cache:** {source_cache}",
            f"**Repository URL:** {payload.get('html_url') or fallback_repo_url}",
            f"**Stars:** {record.stars}",
            f"**Primary language:** {record.primary_language or 'unknown'}",
            f"**Current heuristic score:** {record.score:.1f}",
            f"**Current rationale:** {record.rationale}",
            "",
            "## Repository Signals",
            "",
            f"- Description: {description}",
            f"- Topics: {', '.join(record.topics) or 'none'}",
            f"- Homepage: {payload.get('homepage') or 'not set'}",
            f"- Default branch: {payload.get('default_branch') or 'unknown'}",
            f"- License: {_license_name(payload)}",
            f"- Open issues: {payload.get('open_issues_count', 0)}",
            f"- Forks: {payload.get('forks_count', 0)}",
            f"- Archived: {payload.get('archived', False)}",
            f"- Last pushed at: {to_iso(record.pushed_at) or 'unknown'}",
            f"- Last updated at: {to_iso(record.updated_at) or 'unknown'}",
            "",
            "## Discovery Context",
            "",
            f"- Discovery languages: {discovery_languages}",
            f"- Matched topics: {matched_topics}",
            f"- Language breakdown: {language_breakdown}",
            "",
            "## README Signal",
            "",
            f"- README available: {'yes' if readme else 'no'}",
            f"- README length: {len(readme or '')} characters",
            f"- README flags: {', '.join(sorted(readme_flags)) or 'none detected'}",
            "",
            "## Investigation Notes",
            "",
        ]
        lines.extend(f"- {note}" for note in notes)
        lines.extend(
            [
                "",
                "## Next Step",
                "",
                (
                    "- Clone the repository and validate installation or MCP wiring "
                    "locally before promoting it."
                ),
                (
                    "- If the repo still looks strong after hands-on validation, keep "
                    "it in the inspection queue and move to the next link."
                ),
            ]
        )

        output_path.write_text("\n".join(lines), encoding="utf-8")
        return output_path


def _resolve_repo_ref(repo_ref: str) -> tuple[str, str]:
    """Resolve a GitHub URL or owner/repo slug into canonical values."""

    normalized = canonicalize_repo_url(repo_ref)
    if normalized:
        return normalized
    cleaned = repo_ref.strip().strip("/")
    if cleaned.count("/") == 1 and " " not in cleaned:
        repo_url = f"https://github.com/{cleaned}"
        return repo_url, cleaned
    raise OdisseoError(f"Unsupported repository reference: {repo_ref}")


def _parse_datetime(value: Any) -> datetime | None:
    """Parse cached ISO datetimes into Python objects."""

    if not isinstance(value, str) or not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _list_str(value: Any) -> list[str]:
    """Normalize a JSON-like value into a list of strings."""

    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


def _license_name(payload: dict[str, Any]) -> str:
    """Extract a human-readable license name from GitHub payloads."""

    license_payload = payload.get("license")
    if isinstance(license_payload, dict):
        name = license_payload.get("name")
        if isinstance(name, str):
            return name
    return "unknown"


def _detect_readme_flags(readme: str) -> set[str]:
    """Detect frontier keywords from the repository README."""

    lowered = readme.lower()
    flags: set[str] = set()
    keyword_map = {
        "memory": ("memory", "vector", "context", "recall"),
        "agents": ("agent", "agents", "orchestration", "swarm"),
        "protocols": ("mcp", "model context protocol", "hooks", "p2p", "gossip"),
        "voice_rag": ("voice", "speech", "audio", "rag", "retrieval"),
    }
    for label, keywords in keyword_map.items():
        if any(keyword in lowered for keyword in keywords):
            flags.add(label)
    return flags


def _build_investigation_notes(
    payload: dict[str, Any],
    record: RepoRecord,
    readme_flags: set[str],
) -> list[str]:
    """Build concise notes for one-by-one human inspection."""

    notes: list[str] = []
    if 5 <= record.stars <= 2000:
        notes.append(
            "This still looks like an early-stage or underexposed repository worth "
            "manual review."
        )
    if len(record.source_languages) >= 2:
        notes.append(
            "The repo was rediscovered across multiple languages, which is a "
            "stronger signal than a single-language mention."
        )
    if record.matched_topics:
        notes.append(
            f"It already matched the discovery themes: {', '.join(record.matched_topics)}."
        )
    if readme_flags:
        notes.append(
            f"The README reinforces the same themes: {', '.join(sorted(readme_flags))}."
        )
    if payload.get("archived"):
        notes.append(
            "The repository is archived, so treat it as inspiration rather than an "
            "actively maintained dependency."
        )
    if not notes:
        notes.append(
            "The repository metadata is valid, but the frontier signal is weaker and "
            "needs manual verification."
        )
    return notes
