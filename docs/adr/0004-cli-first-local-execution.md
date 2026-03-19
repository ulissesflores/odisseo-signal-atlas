# ADR 0004: CLI-first local execution

## Status

Accepted

## Context

`Odisseo Signal Atlas` is intended to be a public engineering repository, not an exploratory notebook dump. Notebook-first delivery weakens reproducibility, increases hidden state, and makes release discipline harder to enforce.

## Decision

The project adopts a CLI-first operating model:

- local execution is done through `scripts/run_hunt.py` or `odisseo-atlas`
- environment is loaded from explicit `.env` files
- smoke runs are reproducible from the command line
- notebooks are not part of the supported runtime surface

## Consequences

- CI can validate the same commands used locally
- documentation stays aligned with production usage
- contributors have fewer hidden execution paths
- the public repository presents a cleaner software engineering posture
