# Release Policy

## Versioning

Use semantic versioning for SchoolMemoryLocalAI releases.

Examples:

- `1.0.0` — first production release.
- `1.0.1` — packaging, metadata or compatible model correction.
- `1.1.0` — compatible upstream model/runtime improvement.
- `2.0.0` — breaking host-contract change.

## Immutability

Published release assets must never be replaced.

If any byte changes, publish a new version and new hash.

## Promotion

Recommended lifecycle:

`candidate -> recommended -> superseded`

Use `withdrawn` when a release should no longer be offered.

## Release gate

Before promotion to `recommended`:

1. public-safety scan passes;
2. package SHA-256 is recorded;
3. upstream weight SHA-256 is verified;
4. licence/provenance is checked;
5. generic smoke tests pass;
6. compatibility metadata is complete;
7. no private host artefacts are present.

Product-specific quality evaluation belongs outside this public repository.
