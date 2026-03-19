"""Command-line interface for local execution."""

from __future__ import annotations

import argparse
from pathlib import Path

from .config import load_settings
from .logging_utils import configure_logging
from .pipeline import OdisseoSignalAtlasPipeline


def main() -> None:
    """CLI entrypoint."""

    parser = _build_parser()
    args = parser.parse_args()
    configure_logging(args.log_level)
    if args.command == "smoke":
        _run_smoke(args)
        return
    _run_discovery(args)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run Odisseo Signal Atlas locally.")
    parser.add_argument("--log-level", default="INFO", help="Logging level.")
    subparsers = parser.add_subparsers(dest="command", required=False)

    run_parser = subparsers.add_parser("run", help="Run the full discovery pipeline.")
    _add_common_arguments(run_parser)

    smoke_parser = subparsers.add_parser("smoke", help="Run a constrained smoke execution.")
    _add_common_arguments(smoke_parser)

    parser.set_defaults(command="run")
    return parser


def _add_common_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--target",
        type=int,
        default=None,
        help="Maximum number of repositories to export.",
    )
    parser.add_argument(
        "--languages",
        type=str,
        default="",
        help="Comma-separated language list, for example en,pt,es,it,ru,ja.",
    )
    parser.add_argument(
        "--project-root",
        type=Path,
        default=Path(__file__).resolve().parents[2],
        help="Project root directory.",
    )


def _run_discovery(args: argparse.Namespace) -> None:
    settings = load_settings(args.project_root)
    pipeline = OdisseoSignalAtlasPipeline(settings)
    try:
        _apply_language_filter(pipeline, args.languages)
        report = pipeline.run(target_repos=args.target)
    finally:
        pipeline.close()

    print(f"Output file: {report.output_path}")
    print(f"Queries planned: {report.total_planned_queries}")
    print(f"Queries executed: {report.total_queries}")
    print(f"Queries skipped from history: {report.total_skipped_queries}")
    print(f"Tweets analyzed: {report.total_tweets}")
    print(f"Candidates discovered: {report.total_candidates}")
    print(f"Repositories exported: {report.total_ranked}")
    print(f"Canonical site: {report.site_url}")


def _run_smoke(args: argparse.Namespace) -> None:
    settings = load_settings(args.project_root)
    settings.x_max_results_per_page = min(settings.x_max_results_per_page, 10)
    settings.x_pages_per_query = min(settings.x_pages_per_query, 1)
    settings.output_file = settings.project_root / "output" / "odisseo-signal-atlas.smoke.md"

    pipeline = OdisseoSignalAtlasPipeline(settings)
    try:
        _apply_language_filter(pipeline, args.languages or "en,pt,es")
        report = pipeline.run(target_repos=args.target or 10)
    finally:
        pipeline.close()

    print(f"Smoke output file: {report.output_path}")
    print(f"Queries planned: {report.total_planned_queries}")
    print(f"Queries skipped from history: {report.total_skipped_queries}")
    print(f"Tweets analyzed: {report.total_tweets}")
    print(f"Repositories exported: {report.total_ranked}")


def _apply_language_filter(pipeline: OdisseoSignalAtlasPipeline, languages: str) -> None:
    if not languages:
        return
    wanted = {item.strip() for item in languages.split(",") if item.strip()}
    pipeline.settings.search_languages = [
        language for language in pipeline.settings.search_languages if language.code in wanted
    ]
