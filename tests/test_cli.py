from __future__ import annotations

import sys
from argparse import Namespace
from pathlib import Path
from typing import ClassVar

import pytest

from odisseo_signal_atlas import cli
from odisseo_signal_atlas.config import Settings
from odisseo_signal_atlas.models import (
    PipelineReport,
    RepoInspectionReport,
    SearchLanguage,
)


def _settings(tmp_path: Path) -> Settings:
    return Settings(
        app_name="Odisseo Signal Atlas",
        environment="test",
        project_root=tmp_path,
        cache_dir=tmp_path / "cache",
        output_dir=tmp_path / "output",
        output_file=tmp_path / "output" / "report.md",
        repo_insights_dir=tmp_path / "output" / "repo-insights",
        site_url="https://ulissesflores.com",
        x_bearer_token="token",
        github_token=None,
        x_search_endpoint="https://api.x.com/2/tweets/search/recent",
        x_max_results_per_page=100,
        x_pages_per_query=5,
        x_min_request_interval_seconds=0.0,
        x_lookback_days=1,
        x_max_backfill_days=1,
        x_window_hours=12,
        x_refresh_live_window=True,
        x_rate_limit_default_wait_seconds=60,
        x_rate_limit_max_wait_seconds=900,
        target_repos=500,
        candidate_target_multiplier=1.15,
        query_history_file=tmp_path / "cache" / "query_history.json",
        inspection_state_file=tmp_path / "cache" / "inspection_state.json",
        query_history_retention_days=30,
        excluded_repos=set(),
        search_languages=[
            SearchLanguage("en", "English", ("Claude Code",), ("memory",)),
            SearchLanguage("pt", "Portuguese", ("Claude Code",), ("memoria",)),
        ],
    )


class DummyPipeline:
    instances: ClassVar[list[DummyPipeline]] = []

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.closed = False
        self.run_target: int | None = None
        self.__class__.instances.append(self)

    def run(self, target_repos: int | None = None) -> PipelineReport:
        self.run_target = target_repos
        return PipelineReport(
            output_path=str(self.settings.output_file),
            total_planned_queries=3,
            total_queries=3,
            total_skipped_queries=0,
            total_tweets=5,
            total_candidates=4,
            total_ranked=2,
            days_scanned=1,
            target_reached=False,
            site_url=self.settings.site_url,
        )

    def close(self) -> None:
        self.closed = True


class DummyInspector:
    instances: ClassVar[list[DummyInspector]] = []

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.closed = False
        self.inspected_repo: str | None = None
        self.__class__.instances.append(self)

    def inspect_repo(self, repo: str) -> RepoInspectionReport:
        self.inspected_repo = repo
        return RepoInspectionReport(
            repo_slug="acme/direct",
            output_path=str(self.settings.repo_insights_dir / "acme--direct.md"),
            source_cache="direct",
            remaining_candidates=7,
        )

    def inspect_next(self) -> RepoInspectionReport:
        return RepoInspectionReport(
            repo_slug="acme/next",
            output_path=str(self.settings.repo_insights_dir / "acme--next.md"),
            source_cache="ranked",
            remaining_candidates=6,
        )

    def close(self) -> None:
        self.closed = True


def test_main_routes_to_default_run_and_smoke(monkeypatch: pytest.MonkeyPatch) -> None:
    events: list[tuple[str, str]] = []
    monkeypatch.setattr(cli, "configure_logging", lambda level: events.append(("log", level)))
    monkeypatch.setattr(cli, "_run_discovery", lambda args: events.append(("run", args.command)))
    monkeypatch.setattr(cli, "_run_smoke", lambda args: events.append(("smoke", args.command)))
    monkeypatch.setattr(cli, "_run_inspect", lambda args: events.append(("inspect", args.command)))
    monkeypatch.setattr(
        cli,
        "_run_inspect_next",
        lambda args: events.append(("inspect-next", args.command)),
    )

    monkeypatch.setattr(sys, "argv", ["odisseo-atlas"])
    cli.main()
    monkeypatch.setattr(sys, "argv", ["odisseo-atlas", "smoke"])
    cli.main()
    monkeypatch.setattr(sys, "argv", ["odisseo-atlas", "inspect", "--repo", "acme/repo"])
    cli.main()
    monkeypatch.setattr(sys, "argv", ["odisseo-atlas", "inspect-next"])
    cli.main()

    assert ("run", "run") in events
    assert ("smoke", "smoke") in events
    assert ("inspect", "inspect") in events
    assert ("inspect-next", "inspect-next") in events


def test_run_discovery_filters_languages_and_prints_report(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    settings = _settings(tmp_path)
    DummyPipeline.instances.clear()
    monkeypatch.setattr(cli, "load_settings", lambda project_root: settings)
    monkeypatch.setattr(cli, "OdisseoSignalAtlasPipeline", DummyPipeline)

    args = Namespace(target=7, languages="en", project_root=tmp_path)
    cli._run_discovery(args)

    captured = capsys.readouterr()
    pipeline = DummyPipeline.instances[-1]
    assert pipeline.run_target == 7
    assert pipeline.closed is True
    assert [language.code for language in pipeline.settings.search_languages] == ["en"]
    assert "Repositories exported: 2" in captured.out


def test_run_smoke_constrains_runtime_and_output_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    settings = _settings(tmp_path)
    DummyPipeline.instances.clear()
    monkeypatch.setattr(cli, "load_settings", lambda project_root: settings)
    monkeypatch.setattr(cli, "OdisseoSignalAtlasPipeline", DummyPipeline)

    args = Namespace(target=None, languages="en,pt", project_root=tmp_path)
    cli._run_smoke(args)

    captured = capsys.readouterr()
    pipeline = DummyPipeline.instances[-1]
    assert pipeline.run_target == 10
    assert pipeline.closed is True
    assert pipeline.settings.x_max_results_per_page == 10
    assert pipeline.settings.x_pages_per_query == 1
    assert pipeline.settings.output_file.name == "odisseo-signal-atlas.smoke.md"
    assert "Smoke output file:" in captured.out


def test_run_inspect_uses_repo_inspector_without_x_requirements(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    settings = _settings(tmp_path)
    DummyInspector.instances.clear()
    monkeypatch.setattr(
        cli,
        "load_settings",
        lambda project_root, require_x_bearer=True: settings,
    )
    monkeypatch.setattr(cli, "RepoInspector", DummyInspector)

    args = Namespace(repo="https://github.com/acme/direct", project_root=tmp_path)
    cli._run_inspect(args)

    captured = capsys.readouterr()
    inspector = DummyInspector.instances[-1]
    assert inspector.inspected_repo == "https://github.com/acme/direct"
    assert inspector.closed is True
    assert "Inspection file:" in captured.out
    assert "Remaining ranked candidates: 7" in captured.out


def test_run_inspect_next_uses_ranked_cache_flow(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    settings = _settings(tmp_path)
    DummyInspector.instances.clear()
    monkeypatch.setattr(
        cli,
        "load_settings",
        lambda project_root, require_x_bearer=True: settings,
    )
    monkeypatch.setattr(cli, "RepoInspector", DummyInspector)

    args = Namespace(project_root=tmp_path)
    cli._run_inspect_next(args)

    captured = capsys.readouterr()
    inspector = DummyInspector.instances[-1]
    assert inspector.closed is True
    assert "Repository: acme/next" in captured.out
    assert "Source cache: ranked" in captured.out
