#!/usr/bin/env python3
"""Independently validate a release archive and its sidecar metadata."""

from __future__ import annotations

import argparse
import hashlib
import json
import posixpath
import stat
import tarfile
from pathlib import Path, PurePosixPath

from manifest_validation import validate_lock, validate_manifest
from release_common import LOGICAL_MODEL_ID, ROOT, ValidationError, load_json, sha256_file, validate_version

MODEL_FILES = {"added_tokens.json", "config.json", "merges.txt", "model.safetensors", "model.safetensors.index.json", "special_tokens_map.json", "tokenizer.json", "tokenizer_config.json", "vocab.json"}
NOTICE_FILES = {"README.md", "UPSTREAM_PROVENANCE.json", "LICENSE", "THIRD_PARTY_NOTICES.md", "MODEL_LOCK.json", "release-manifest.json"}
EXPECTED_FILES = MODEL_FILES | NOTICE_FILES
SECRET_NAMES = {".env", ".npmrc", ".pypirc", "credentials", "id_rsa", "id_ed25519", "known_hosts", "authorized_keys"}
ARCHIVE_SUFFIXES = (".zip", ".tar", ".tar.gz", ".tgz", ".7z", ".rar", ".gz")


def validate_archive(archive_path: Path, manifest_path: Path | None = None) -> dict:
    if not archive_path.is_file() or archive_path.is_symlink(): raise ValidationError("archive is missing or is a symlink")
    name = archive_path.name
    if not name.startswith(LOGICAL_MODEL_ID + "-") or not name.endswith(".tar.gz"): raise ValidationError("invalid archive filename")
    version = name[len(LOGICAL_MODEL_ID) + 1:-7]; validate_version(version)
    manifest_path = manifest_path or archive_path.with_name(f"manifest-{version}.json")
    manifest = load_json(manifest_path); lock = load_json(ROOT / "MODEL_LOCK.json")
    validate_lock(lock); validate_manifest(manifest, lock)
    if manifest["version"] != version or manifest["asset"]["fileName"] != name: raise ValidationError("release version is inconsistent")
    actual_package_hash = sha256_file(archive_path)
    if manifest["asset"]["sha256"] != actual_package_hash: raise ValidationError("package SHA-256 mismatch")
    if manifest["storage"]["downloadBytes"] != archive_path.stat().st_size: raise ValidationError("package byte count mismatch")
    root = f"{LOGICAL_MODEL_ID}-{version}"; seen: set[str] = set(); content: dict[str, bytes] = {}; installed = 0
    try:
        with tarfile.open(archive_path, "r:gz") as tar:
            for member in tar:
                path = PurePosixPath(member.name)
                if member.name in seen: raise ValidationError("duplicate archive entry")
                seen.add(member.name)
                if path.is_absolute() or ".." in path.parts or posixpath.normpath(member.name) != member.name: raise ValidationError("unsafe archive path")
                if len(path.parts) != 2 or path.parts[0] != root: raise ValidationError("invalid archive structure")
                relative = path.parts[1]
                if relative not in EXPECTED_FILES: raise ValidationError(f"unexpected archive file: {relative}")
                if member.issym() or member.islnk() or not member.isfile(): raise ValidationError("links and non-regular entries are forbidden")
                if member.mode & 0o111: raise ValidationError(f"unexpected executable: {relative}")
                if relative.casefold() in SECRET_NAMES or relative.casefold().endswith(ARCHIVE_SUFFIXES): raise ValidationError(f"secret-like or nested archive file: {relative}")
                stream = tar.extractfile(member)
                if stream is None: raise ValidationError("cannot read archive member")
                content[relative] = stream.read(); installed += member.size
    except (tarfile.TarError, EOFError, OSError) as exc: raise ValidationError(f"invalid or truncated archive: {exc}") from exc
    if set(content) != EXPECTED_FILES: raise ValidationError(f"required archive files differ: {sorted(EXPECTED_FILES - set(content))}")
    if installed != manifest["storage"]["installedBytes"]: raise ValidationError("installed byte count mismatch")
    weight = content[lock["weights"]["file"]]
    if len(weight) != lock["weights"]["sizeBytes"] or hashlib.sha256(weight).hexdigest() != lock["weights"]["sha256"]: raise ValidationError("locked model weight mismatch")
    try:
        packed_lock = json.loads(content["MODEL_LOCK.json"]); provenance = json.loads(content["UPSTREAM_PROVENANCE.json"]); embedded = json.loads(content["release-manifest.json"])
    except (UnicodeError, json.JSONDecodeError) as exc: raise ValidationError(f"invalid packaged metadata: {exc}") from exc
    if packed_lock != lock: raise ValidationError("packaged lock differs from repository lock")
    if provenance.get("repository") != lock["upstream"]["repository"] or provenance.get("revision") != lock["upstream"]["revision"]: raise ValidationError("packaged provenance mismatch")
    for key in ("logicalModelId", "contractVersion", "version", "runtime", "compatibility", "upstream"):
        if embedded.get(key) != manifest[key]: raise ValidationError(f"embedded manifest {key} mismatch")
    checksum_path = archive_path.with_suffix("").with_suffix(".sha256")
    if checksum_path.exists() and checksum_path.read_text(encoding="ascii") != f"{actual_package_hash}  {name}\n": raise ValidationError("checksum sidecar mismatch")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("archive", type=Path); parser.add_argument("--manifest", type=Path)
    args = parser.parse_args()
    try: manifest = validate_archive(args.archive.resolve(), args.manifest.resolve() if args.manifest else None)
    except (OSError, ValidationError) as exc: print(f"ERROR: {exc}"); return 1
    print(f"Validated {manifest['logicalModelId']} {manifest['version']}"); return 0


if __name__ == "__main__": raise SystemExit(main())
