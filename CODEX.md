# Codex Instructions

This is a public repository. Treat prevention of private-information leakage as a release requirement.

## Objective

Complete a production-ready, generic packaging and validation pipeline for `SchoolMemoryLocalAI` without introducing any host-application-specific content.

## Constraints

- Do not inspect, import or copy files from any other repository.
- Do not add product prompts, user examples, private evaluation data or application source.
- Do not add names, email addresses, addresses, coordinates, internal URLs or credentials.
- Do not change the locked v1 upstream revision without an explicit change to `MODEL_LOCK.json`.
- Do not commit model weights into normal Git history.
- Release artefacts must be immutable and checksum verified.
- Scripts must fail closed on integrity mismatches.
- Keep the host contract model-family agnostic.

## Tasks

1. Validate `MODEL_LOCK.json` and manifest files in CI.
2. Implement a packaging script that:
   - downloads or accepts the exact locked upstream revision;
   - verifies `model.safetensors` against the locked SHA-256;
   - copies only inference-required files and required notices;
   - creates `SchoolMemoryLocalAI-<version>.tar.gz`;
   - calculates the package SHA-256;
   - produces a candidate release manifest;
   - never overwrites an existing artefact.
3. Implement a package-validation script that verifies:
   - archive integrity;
   - package checksum;
   - expected files;
   - locked model-weight checksum;
   - no unexpected executable or secret-like files.
4. Extend public-safety checks for:
   - common secret formats;
   - private keys;
   - obvious credentials;
   - email addresses;
   - private IPv4 ranges and localhost endpoints;
   - accidental absolute home-directory paths;
   - optional local deny-list terms.
5. Add generic smoke-test scaffolding. Tests must use synthetic, non-domain-specific text.
6. Add CI workflows that run without access to private repositories or secrets.
7. Document the exact manual steps required to create and publish an immutable GitHub Release asset.
8. Do not mark `manifest/latest.json` as `recommended` until the actual release package exists and its real SHA-256 replaces the placeholder.

## Definition of done

- CI passes on a clean public clone.
- The locked model can be reproduced from its exact upstream revision.
- A package can be built and independently verified.
- No project-specific information is present.
- No production release is silently mutable.
