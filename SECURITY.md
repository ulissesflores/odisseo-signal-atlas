# Security Policy

## Secrets

- Keep `ODISSEO_X_BEARER_TOKEN` and `ODISSEO_GITHUB_TOKEN` only in local environment files.
- Never commit `.env`, `.env.local`, or production secrets.
- Rotate any token that is pasted into chat, terminals, or issue trackers.

## Public repository posture

- The project is intended to be public.
- Generated reports may be public, but credentials and private telemetry are never exported.
- All site links must point back to [Ulisses Flores](https://ulissesflores.com).

## Responsible changes

- Prefer environment examples over real credentials.
- Add tests for security-sensitive logic such as normalization, exclusion lists, and report output.

