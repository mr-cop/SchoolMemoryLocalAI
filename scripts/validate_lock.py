#!/usr/bin/env python3
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
lock = json.loads((ROOT / "MODEL_LOCK.json").read_text(encoding="utf-8"))
manifest = json.loads((ROOT / "manifest" / "latest.json").read_text(encoding="utf-8"))

errors = []

if lock.get("logicalModelId") != "SchoolMemoryLocalAI":
    errors.append("MODEL_LOCK logicalModelId must be SchoolMemoryLocalAI")

if manifest.get("logicalModelId") != "SchoolMemoryLocalAI":
    errors.append("manifest logicalModelId must be SchoolMemoryLocalAI")

if manifest.get("contractVersion") != lock.get("contractVersion"):
    errors.append("contractVersion mismatch")

if manifest.get("upstream", {}).get("repository") != lock.get("upstream", {}).get("repository"):
    errors.append("upstream repository mismatch")

if manifest.get("upstream", {}).get("revision") != lock.get("upstream", {}).get("revision"):
    errors.append("upstream revision mismatch")

sha = lock.get("weights", {}).get("sha256", "")
if len(sha) != 64 or any(c not in "0123456789abcdef" for c in sha):
    errors.append("locked weight SHA-256 is invalid")

asset_sha = manifest.get("asset", {}).get("sha256", "")
if len(asset_sha) != 64 or any(c not in "0123456789abcdef" for c in asset_sha):
    errors.append("release asset SHA-256 is invalid")

if manifest.get("status") == "recommended" and asset_sha == "0" * 64:
    errors.append("recommended release cannot have placeholder package SHA-256")

if errors:
    for error in errors:
        print(f"ERROR: {error}")
    sys.exit(1)

print("Lock and candidate manifest are internally consistent.")
