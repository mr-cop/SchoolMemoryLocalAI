"""Strict semantic validation for locks, release manifests, and their schema."""

from __future__ import annotations

from urllib.parse import urlparse
from typing import Any

from release_common import (LOGICAL_MODEL_ID, PLACEHOLDER_SHA256, SHA256, STATUSES,
                            SUPPORTED_CONTRACT_VERSIONS, ValidationError, validate_version)


def _object(value: Any, name: str, required: set[str], optional: set[str] = set()) -> dict:
    if not isinstance(value, dict):
        raise ValidationError(f"{name} must be an object")
    missing, extra = required - value.keys(), value.keys() - required - optional
    if missing: raise ValidationError(f"{name} missing fields: {', '.join(sorted(missing))}")
    if extra: raise ValidationError(f"{name} has unknown fields: {', '.join(sorted(extra))}")
    return value


def _positive_int(value: Any, name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValidationError(f"{name} must be a positive integer")


def validate_lock(lock: dict) -> None:
    _object(lock, "MODEL_LOCK", {"logicalModelId", "contractVersion", "releaseLine", "upstream", "runtime", "weights"})
    if lock["logicalModelId"] != LOGICAL_MODEL_ID: raise ValidationError("wrong logical model ID")
    if lock["contractVersion"] not in SUPPORTED_CONTRACT_VERSIONS: raise ValidationError("unsupported contract version")
    if lock["releaseLine"] != "1.x": raise ValidationError("unsupported release line")
    upstream = _object(lock["upstream"], "upstream", {"provider", "repository", "revision", "baseModel", "licence", "conversionTool"})
    if upstream["provider"] != "Hugging Face" or not all(isinstance(upstream[x], str) and upstream[x] for x in ("repository", "baseModel", "licence")): raise ValidationError("invalid upstream identity")
    if not isinstance(upstream["revision"], str) or not re_full_hex(upstream["revision"], 40): raise ValidationError("upstream revision must be a 40-character commit hash")
    tool = _object(upstream["conversionTool"], "conversionTool", {"name", "version"})
    if not all(isinstance(tool[x], str) and tool[x] for x in tool): raise ValidationError("invalid conversion tool")
    runtime = _object(lock["runtime"], "runtime", {"family", "format", "quantisation"})
    if runtime["family"] != "mlx" or runtime["format"] != "safetensors": raise ValidationError("unsupported locked runtime")
    quant = _object(runtime["quantisation"], "quantisation", {"bits", "groupSize"})
    _positive_int(quant["bits"], "quantisation.bits"); _positive_int(quant["groupSize"], "quantisation.groupSize")
    weights = _object(lock["weights"], "weights", {"file", "sizeBytes", "sha256"})
    if weights["file"] != "model.safetensors": raise ValidationError("unsupported weight filename")
    _positive_int(weights["sizeBytes"], "weights.sizeBytes")
    if not isinstance(weights["sha256"], str) or not SHA256.fullmatch(weights["sha256"]): raise ValidationError("malformed weight SHA-256")


def re_full_hex(value: str, length: int) -> bool:
    return len(value) == length and all(c in "0123456789abcdef" for c in value)


def validate_manifest(manifest: dict, lock: dict) -> None:
    required = {"logicalModelId", "contractVersion", "version", "status", "runtime", "compatibility", "storage", "asset", "upstream"}
    _object(manifest, "manifest", required)
    if manifest["logicalModelId"] != LOGICAL_MODEL_ID or manifest["logicalModelId"] != lock["logicalModelId"]: raise ValidationError("wrong logical model ID")
    if manifest["contractVersion"] not in SUPPORTED_CONTRACT_VERSIONS or manifest["contractVersion"] != lock["contractVersion"]: raise ValidationError("incompatible contract version")
    validate_version(manifest["version"])
    if manifest["status"] not in STATUSES: raise ValidationError("invalid release state")
    runtime = _object(manifest["runtime"], "runtime", {"family", "format"})
    if runtime != {k: lock["runtime"][k] for k in ("family", "format")}: raise ValidationError("runtime does not match lock")
    compat = _object(manifest["compatibility"], "compatibility", {"minimumHostContract", "minimumOS"}, {"architectures"})
    _positive_int(compat["minimumHostContract"], "minimumHostContract")
    if compat["minimumHostContract"] > manifest["contractVersion"]: raise ValidationError("minimum host contract exceeds contract version")
    if not isinstance(compat["minimumOS"], str) or not compat["minimumOS"]: raise ValidationError("minimumOS must be non-empty")
    if "architectures" in compat and (not isinstance(compat["architectures"], list) or not compat["architectures"] or len(set(compat["architectures"])) != len(compat["architectures"]) or not all(isinstance(x, str) and x for x in compat["architectures"])): raise ValidationError("invalid architectures")
    storage = _object(manifest["storage"], "storage", {"downloadBytes", "installedBytes", "warningFreeBytes", "minimumFreeBytes"})
    for key, value in storage.items(): _positive_int(value, f"storage.{key}")
    if storage["minimumFreeBytes"] < storage["installedBytes"] or storage["warningFreeBytes"] < storage["minimumFreeBytes"]: raise ValidationError("storage policy thresholds are inconsistent")
    asset = _object(manifest["asset"], "asset", {"fileName", "sha256", "downloadURL"})
    expected_name = f"{LOGICAL_MODEL_ID}-{manifest['version']}.tar.gz"
    if asset["fileName"] != expected_name: raise ValidationError("asset filename/version mismatch")
    if not isinstance(asset["sha256"], str) or not SHA256.fullmatch(asset["sha256"]): raise ValidationError("malformed package SHA-256")
    if asset["downloadURL"] is not None and not valid_https_url(asset["downloadURL"]): raise ValidationError("asset URL must be a valid HTTPS URL")
    if manifest["status"] == "recommended" and (asset["sha256"] == PLACEHOLDER_SHA256 or not valid_https_url(asset["downloadURL"])): raise ValidationError("recommended release requires a non-placeholder hash and valid HTTPS URL")
    upstream = _object(manifest["upstream"], "upstream", {"repository", "revision", "licence"})
    for key in upstream:
        if upstream[key] != lock["upstream"][key]: raise ValidationError(f"upstream {key} mismatch")


def valid_https_url(value: Any) -> bool:
    if not isinstance(value, str): return False
    parsed = urlparse(value)
    return parsed.scheme == "https" and bool(parsed.netloc) and not parsed.username and not parsed.password


def validate_schema(schema: dict) -> None:
    _object(schema, "schema", {"$schema", "$id", "title", "type", "additionalProperties", "required", "properties"})
    if schema["$schema"] != "https://json-schema.org/draft/2020-12/schema" or schema["type"] != "object" or schema["additionalProperties"] is not False: raise ValidationError("schema must be strict JSON Schema draft 2020-12")
    if set(schema["required"]) != set(schema["properties"]): raise ValidationError("schema required/properties fields differ")
    if schema["properties"].get("logicalModelId", {}).get("const") != LOGICAL_MODEL_ID: raise ValidationError("schema logical model constraint is invalid")
    if schema["properties"].get("contractVersion", {}).get("enum") != sorted(SUPPORTED_CONTRACT_VERSIONS): raise ValidationError("schema contract versions are unsupported")
