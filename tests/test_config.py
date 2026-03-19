from pathlib import Path

import pytest

from odisseo_signal_atlas.config import load_settings
from odisseo_signal_atlas.exceptions import ConfigurationError


def test_load_settings_honors_environment_layering(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    (tmp_path / ".env").write_text("ODISSEO_X_BEARER_TOKEN=base-token\n", encoding="utf-8")
    (tmp_path / ".env.local").write_text(
        "ODISSEO_X_BEARER_TOKEN=local-token\nODISSEO_TARGET_REPOS=42\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("ODISSEO_ENV", "local")

    settings = load_settings(tmp_path)

    assert settings.x_bearer_token == "local-token"
    assert settings.target_repos == 42
    assert settings.output_file == Path(tmp_path) / "output/odisseo-signal-atlas-report.md"
    assert settings.repo_insights_dir == Path(tmp_path) / "output/repo-insights"
    assert settings.query_history_file == Path(tmp_path) / "cache/query_history.json"
    assert settings.inspection_state_file == Path(tmp_path) / "cache/inspection_state.json"
    assert settings.x_min_request_interval_seconds == 0.25
    assert settings.x_max_backfill_days == 3
    assert settings.x_rate_limit_default_wait_seconds == 60
    assert settings.x_rate_limit_max_wait_seconds == 900
    assert settings.candidate_target_multiplier == 1.15


def test_load_settings_requires_x_bearer_token(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ODISSEO_ENV", "local")
    monkeypatch.delenv("ODISSEO_X_BEARER_TOKEN", raising=False)

    with pytest.raises(ConfigurationError, match="ODISSEO_X_BEARER_TOKEN"):
        load_settings(tmp_path)


def test_process_environment_overrides_env_files(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    (tmp_path / ".env").write_text("ODISSEO_X_BEARER_TOKEN=file-token\n", encoding="utf-8")
    (tmp_path / ".env.local").write_text(
        "ODISSEO_X_BEARER_TOKEN=local-file-token\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("ODISSEO_ENV", "local")
    monkeypatch.setenv("ODISSEO_X_BEARER_TOKEN", "process-token")

    settings = load_settings(tmp_path)

    assert settings.x_bearer_token == "process-token"


def test_load_settings_allows_inspection_mode_without_x_bearer(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ODISSEO_ENV", "local")
    monkeypatch.delenv("ODISSEO_X_BEARER_TOKEN", raising=False)

    settings = load_settings(tmp_path, require_x_bearer=False)

    assert settings.x_bearer_token == ""


def test_language_matrix_includes_hebrew_and_x_native_dev_communities(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    (tmp_path / ".env").write_text("ODISSEO_X_BEARER_TOKEN=base-token\n", encoding="utf-8")
    monkeypatch.setenv("ODISSEO_ENV", "local")

    settings = load_settings(tmp_path)
    codes = {language.code for language in settings.search_languages}

    assert {"he", "tr", "id"}.issubset(codes)
