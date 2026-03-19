"""Environment-aware configuration loading."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

from .exceptions import ConfigurationError
from .models import SearchLanguage

DEFAULT_SITE_URL = "https://ulissesflores.com"
DEFAULT_OUTPUT_FILE = "output/odisseo-signal-atlas-report.md"
DEFAULT_X_ENDPOINT = "https://api.x.com/2/tweets/search/recent"

DEFAULT_EXCLUDED_REPOS = {
    "ComposioHQ/awesome-claude-skills",
    "hesreallyhim/awesome-claude-code",
    "alirezarezvani/claude-skills",
    "VoltAgent/voltagent",
    "affaan-m/everything-claude-code",
    "anthropics/claude-code",
    "anthropics/skills",
    "obra/superpowers",
    "primeline-ai/evolving-lite",
    "rohitg00/claude-code-use-cases",
    "sickn33/antigravity",
}

DEFAULT_LANGUAGES = [
    SearchLanguage(
        "en",
        "English",
        ("Claude Code", "Claude MCP", "Claude agent", "MCP server"),
        ("memory", "multi-agent", "voice", "rag"),
    ),
    SearchLanguage(
        "pt",
        "Portuguese",
        ("Claude Code", "Claude MCP", "agente Claude", "memoria Claude"),
        ("memoria", "multiagente", "voz", "rag"),
    ),
    SearchLanguage(
        "es",
        "Spanish",
        ("Claude Code", "Claude MCP", "agente Claude", "memoria Claude"),
        ("memoria", "multiagente", "voz", "rag"),
    ),
    SearchLanguage(
        "it",
        "Italian",
        ("Claude Code", "Claude MCP", "agente Claude", "memoria Claude"),
        ("memoria", "multi-agent", "voce", "rag"),
    ),
    SearchLanguage(
        "ru",
        "Russian",
        ("Claude Code", "Claude MCP", "Claude agent", "MCP server"),
        ("pamiat", "multi-agent", "golos", "rag"),
    ),
    SearchLanguage(
        "ja",
        "Japanese",
        ("Claude Code", "Claude MCP", "Claude agent", "MCP server"),
        ("メモリ", "マルチエージェント", "音声", "RAG"),
    ),
    SearchLanguage(
        "zh",
        "Chinese",
        ("Claude Code", "Claude MCP", "Claude agent", "MCP server"),
        ("记忆", "多智能体", "语音", "RAG"),
    ),
    SearchLanguage(
        "ko",
        "Korean",
        ("Claude Code", "Claude MCP", "Claude agent", "MCP server"),
        ("메모리", "멀티에이전트", "음성", "RAG"),
    ),
    SearchLanguage(
        "fr",
        "French",
        ("Claude Code", "Claude MCP", "agent Claude", "memoire Claude"),
        ("memoire", "multi-agent", "voix", "rag"),
    ),
    SearchLanguage(
        "de",
        "German",
        ("Claude Code", "Claude MCP", "Claude Agent", "Claude Speicher"),
        ("speicher", "multi-agent", "sprache", "rag"),
    ),
    SearchLanguage(
        "ar",
        "Arabic",
        ("Claude Code", "Claude MCP", "Claude agent", "MCP server"),
        ("ذاكرة", "متعدد الوكلاء", "صوت", "RAG"),
    ),
    SearchLanguage(
        "he",
        "Hebrew",
        ("Claude Code", "Claude MCP", "סוכן Claude", "זיכרון Claude"),
        ("זיכרון", "רב-סוכנים", "קול", "RAG"),
    ),
    SearchLanguage(
        "tr",
        "Turkish",
        ("Claude Code", "Claude MCP", "Claude ajan", "Claude hafiza"),
        ("hafiza", "coklu ajan", "ses", "rag"),
    ),
    SearchLanguage(
        "id",
        "Indonesian",
        ("Claude Code", "Claude MCP", "agen Claude", "memori Claude"),
        ("memori", "multi-agen", "suara", "rag"),
    ),
]


@dataclass(slots=True)
class Settings:
    """Runtime settings loaded from environment files and process vars."""

    app_name: str
    environment: str
    project_root: Path
    cache_dir: Path
    output_dir: Path
    output_file: Path
    site_url: str
    x_bearer_token: str
    github_token: str | None
    x_search_endpoint: str
    x_max_results_per_page: int
    x_pages_per_query: int
    x_lookback_days: int
    x_window_hours: int
    x_refresh_live_window: bool
    target_repos: int
    query_history_file: Path
    query_history_retention_days: int
    excluded_repos: set[str]
    search_languages: list[SearchLanguage]


def load_settings(project_root: str | Path | None = None) -> Settings:
    """Load layered configuration for the current environment."""

    root = Path(project_root or Path.cwd()).resolve()
    environment = os.getenv("ODISSEO_ENV", "local")
    _load_env_file(root / ".env.local")
    _load_env_file(root / f".env.{environment}")
    _load_env_file(root / ".env")

    x_bearer_token = os.getenv("ODISSEO_X_BEARER_TOKEN", "").strip()
    if not x_bearer_token:
        raise ConfigurationError("ODISSEO_X_BEARER_TOKEN is required for discovery runs.")

    output_file = root / os.getenv("ODISSEO_OUTPUT_FILE", DEFAULT_OUTPUT_FILE)
    return Settings(
        app_name="Odisseo Signal Atlas",
        environment=os.getenv("ODISSEO_ENV", environment),
        project_root=root,
        cache_dir=root / "cache",
        output_dir=root / "output",
        output_file=output_file,
        site_url=os.getenv("ODISSEO_SITE_URL", DEFAULT_SITE_URL),
        x_bearer_token=x_bearer_token,
        github_token=os.getenv("ODISSEO_GITHUB_TOKEN") or None,
        x_search_endpoint=os.getenv(
            "ODISSEO_X_SEARCH_ENDPOINT",
            DEFAULT_X_ENDPOINT,
        ),
        x_max_results_per_page=int(os.getenv("ODISSEO_X_MAX_RESULTS_PER_PAGE", "100")),
        x_pages_per_query=int(os.getenv("ODISSEO_X_PAGES_PER_QUERY", "5")),
        x_lookback_days=int(os.getenv("ODISSEO_X_LOOKBACK_DAYS", "3")),
        x_window_hours=int(os.getenv("ODISSEO_X_WINDOW_HOURS", "12")),
        x_refresh_live_window=_env_bool("ODISSEO_X_REFRESH_LIVE_WINDOW", default=True),
        target_repos=int(os.getenv("ODISSEO_TARGET_REPOS", "500")),
        query_history_file=root / os.getenv(
            "ODISSEO_QUERY_HISTORY_FILE",
            "cache/query_history.json",
        ),
        query_history_retention_days=int(
            os.getenv("ODISSEO_QUERY_HISTORY_RETENTION_DAYS", "30")
        ),
        excluded_repos=set(DEFAULT_EXCLUDED_REPOS),
        search_languages=list(DEFAULT_LANGUAGES),
    )


def _load_env_file(path: Path) -> None:
    """Load an environment file if it exists."""

    if path.exists():
        load_dotenv(path, override=False)


def _env_bool(name: str, default: bool) -> bool:
    """Parse boolean environment variables using common truthy values."""

    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}
