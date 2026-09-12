# SchoolMemoryLocalAI

SchoolMemoryLocalAI is a versioned distribution contract for a small on-device language model.

This repository deliberately contains **no host-application data, private prompts, user data, product-specific evaluation cases, internal architecture, credentials, or operational configuration**.

The stable logical model identifier is:

`SchoolMemoryLocalAI`

Host applications should integrate against the manifest/compatibility contract rather than hard-coding an upstream model family.

## v1 model lock

The initial model is locked to:

- Upstream artefact: `mlx-community/Qwen3-0.6B-4bit`
- Upstream revision: `73e3e38d981303bc594367cd910ea6eb48349da8`
- Runtime format: MLX / Safetensors
- Quantisation: 4-bit, group size 64
- Weight file: `model.safetensors`
- Weight SHA-256: `392e8d466d56100ada00eb82031fb854297fc9e389b7d303eba3af114e87bce2`
- Weight size: `335450584` bytes
- Upstream conversion tooling: `mlx-lm 0.24.0`
- Upstream licence: Apache-2.0

The model identity may change in future releases without changing the host-facing logical identifier.

## Repository boundary

This public repository may contain:

- immutable upstream model provenance;
- model packaging and integrity tooling;
- manifest schemas and compatibility metadata;
- public release metadata;
- generic host integration contracts;
- public safety checks;
- third-party licence notices.

It must not contain:

- user or customer data;
- names, emails, addresses, coordinates or other personal information;
- host-application prompts or prompt templates;
- host-application feature descriptions not required by the generic contract;
- private evaluation datasets or examples;
- API keys, tokens, certificates, secrets or internal URLs;
- source copied from a private host application.

See `PUBLIC_REPOSITORY_POLICY.md`.

## Status

The v1 contract and upstream model are frozen. A release asset is not considered published until its package hash and download location are recorded in a signed/committed release manifest.
