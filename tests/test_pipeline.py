from __future__ import annotations

import copy
import hashlib
import io
import json
import os
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import acquire_model
import build_release
import check_public_safety
import validate_release
from manifest_validation import validate_lock, validate_manifest
from release_common import INFERENCE_FILES, UPSTREAM_PROVENANCE_FILES, ValidationError, canonical_json, sha256_file


def fixture_lock(weight=b"weights"):
    return {"logicalModelId": "SchoolMemoryLocalAI", "contractVersion": 1, "releaseLine": "1.x",
            "upstream": {"provider": "Hugging Face", "repository": "public/model", "revision": "a" * 40, "baseModel": "public/base", "licence": "Apache-2.0", "conversionTool": {"name": "tool", "version": "1.0"}},
            "runtime": {"family": "mlx", "format": "safetensors", "quantisation": {"bits": 4, "groupSize": 64}},
            "weights": {"file": "model.safetensors", "sizeBytes": len(weight), "sha256": hashlib.sha256(weight).hexdigest()}}


def fixture_manifest():
    return {"logicalModelId": "SchoolMemoryLocalAI", "contractVersion": 1, "version": "1.0.0", "status": "candidate",
            "runtime": {"family": "mlx", "format": "safetensors"}, "compatibility": {"minimumHostContract": 1, "minimumOS": "17.0", "architectures": ["arm64"]},
            "storage": {"downloadBytes": 1, "installedBytes": 1, "warningFreeBytes": 1000000, "minimumFreeBytes": 500000},
            "asset": {"fileName": "SchoolMemoryLocalAI-1.0.0.tar.gz", "sha256": "0" * 64, "downloadURL": None},
            "upstream": {"repository": "public/model", "revision": "a" * 40, "licence": "Apache-2.0"}}


