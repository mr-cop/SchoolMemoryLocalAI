#!/usr/bin/env python3
import sys
from manifest_validation import validate_lock, validate_manifest, validate_schema
from release_common import ROOT, ValidationError, load_json

try:
    lock = load_json(ROOT / "MODEL_LOCK.json")
    schema = load_json(ROOT / "manifest" / "schema.json")
    manifest = load_json(ROOT / "manifest" / "latest.json")
    validate_schema(schema)
    validate_lock(lock)
    validate_manifest(manifest, lock)
except ValidationError as exc:
    print(f"ERROR: {exc}", file=sys.stderr)
    sys.exit(1)

print("Lock and candidate manifest are internally consistent.")
