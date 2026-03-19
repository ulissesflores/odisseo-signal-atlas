# ADR 0005: Time-sliced query history for X discovery

## Status

Accepted

## Context

`Odisseo Signal Atlas` needs to search X across many languages and topics without wasting API quota on the same historical slices every time the pipeline runs. A naive loop over language and topic terms replays identical searches and produces avoidable duplicates.

## Decision

The pipeline uses explicit recent-search windows plus a persistent query-history cache:

- each concrete query is paired with a UTC window
- completed query windows are recorded in `cache/query_history.json`
- historical windows already seen are skipped on later runs
- the newest live window can still be refreshed to catch recent activity

## Consequences

- X API usage becomes more efficient and predictable
- local reruns avoid redundant backfills
- multilingual runs can scale without starting from zero each time
- the cache becomes part of operational observability and should not be committed
