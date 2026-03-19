# ADR 0001: Core Architecture

## Status

Accepted

## Context

The repository must be public, local-first, and suitable for sustained discovery runs against external APIs. The previous prototype mixed notebook concerns, weak documentation, and insufficient software engineering standards.

## Decision

Adopt a package-first architecture with:

- explicit settings
- thin CLI
- separate clients for X and GitHub
- deterministic normalization and ranking
- Markdown export as a dedicated concern

## Consequences

- easier testing
- cleaner public surface
- simpler future CI and packaging

