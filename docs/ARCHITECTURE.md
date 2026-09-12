# Architecture

## Principle

`SchoolMemoryLocalAI` is a stable logical model identity. The upstream model, quantisation and runtime may change between releases.

A host application must depend only on the public manifest and host contract.

## Layers

```text
Host application
    |
    v
Generic local-AI adapter
    |
    v
SchoolMemoryLocalAI manifest
    |
    +--> compatibility policy
    +--> storage policy
    +--> immutable release asset
    +--> integrity verification
```

## Separation of concerns

This repository owns:

1. model provenance;
2. immutable release packaging;
3. compatibility metadata;
4. package integrity;
5. generic lifecycle rules.

The host application owns:

1. prompts and instructions;
2. user context;
3. retrieval logic;
4. safety/policy rules specific to the application;
5. output validation;
6. fallback/provider selection;
7. user interface and storage consent.

No host-specific content should cross this boundary.

## Installation sequence

1. Fetch committed release metadata.
2. Verify host-contract and OS compatibility.
3. Evaluate free-space policy in the host.
4. Download to a temporary location.
5. Verify the release-package SHA-256.
6. Unpack to a versioned directory.
7. Validate required model files and locked weight hash.
8. Atomically mark the new version active.
9. Keep the previous working version until the new version has loaded successfully.
10. Remove obsolete versions according to host policy.

## Update sequence

An installed version is never replaced in place. Each version is immutable.

A newer release may be offered only when:

- its status is `recommended`;
- its contract version is supported;
- its runtime is supported;
- its minimum OS is satisfied;
- its integrity metadata is complete.

## Withdrawal

A manifest may mark a release `withdrawn`. A host should stop offering a withdrawn release for new installation. Whether an already installed release is disabled is a host policy decision and must not be controlled remotely without an explicit host-side rule.

## Package boundary and rollback

Acquisition is exact-revision, allow-list based, non-executing, hash checked, and atomic. Packaging consumes only that materialised directory and public licence/provenance files. Validation is a separate entry point that parses every archive entry directly and does not trust the builder's conclusions.

Storage thresholds belong to release policy, not to a particular upstream family. Hosts should stage downloads and extraction, activate versioned installations atomically, retain the last successfully loaded version for rollback, and never mutate an installed version in place.
