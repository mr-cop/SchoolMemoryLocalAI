#!/usr/bin/env python3
"""Atomically materialise the explicitly locked Hugging Face revision."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from manifest_validation import validate_lock
from release_common import INFERENCE_FILES, ROOT, UPSTREAM_PROVENANCE_FILES, ValidationError, load_json, sha256_file


def download(url: str, destination: Path) -> None:
    partial = destination.with_suffix(destination.suffix + ".partial")
    try:
        with urllib.request.urlopen(url, timeout=120) as response, partial.open("xb") as output:
            if getattr(response, "status", 200) != 200:
                raise ValidationError(f"download failed with HTTP {response.status}")
            shutil.copyfileobj(response, output, length=1024 * 1024)
        os.replace(partial, destination)
    except Exception:
        partial.unlink(missing_ok=True)
        raise


def acquire(destination: Path, base_url: str = "https://huggingface.co") -> None:
    lock = load_json(ROOT / "MODEL_LOCK.json"); validate_lock(lock)
    if destination.exists(): raise ValidationError(f"destination already exists: {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    repository, revision = lock["upstream"]["repository"], lock["upstream"]["revision"]
    quoted_repo = "/".join(urllib.parse.quote(x, safe="") for x in repository.split("/"))
    with tempfile.TemporaryDirectory(prefix="schoolmemory-acquire-", dir=destination.parent) as temp:
        stage = Path(temp) / "model"; stage.mkdir()
        for name in INFERENCE_FILES + UPSTREAM_PROVENANCE_FILES:
            url = f"{base_url.rstrip('/')}/{quoted_repo}/resolve/{revision}/{urllib.parse.quote(name)}"
            try: download(url, stage / name)
            except (OSError, urllib.error.URLError) as exc: raise ValidationError(f"failed acquiring locked {name}: {exc}") from exc
        weight = stage / lock["weights"]["file"]
        if weight.stat().st_size != lock["weights"]["sizeBytes"]: raise ValidationError("locked weight size mismatch")
        if sha256_file(weight) != lock["weights"]["sha256"]: raise ValidationError("locked weight SHA-256 mismatch")
        provenance = {"repository": repository, "revision": revision, "files": list(INFERENCE_FILES + UPSTREAM_PROVENANCE_FILES)}
        (stage / "UPSTREAM_PROVENANCE.json").write_text(json.dumps(provenance, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        os.replace(stage, destination)


def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("destination", type=Path); parser.add_argument("--base-url", default="https://huggingface.co")
    args = parser.parse_args()
    try: acquire(args.destination.resolve(), args.base_url)
    except ValidationError as exc: print(f"ERROR: {exc}"); return 1
    print(f"Materialised verified locked model at {args.destination}"); return 0


if __name__ == "__main__": raise SystemExit(main())
