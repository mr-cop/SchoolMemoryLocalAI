# SchoolMemoryLocalAI

SchoolMemoryLocalAI is an immutable, versioned distribution contract for a small on-device language model. It packages verified inference files and public provenance behind the stable logical identifier `SchoolMemoryLocalAI`.

It is **not** a host application, prompt library, behavioural evaluation suite, user-data store, or remote AI service. This repository contains no host-specific implementation or private material. Consumers integrate with the manifest and [host contract](docs/HOST_CONTRACT.md), not an upstream model name. Model family, quantisation, package layout, and runtime may change in a later release when the public contract remains compatible.

## Frozen v1 provenance

v1 is locked in `MODEL_LOCK.json` to upstream `mlx-community/Qwen3-0.6B-4bit`, revision `73e3e38d981303bc594367cd910ea6eb48349da8`. Its `model.safetensors` must be exactly 335450584 bytes with SHA-256 `392e8d466d56100ada00eb82031fb854297fc9e389b7d303eba3af114e87bce2`. Acquisition never resolves a moving branch.

The frozen converted repository contains its model card but no standalone licence file. The model card declares Apache-2.0 and links to the base model licence. Candidate packages therefore preserve that frozen model card, this repository's complete Apache-2.0 `LICENSE`, the lock, and `THIRD_PARTY_NOTICES.md`. See the notices for the precise verification boundary.

## Candidate lifecycle

Requirements: Python 3.10 or newer, network access for acquisition, and enough temporary storage. No third-party Python package is needed for integrity/build tasks.

```bash
python3 scripts/check_public_safety.py
python3 scripts/validate_lock.py
python3 -m unittest discover -s tests -v
python3 scripts/acquire_model.py models/locked
python3 scripts/build_release.py --version 1.0.0
python3 scripts/validate_release.py dist/SchoolMemoryLocalAI-1.0.0.tar.gz
```

Acquisition stages every allow-listed file in a temporary directory, verifies the frozen weight byte count and hash, and atomically moves the completed model. A failed or interrupted operation leaves no apparently valid destination. The build refuses to overwrite outputs; `--force` is only for destroying an **unpublished local** build.

The validator requires the adjacent `manifest-1.0.0.json` and, when present, verifies the `.sha256` sidecar. It reads archive members without extracting them and rejects traversal, links, duplicates, executables, secret-like names, nested archives, unexpected files, metadata disagreements, and hash/size mismatches.

### Optional MLX smoke test

On supported Apple silicon after installing the pinned conversion-era runtime (`python3 -m pip install 'mlx-lm==0.24.0'`):

```bash
python3 scripts/smoke_test_runtime.py models/locked --timeout 180
```

This uses only synthetic generic text. It checks discovery, loading, tokenizer usability, non-empty generation, termination, and enforced timeout cancellation. Application behaviour testing belongs outside this repository.

## Manual release verification and publication

1. Run the GitHub Actions **Full model candidate verification** workflow for version `1.0.0`.
2. Download its candidate workflow artefact and verify all three expected files are present.
3. Run `sha256sum -c SchoolMemoryLocalAI-1.0.0.sha256` and `python3 scripts/validate_release.py SchoolMemoryLocalAI-1.0.0.tar.gz --manifest manifest-1.0.0.json` from a clean public checkout.
4. Confirm the public-safety, integrity, licence/provenance, and generic MLX smoke gates passed.
5. Publish a GitHub **pre-release** with tag/title `v1.0.0` / `SchoolMemoryLocalAI v1.0.0`; attach the `.tar.gz`, `.sha256`, and manifest without renaming them. Never replace an uploaded asset.
6. Download and revalidate the public asset, then record its real immutable HTTPS URL and existing package SHA-256 in `manifest/latest.json`; change status to `recommended`, rerun every gate, review, and merge that metadata change.
7. Remove the GitHub pre-release flag to complete promotion. Any changed artefact byte requires a new semantic version.

Until the real asset exists, URL and hash are known, and all gates pass, `manifest/latest.json` remains `candidate`. A downloaded update installs into a versioned directory and becomes active only after complete validation and a successful load. The previous working version remains available for atomic rollback; withdrawal prevents new offers but does not silently control installed copies.

Storage fields distinguish compressed download bytes, uncompressed installed bytes, a policy warning threshold, and a policy minimum installation threshold. They are not claims about runtime working-space needs; a host must establish any additional runtime requirement for its environment.

See [public repository policy](PUBLIC_REPOSITORY_POLICY.md), [architecture](docs/ARCHITECTURE.md), and [release policy](docs/RELEASE_POLICY.md).
