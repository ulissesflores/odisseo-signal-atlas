# ADR 0002: Environment and Secrets

## Status

Accepted

## Context

The project needs local, staging-like, and production-like settings without ever committing secrets.

## Decision

Use layered environment files:

- `.env`
- `.env.<environment>`
- `.env.local`

Environment examples are versioned. Real credentials remain local only.

## Consequences

- reproducible local development
- safer public repository posture
- cleaner separation between public defaults and private credentials