class ManifestTests(unittest.TestCase):
    def setUp(self): self.lock, self.manifest = fixture_lock(), fixture_manifest()

    def test_valid_candidate(self): validate_lock(self.lock); validate_manifest(self.manifest, self.lock)

    def test_bad_inputs_fail_closed(self):
        mutations = [("logicalModelId", "Other"), ("contractVersion", 2), ("status", "unknown"), ("version", "01.0.0")]
        for field, value in mutations:
            with self.subTest(field=field), self.assertRaises(ValidationError):
                candidate = copy.deepcopy(self.manifest); candidate[field] = value; validate_manifest(candidate, self.lock)

    def test_recommended_rejects_placeholder_and_missing_url(self):
        self.manifest["status"] = "recommended"
        with self.assertRaises(ValidationError): validate_manifest(self.manifest, self.lock)
        self.manifest["asset"]["sha256"] = "1" * 64
        with self.assertRaises(ValidationError): validate_manifest(self.manifest, self.lock)

    def test_malformed_hash_rejected(self):
        self.lock["weights"]["sha256"] = "bad"
        with self.assertRaises(ValidationError): validate_lock(self.lock)


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.root = Path(self.temp.name); self.source = self.root / "source"; self.source.mkdir()
        self.weight = b"weights"; self.lock = fixture_lock(self.weight); self.manifest = fixture_manifest()
        for name in INFERENCE_FILES + UPSTREAM_PROVENANCE_FILES: (self.source / name).write_bytes(self.weight if name == "model.safetensors" else b"{}\n")
        (self.source / "UPSTREAM_PROVENANCE.json").write_bytes(canonical_json({"repository": "public/model", "revision": "a" * 40, "files": list(INFERENCE_FILES + UPSTREAM_PROVENANCE_FILES)}))
        for name in ("LICENSE", "THIRD_PARTY_NOTICES.md", "MODEL_LOCK.json"):
            (self.root / name).write_bytes(canonical_json(self.lock) if name == "MODEL_LOCK.json" else b"notice\n")

    def tearDown(self): self.temp.cleanup()

    def _load(self, path):
        if path.name == "MODEL_LOCK.json": return copy.deepcopy(self.lock)
        if path.name == "latest.json": return copy.deepcopy(self.manifest)
        return json.loads(path.read_text())

    def build(self, out=None):
        out = out or self.root / "dist"
        with mock.patch.object(build_release, "ROOT", self.root), mock.patch.object(build_release, "load_json", side_effect=self._load):
            return build_release.build("1.0.0", self.source, out)

    def validate(self, archive, manifest):
        original = validate_release.load_json
        def loader(path): return copy.deepcopy(self.lock) if path.name == "MODEL_LOCK.json" else original(path)
        with mock.patch.object(validate_release, "ROOT", self.root), mock.patch.object(validate_release, "load_json", side_effect=loader):
            return validate_release.validate_archive(archive, manifest)

    def test_build_is_reproducible_and_valid(self):
        a = self.build(self.root / "one"); b = self.build(self.root / "two")
        self.assertEqual(sha256_file(a[0]), sha256_file(b[0])); self.validate(a[0], a[2])

    def test_refuses_overwrite(self):
        self.build()
        with self.assertRaises(ValidationError): self.build()

    def test_missing_and_wrong_weight_fail(self):
        (self.source / "model.safetensors").unlink()
        with self.assertRaises(ValidationError): self.build()
        (self.source / "model.safetensors").write_bytes(b"tampered")
        with self.assertRaises(ValidationError): self.build()

    def _rewrite(self, archive, transform):
        members = []
        with tarfile.open(archive, "r:gz") as source:
            for member in source:
                members.append((member, source.extractfile(member).read()))
        with tarfile.open(archive, "w:gz") as target:
            for member, data in transform(members): target.addfile(member, io.BytesIO(data))
        manifest = archive.with_name("manifest-1.0.0.json"); value = json.loads(manifest.read_text()); value["asset"]["sha256"] = sha256_file(archive); value["storage"]["downloadBytes"] = archive.stat().st_size; manifest.write_bytes(canonical_json(value))

    def test_package_hash_mismatch(self):
        archive, _, manifest = self.build(); archive.write_bytes(archive.read_bytes() + b"x")
        with self.assertRaises(ValidationError): self.validate(archive, manifest)

    def test_traversal_symlink_duplicate_and_executable_rejected(self):
        transforms = []
        def traversal(items): items[0][0].name = "../escape"; return items
        def symlink(items): items[0][0].type = tarfile.SYMTYPE; items[0][0].linkname = "elsewhere"; items[0][0].size = 0; items[0] = (items[0][0], b""); return items
        def duplicate(items): return items + [items[0]]
        def executable(items): items[0][0].mode = 0o755; return items
        for transform in (traversal, symlink, duplicate, executable):
            with self.subTest(transform=transform.__name__):
                archive, _, manifest = self.build(self.root / transform.__name__); self._rewrite(archive, transform)
                with self.assertRaises(ValidationError): self.validate(archive, manifest)


class DownloadTests(unittest.TestCase):
    def test_interrupted_download_removes_partial(self):
        class Broken:
            status = 200
            def __enter__(self): return self
            def __exit__(self, *args): return False
            def read(self, size=-1): raise OSError("interrupted")
        with tempfile.TemporaryDirectory() as temp, mock.patch("urllib.request.urlopen", return_value=Broken()):
            path = Path(temp) / "file"
            with self.assertRaises(OSError): acquire_model.download("https://invalid.example/file", path)
            self.assertFalse(path.exists()); self.assertFalse(Path(str(path) + ".partial").exists())


class PublicSafetyTests(unittest.TestCase):
    def test_secret_and_binary_fail_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); secret = root / "sample.txt"; binary = root / "payload.bin"
            secret.write_text("password" + "=not-a-real-secret-value\n")
            binary.write_bytes(b"\xff\x00")
            with mock.patch.object(check_public_safety, "ROOT", root), mock.patch.object(check_public_safety, "DENYLIST", root / ".public-safety-denylist.txt"):
                findings = check_public_safety.scan([secret, binary])
            self.assertEqual({item[1] for item in findings}, {"secret assignment", "unexpected binary artefact"})


if __name__ == "__main__": unittest.main()
