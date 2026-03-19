# Architecture

`Odisseo Signal Atlas` is a local-first discovery engine with five layers:

1. Configuration loading and environment layering
2. Query generation across multiple languages and frontier topics
3. External discovery clients for X and GitHub
4. Normalization, ranking, and report assembly
5. Export and cache persistence
6. CLI execution and reproducible release gates

## Runtime flow

1. Load settings from `.env` files and process environment.
2. Build multilingual X queries from seed terms and topic presets.
3. Search the X API and collect tweet entities and expanded URLs.
4. Normalize GitHub links into canonical repository slugs.
5. Enrich each slug with GitHub metadata.
6. Apply exclusion rules and quality scoring.
7. Persist cache artifacts and export a Markdown report.
8. Surface the result through a local CLI and CI-safe automation.

## Design constraints

- local-first
- public-repo quality
- deterministic report format
- explicit environment boundaries
- no secrets in versioned files
- CLI-first runtime surface
