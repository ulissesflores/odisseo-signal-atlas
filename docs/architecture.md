# Architecture

`Odisseo Signal Atlas` is a local-first discovery engine with five layers:

1. Configuration loading and environment layering
2. Query generation across multiple languages and frontier topics
3. Time-sliced query planning and persistent query history
4. Rate-limit-aware external discovery clients for X and GitHub
5. Normalization, ranking, and report assembly
6. Incremental cache persistence, resumable candidates, and observability
7. CLI execution and reproducible release gates

## Runtime flow

1. Load settings from `.env` files and process environment.
2. Build multilingual X queries from seed terms, topic presets, and recent-search windows.
3. Skip historical query slices already recorded in the local query-history cache.
4. Search the X API, pace requests, and wait for reset windows when X returns `429`.
5. Normalize GitHub links into canonical repository slugs.
6. Enrich each slug with GitHub metadata.
7. Apply exclusion rules and quality scoring.
8. Persist query history and candidate cache after each completed query so interrupted runs can resume.
9. Surface the result through a local CLI and CI-safe automation.

## Design constraints

- local-first
- public-repo quality
- deterministic report format
- explicit environment boundaries
- no secrets in versioned files
- CLI-first runtime surface
- query windows must be replay-safe
- long-running executions must survive rate-limit interruptions
