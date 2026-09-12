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

## Candidate build and GitHub Release

Use the manually dispatched **Full model candidate verification** workflow or follow the commands in `README.md`. The workflow acquires the exact commit, verifies the frozen weight, builds and independently validates the archive, runs the generic MLX smoke test, and uploads—but does not publish—the three candidate assets.

A maintainer must verify the downloaded workflow artefact, then create `SchoolMemoryLocalAI v1.0.0` with:

- `SchoolMemoryLocalAI-1.0.0.tar.gz`;
- `SchoolMemoryLocalAI-1.0.0.sha256`;
- `manifest-1.0.0.json`.

Publish the validated upload first as a GitHub pre-release. Only after that public asset exists, has been downloaded and revalidated, and its immutable HTTPS URL and real checksum are known may committed latest metadata become `recommended`; promotion then removes the pre-release flag. GitHub assets are immutable under this policy: never delete and replace one under an existing version. Correct any byte with a new semantic version. No workflow in this repository automatically publishes a release.

## Validation independence

The release validator recalculates hashes and sizes, parses archive members without extraction, and separately enforces structure, file allow-lists, metadata consistency, and archive safety. The lightweight test suite creates synthetic packages and exercises both successful reproducibility and adversarial failures without downloading model weights.
