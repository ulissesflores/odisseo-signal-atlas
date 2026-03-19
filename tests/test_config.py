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
