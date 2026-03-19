# Odisseo Signal Atlas

[![CI](https://github.com/ulissesflores/odisseo-signal-atlas/actions/workflows/ci.yml/badge.svg)](https://github.com/ulissesflores/odisseo-signal-atlas/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](pyproject.toml)

Official engineering repository for the `Odisseo Signal Atlas` discovery engine by [Ulisses Flores](https://ulissesflores.com).

Odisseo Signal Atlas is a multilingual discovery pipeline that searches the `X` API, extracts GitHub repositories from real social signals, enriches them with GitHub metadata, scores them against frontier engineering criteria, and exports a public-quality Markdown report.

It is designed to backfill recent search windows without pointlessly repeating the same historical queries on every run. It also persists resumable candidate state, writes a Markdown report for every run, and respects X rate-limit windows instead of discarding a long execution when the API asks for a cooldown.

## Public positioning

- Brand: `Odisseo`
- Product: `Odisseo Signal Atlas`
- Site: [ulissesflores.com](https://ulissesflores.com)
- Distribution goal: SEO, GEO, and LLM-friendly public repository
- Operating model: local-first, environment-driven, reproducible, testable
- Delivery surface: CLI-first, no notebook dependency

## What This Repository Is

This repository is intentionally structured like a public software product, not a throwaway script. That means source code, tests, docs, ADRs, CI, security policy, templates, and release metadata all live here on purpose.

Tracked public files stay relatively small. Local-only artifacts such as `.venv`, cache files, `.env.local`, smoke outputs, and editor cruft are ignored and are not part of the public repository surface.

## Scope

- Multilingual query generation for `en`, `pt`, `es`, `it`, `ru`, `ja`, `zh`, `ko`, `fr`, `de`, `ar`, `he`, `tr`, and `id`
- Real X API discovery
- GitHub repository normalization and enrichment
- Heuristic ranking for hidden gems, experimental repos, MCP servers, memory systems, multi-agent stacks, and adjacent frontier tooling
- Time-sliced recent-search execution with persistent query history
- Markdown export with canonical site link back to [Ulisses Flores](https://ulissesflores.com)

## Engineering standards

- Environment layering: `.env`, `.env.local`, `.env.production`
- Local-first execution
- Automated tests
- Static quality gates
- ADRs and architecture documentation
- Security guidance for public operation
- Changelog and contribution flow
- Public metadata and licensing for open distribution

## Quick start

```bash
cp .env.example .env
cp .env.local.example .env.local
make install-dev
```

Populate secrets locally:

- `ODISSEO_X_BEARER_TOKEN`
- `ODISSEO_GITHUB_TOKEN` for sustained enrichment runs

## Language strategy

The default language matrix mixes globally relevant developer languages with communities that are especially active on X for tooling, OSS, and AI engineering discourse. That is why the defaults include Japanese, Brazilian Portuguese, Hebrew, Turkish, and Indonesian in addition to the usual English-centric set.

## Runtime surfaces

- `requirements.txt`: production dependencies
- `requirements-dev.txt`: local engineering stack
- `pyproject.toml`: package metadata, tooling, coverage gate, CLI entrypoint
- `Makefile`: deterministic local commands
- `scripts/run_hunt.py`: thin local launcher
- `src/odisseo_signal_atlas/`: core product code
- `tests/`: automated regression suite
- `docs/adr/`: architectural decisions for public maintenance

## Repository layout

```text
src/odisseo_signal_atlas/   application package
tests/                      regression and integration-style tests
scripts/                    local launchers
docs/adr/                   architecture decisions
.github/                    CI, templates, repository governance
```

## Local execution model

Notebook-based execution is intentionally out of scope. The repository is designed for:

- local CLI execution
- explicit environment files
- reproducible CI runs
- versioned software engineering artifacts
- public release hygiene

## Commands

```bash
make lint
make test
make typecheck
make smoke
make run
```

Or directly:

```bash
.venv/bin/python scripts/run_hunt.py --target 500 --languages en,pt,es,it,ru,ja,zh,ko,fr,de,ar
```

For a serious multilingual run with local GitHub auth:

```bash
ODISSEO_GITHUB_TOKEN="$(gh auth token)" \
.venv/bin/python scripts/run_hunt.py run \
  --target 500 \
  --languages en,pt,es,it,ru,ja,zh,ko,fr,de,ar,he,tr,id
```

## Configuration

The project reads environment in this order:

1. Process environment variables
2. `.env.local`
3. `.env.<environment>`
4. `.env`

`ODISSEO_ENV` defaults to `local`.

See:

- [.env.example](.env.example)
- [.env.local.example](.env.local.example)
- [.env.production.example](.env.production.example)

Recommended local setup:

```bash
cp .env.example .env
cp .env.local.example .env.local
```

Keep real tokens only in ignored local files.

Recent-search control is configured with:

- `ODISSEO_X_LOOKBACK_DAYS`
- `ODISSEO_X_MAX_BACKFILL_DAYS`
- `ODISSEO_X_WINDOW_HOURS`
- `ODISSEO_X_REFRESH_LIVE_WINDOW`
- `ODISSEO_X_MIN_REQUEST_INTERVAL_SECONDS`
- `ODISSEO_X_RATE_LIMIT_DEFAULT_WAIT_SECONDS`
- `ODISSEO_X_RATE_LIMIT_MAX_WAIT_SECONDS`
- `ODISSEO_CANDIDATE_TARGET_MULTIPLIER`
- `ODISSEO_QUERY_HISTORY_FILE`
- `ODISSEO_QUERY_HISTORY_RETENTION_DAYS`

The pipeline stores executed query windows in `cache/query_history.json` so older slices are skipped on subsequent runs while the newest live window can still be refreshed.

Discovered candidates are also persisted incrementally in `cache/candidates.json`. That allows an interrupted or rate-limited run to resume without losing already discovered repository signals.

If a run does not find enough repositories within the first recent-search slice, the pipeline keeps moving backward in time until it reaches the configured backfill limit. Every run writes a Markdown file, including progress or failure snapshots when final enrichment has not completed yet.

Backfill semantics are strict:

- every run starts from the current UTC anchor and moves backward
- if a time window is already present in `cache/query_history.json`, that window is skipped
- skipped windows still advance the cursor, so the pipeline keeps walking backward instead of looping on already searched days

## Documentation

- [Architecture](docs/architecture.md)
- [ADR 0001](docs/adr/0001-core-architecture.md)
- [ADR 0002](docs/adr/0002-environment-and-secrets.md)
- [ADR 0003](docs/adr/0003-public-branding-and-canonical-links.md)
- [ADR 0004](docs/adr/0004-cli-first-local-execution.md)
- [Security](SECURITY.md)
- [Contributing](CONTRIBUTING.md)
- [Changelog](CHANGELOG.md)
- [License](LICENSE)

## Current quality bar

The repository is considered acceptable only when:

- tests pass
- lint passes
- typecheck passes
- smoke run succeeds
- generated Markdown contains canonical backlink to [Ulisses Flores](https://ulissesflores.com)
- CI enforces the same gates
