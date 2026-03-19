# ADR 0006: Sequential Repository Inspection

- Status: accepted
- Date: 2026-03-19

## Context

The primary discovery pipeline depends on the X recent-search API. That API is rate-limited by request windows, and a long multilingual run can hit a cooldown before final enrichment is complete.

When that happens, the operator still needs a productive workflow instead of waiting idly for the next reset window. The repository therefore needs a second operating mode that does not require new X queries and still produces useful output.

## Decision

Add a sequential inspection workflow that reads the ranked cache, picks one repository at a time, enriches it with current GitHub metadata, and writes a dedicated Markdown analysis under `output/repo-insights/`.

The workflow persists its own state in `cache/inspection_state.json` so that each subsequent command can move to the next unseen repository.

Two CLI commands expose the workflow:

- `inspect-next`: inspect the next unseen ranked repository
- `inspect --repo <owner/repo-or-url>`: inspect a specific repository directly

Inspection mode is allowed to load configuration without an X bearer token because it never calls the X API.

## Consequences

### Positive

- Human review can continue while the X API is cooling down
- The repository gains a deterministic one-by-one validation workflow
- Per-repo Markdown artifacts become reusable research notes for future curation

### Negative

- The codebase must maintain a second output surface and state file
- Inspection state can become stale if ranked caches are deleted or manually edited

## Follow-up

- Consider adding clone-and-validate hooks for shortlisted repositories
- Consider adding issue templates for promoting or rejecting inspected repositories
