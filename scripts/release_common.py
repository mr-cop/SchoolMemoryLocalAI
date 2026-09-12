"""Shared constants and small, dependency-free release helpers."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
LOGICAL_MODEL_ID = "SchoolMemoryLocalAI"
SUPPORTED_CONTRACT_VERSIONS = {1}
SEMVER = re.compile(r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)(?:-([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")
PLACEHOLDER_SHA256 = "0" * 64
STATUSES = {"candidate", "recommended", "superseded", "withdrawn"}

# This is an explicit allow-list: an upstream repository cannot add package content.
INFERENCE_FILES = (
    "added_tokens.json", "config.json", "merges.txt", "model.safetensors",
    "model.safetensors.index.json", "special_tokens_map.json", "tokenizer.json",
    "tokenizer_config.json", "vocab.json",
)
UPSTREAM_PROVENANCE_FILES = ("README.md",)
PACKAGE_METADATA_FILES = ("LICENSE", "THIRD_PARTY_NOTICES.md", "MODEL_LOCK.json", "release-manifest.json")


class ValidationError(ValueError):
    pass


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValidationError(f"cannot read valid JSON from {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ValidationError(f"{path} must contain a JSON object")
    return value


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def validate_version(version: str) -> None:
    match = SEMVER.fullmatch(version) if isinstance(version, str) else None
    if not match or any(part.startswith("0") and len(part) > 1 for part in match.groups()[:3]):
        raise ValidationError(f"invalid semantic version: {version!r}")
    prerelease = match.group(4)
    if prerelease and any(part.isdigit() and len(part) > 1 and part.startswith("0") for part in prerelease.split(".")):
        raise ValidationError(f"invalid semantic version: {version!r}")


def canonical_json(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")
