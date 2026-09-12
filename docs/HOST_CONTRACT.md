# Host Contract v1

This document defines the generic boundary between a host application and SchoolMemoryLocalAI.

## Stable identifier

`SchoolMemoryLocalAI`

Do not use an upstream model name as a host-facing identifier.

## Required host responsibilities

The host must:

- load release metadata;
- enforce compatibility;
- obtain any required user consent for storage/network use;
- verify package integrity before activation;
- provide inference prompts and context at runtime;
- validate generated output;
- implement deterministic or alternative fallbacks;
- handle cancellation, memory pressure and inference failure;
- expose removal of downloaded assets where appropriate.

## Model package responsibilities

A release package must:

- contain only files required for local inference and licence/provenance notices;
- be immutable after publication;
- have a release-package SHA-256;
- preserve the locked upstream model revision;
- preserve or document all required upstream notices;
- contain no host data or product prompts.

## Contract evolution

Breaking changes increment `contractVersion`.

A host must ignore releases requiring a contract version newer than it implements.

Changing the upstream model, quantisation, package compression or prompt-independent runtime configuration does not by itself require a contract-version increment if the host contract remains compatible.
