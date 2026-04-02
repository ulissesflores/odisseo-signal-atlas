# Odisseo Signal Atlas

[![CI](https://github.com/ulissesflores/odisseo-signal-atlas/actions/workflows/ci.yml/badge.svg)](https://github.com/ulissesflores/odisseo-signal-atlas/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](pyproject.toml)

`Odisseo Signal Atlas` is a local-first discovery engine for finding frontier GitHub repositories from real social signals.

It searches recent windows on the `X` API, extracts GitHub repositories mentioned in those conversations, enriches them with GitHub metadata, ranks them against frontier-engineering heuristics, and exports reproducible Markdown reports for curation and follow-up review.

The pipeline is built for long-running multilingual discovery: it tracks which recent-search windows have already been scanned, persists candidate state incrementally, survives `429` rate-limit pauses, and supports a sequential human-review workflow over the ranked cache without issuing new `X` requests.

## At a glance

- Product: `Odisseo Signal Atlas`
- Brand: `Odisseo`
- Site: [ulissesflores.com](https://ulissesflores.com)
- Runtime surface: local-first Python CLI
- Package status: `0.1.0` alpha
- Primary outputs:
  - `output/odisseo-signal-atlas-report.md`
  - `output/repo-insights/`
- Core commands:
  - `run`
  - `smoke`
  - `inspect`
  - `inspect-next`

## What it does

- Builds multilingual search queries across engineering and OSS topics
- Scans recent `X` windows while avoiding already searched slices via `cache/query_history.json`
- Normalizes GitHub links into canonical repository slugs
- Enriches repositories with GitHub metadata and heuristic scoring
- Writes a public-quality Markdown report for every run
- Persists candidate and inspection state so long executions can resume

## Why this repository exists

Most discovery workflows for frontier tooling are either ad hoc social browsing or brittle one-shot scripts. Odisseo Signal Atlas is meant to be the middle ground: a repeatable local workflow that can keep backfilling recent signal windows, produce traceable reports, and turn raw social chatter into a ranked repository shortlist.

It is intentionally structured like a maintained software product rather than a throwaway notebook. Source code, tests, ADRs, CI, security guidance, and release metadata all live here because the repository is part of the deliverable.

## Quick start

```bash
cp .env.example .env
cp .env.local.example .env.local
make install-dev
```

Populate secrets locally:

- `ODISSEO_X_BEARER_TOKEN`
- `ODISSEO_GITHUB_TOKEN` for sustained enrichment runs

Run a constrained smoke pass first:

```bash
ODISSEO_X_BEARER_TOKEN="..." \
ODISSEO_GITHUB_TOKEN="$(gh auth token)" \
.venv/bin/python scripts/run_hunt.py smoke --target 10 --languages en,pt,es
```

Then run a larger multilingual discovery:

```bash
ODISSEO_X_BEARER_TOKEN="..." \
ODISSEO_GITHUB_TOKEN="$(gh auth token)" \
.venv/bin/python scripts/run_hunt.py run \
  --target 500 \
  --languages en,pt,es,it,ru,ja,zh,ko,fr,de,ar,he,tr,id
```

Continue review without calling the `X` API again:

```bash
.venv/bin/python scripts/run_hunt.py inspect-next
.venv/bin/python scripts/run_hunt.py inspect --repo https://github.com/owner/repo
```

Those inspection commands read the ranked cache plus GitHub metadata only. They are useful while waiting for the next `X` rate-limit reset window.

## Pipeline

1. Load layered configuration from environment files and process environment
2. Generate multilingual recent-search queries over tooling and engineering topics
3. Walk backward through recent windows until the target or backfill ceiling is reached
4. Skip windows already recorded in `cache/query_history.json`
5. Extract GitHub links from `X`, normalize repository slugs, and enrich metadata from GitHub
6. Rank candidates and export a Markdown report
7. Persist candidate and inspection state for resumable discovery and sequential review

## Outputs

- `output/odisseo-signal-atlas-report.md`: main discovery report for each run
- `output/repo-insights/`: one Markdown analysis per manually reviewed repository
- `cache/query_history.json`: replay-safe history of scanned search windows
- `cache/candidates.json`: incremental repository candidate cache
- `cache/inspection_state.json`: state for `inspect-next`

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
- `ODISSEO_INSPECTION_STATE_FILE`
- `ODISSEO_REPO_INSIGHTS_DIR`
- `ODISSEO_QUERY_HISTORY_RETENTION_DAYS`

If a run does not find enough repositories within the first recent-search slice, the pipeline keeps moving backward in time until it reaches the configured backfill limit. Every run writes a Markdown file, including progress or failure snapshots when final enrichment has not completed yet.

## Language strategy

The default language matrix mixes globally relevant developer languages with communities that are especially active on `X` for tooling, OSS, and AI engineering discourse. That is why the defaults include Japanese, Brazilian Portuguese, Hebrew, Turkish, and Indonesian alongside English-centric search terms.

## Engineering and maintenance

- Environment layering: `.env`, `.env.local`, `.env.production`
- Local-first execution with no notebook dependency
- Automated tests, lint, and type-check gates
- ADRs and architecture documentation
- Security guidance for public operation
- Public metadata and release hygiene

Common local commands:

```bash
make lint
make test
make typecheck
make smoke
make run
```

## Repository layout

```text
src/odisseo_signal_atlas/   application package
tests/                      regression and integration-style tests
scripts/                    local launchers
docs/adr/                   architecture decisions
.github/                    CI, templates, repository governance
```

## Documentation

- [Architecture](docs/architecture.md)
- [ADR 0001](docs/adr/0001-core-architecture.md)
- [ADR 0002](docs/adr/0002-environment-and-secrets.md)
- [ADR 0003](docs/adr/0003-public-branding-and-canonical-links.md)
- [ADR 0004](docs/adr/0004-cli-first-local-execution.md)
- [ADR 0005](docs/adr/0005-time-sliced-query-history.md)
- [ADR 0006](docs/adr/0006-sequential-repo-inspection.md)
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
