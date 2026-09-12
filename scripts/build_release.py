#!/usr/bin/env python3
"""Build a byte-reproducible candidate archive from verified local model files."""

from __future__ import annotations

import argparse
import gzip
import io
import os
import tarfile
import tempfile
from pathlib import Path

from manifest_validation import validate_lock, validate_manifest
from release_common import (INFERENCE_FILES, LOGICAL_MODEL_ID, PACKAGE_METADATA_FILES, ROOT,
                            UPSTREAM_PROVENANCE_FILES, ValidationError, canonical_json,
                            load_json, sha256_file, validate_version)


def checked_source(source: Path, lock: dict) -> list[str]:
    expected = list(INFERENCE_FILES + UPSTREAM_PROVENANCE_FILES) + ["UPSTREAM_PROVENANCE.json"]
    for name in expected:
        path = source / name
        if not path.is_file() or path.is_symlink(): raise ValidationError(f"missing or unsafe source file: {name}")
    weight = source / lock["weights"]["file"]
    if weight.stat().st_size != lock["weights"]["sizeBytes"] or sha256_file(weight) != lock["weights"]["sha256"]: raise ValidationError("model weights do not match frozen lock")
    provenance = load_json(source / "UPSTREAM_PROVENANCE.json")
    if provenance.get("repository") != lock["upstream"]["repository"] or provenance.get("revision") != lock["upstream"]["revision"]: raise ValidationError("source provenance does not match frozen lock")
    return expected


def write_tar(output: Path, root_name: str, files: dict[str, Path | bytes]) -> None:
    with output.open("xb") as raw, gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0, compresslevel=9) as zipped, tarfile.open(fileobj=zipped, mode="w", format=tarfile.PAX_FORMAT) as archive:
        for relative in sorted(files):
            value = files[relative]; data = value if isinstance(value, bytes) else value.read_bytes()
            info = tarfile.TarInfo(f"{root_name}/{relative}"); info.size = len(data); info.mode = 0o644; info.mtime = 0; info.uid = info.gid = 0; info.uname = info.gname = ""
            archive.addfile(info, io.BytesIO(data))


def build(version: str, source: Path, output_dir: Path, force: bool = False) -> tuple[Path, Path, Path]:
    validate_version(version)
    lock = load_json(ROOT / "MODEL_LOCK.json"); validate_lock(lock); source_files = checked_source(source, lock)
    output_dir.mkdir(parents=True, exist_ok=True)
    archive_final = output_dir / f"{LOGICAL_MODEL_ID}-{version}.tar.gz"; checksum_final = output_dir / f"{LOGICAL_MODEL_ID}-{version}.sha256"; manifest_final = output_dir / f"manifest-{version}.json"
    targets = (archive_final, checksum_final, manifest_final)
    if any(p.exists() for p in targets) and not force: raise ValidationError("release output exists; use --force only for unpublished developer rebuilds")
    if force:
        for path in targets: path.unlink(missing_ok=True)
    archive, checksum, manifest_path = (Path(str(path) + ".partial") for path in targets)
    for path in (archive, checksum, manifest_path): path.unlink(missing_ok=True)
    template = load_json(ROOT / "manifest" / "latest.json")
    if template["version"] != version: raise ValidationError("version must match candidate manifest release line")
    package_manifest = dict(template); package_manifest["status"] = "candidate"; package_manifest["asset"] = {"fileName": archive_final.name, "sha256": "0" * 64, "downloadURL": None}
    package_manifest["storage"] = dict(template["storage"])
    # Measured package sizes live in the external sidecar; fixed embedded values
    # avoid making archive bytes depend on measurements of that same archive.
    package_manifest["storage"]["downloadBytes"] = 1
    package_manifest["storage"]["installedBytes"] = 1
    files: dict[str, Path | bytes] = {name: source / name for name in source_files}
    files.update({"LICENSE": ROOT / "LICENSE", "THIRD_PARTY_NOTICES.md": ROOT / "THIRD_PARTY_NOTICES.md", "MODEL_LOCK.json": ROOT / "MODEL_LOCK.json", "release-manifest.json": canonical_json(package_manifest)})
    root_name = f"{LOGICAL_MODEL_ID}-{version}"
    write_tar(archive, root_name, files)
    package_hash = sha256_file(archive)
    installed = sum((v.stat().st_size if isinstance(v, Path) else len(v)) for v in files.values())
    package_manifest["storage"]["downloadBytes"] = archive.stat().st_size
    package_manifest["storage"]["installedBytes"] = installed
    package_manifest["asset"]["sha256"] = package_hash
    # The embedded manifest cannot contain the archive's self-referential hash. The
    # authoritative sidecar is generated after packaging and independently checked.
    manifest_path.write_bytes(canonical_json(package_manifest)); validate_manifest(package_manifest, lock)
    checksum.write_text(f"{package_hash}  {archive_final.name}\n", encoding="ascii")
    for partial, final in zip((archive, checksum, manifest_path), targets): os.replace(partial, final)
    return targets


def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--version", required=True); parser.add_argument("--source", type=Path, default=ROOT / "models" / "locked"); parser.add_argument("--output", type=Path, default=ROOT / "dist"); parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    try: outputs = build(args.version, args.source.resolve(), args.output.resolve(), args.force)
    except (OSError, ValidationError) as exc: print(f"ERROR: {exc}"); return 1
    for path in outputs: print(path)
    return 0


if __name__ == "__main__": raise SystemExit(main())
