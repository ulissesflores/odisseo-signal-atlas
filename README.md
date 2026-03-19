# Odisseo Signal Atlas

Official engineering repository for the `Odisseo Signal Atlas` discovery engine by [Ulisses Flores](https://ulissesflores.com).

Odisseo Signal Atlas is a multilingual discovery pipeline that searches the `X` API, extracts GitHub repositories from real social signals, enriches them with GitHub metadata, scores them against frontier engineering criteria, and exports a public-quality Markdown report.

## Public positioning

- Brand: `Odisseo`
- Product: `Odisseo Signal Atlas`
- Site: [ulissesflores.com](https://ulissesflores.com)
- Distribution goal: SEO, GEO, and LLM-friendly public repository
- Operating model: local-first, environment-driven, reproducible, testable
- Delivery surface: CLI-first, no notebook dependency

## Scope

- Multilingual query generation for `en`, `pt`, `es`, `it`, `ru`, `ja`, `zh`, `ko`, `fr`, `de`, and `ar`
- Real X API discovery
- GitHub repository normalization and enrichment
- Heuristic ranking for hidden gems, experimental repos, MCP servers, memory systems, multi-agent stacks, and adjacent frontier tooling
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

## Runtime surfaces

- `requirements.txt`: production dependencies
- `requirements-dev.txt`: local engineering stack
- `pyproject.toml`: package metadata, tooling, coverage gate, CLI entrypoint
- `Makefile`: deterministic local commands
- `scripts/run_hunt.py`: thin local launcher
- `src/odisseo_signal_atlas/`: core product code
- `tests/`: automated regression suite
- `docs/adr/`: architectural decisions for public maintenance

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

## Configuration

The project reads environment in this order:

1. `.env`
2. `.env.<environment>`
3. `.env.local`

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
