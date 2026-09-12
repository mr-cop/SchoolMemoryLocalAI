#!/usr/bin/env python3
"""Scan files intended for publication; patterns are assembled to avoid self-hits."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DENYLIST = ROOT / ".public-safety-denylist.txt"
BINARY_ALLOWLIST: set[str] = set()
CREDENTIAL_NAMES = {".env", ".env.local", ".npmrc", ".pypirc", "credentials", "id_rsa", "id_ed25519", "known_hosts", "authorized_keys"}


def tracked_files() -> list[Path]:
    result = subprocess.run(["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"], cwd=ROOT, check=True, capture_output=True)
    return [ROOT / item.decode("utf-8") for item in result.stdout.split(b"\0") if item]


def signatures() -> list[tuple[str, re.Pattern[str]]]:
    slash, backslash, begin = "/", "\\", "-----" + "BEGIN"
    return [
        ("private key", re.compile(re.escape(begin) + r" (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY")),
        ("certificate", re.compile(re.escape(begin) + r" CERTIFICATE")),
        ("bearer token", re.compile(r"\bBear" + r"er\s+[A-Za-z0-9._~+/=-]{20,}", re.I)),
        ("GitHub token", re.compile(r"\b(?:gh" + r"[oprsu]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})\b")),
        ("AWS access key", re.compile(r"\b(?:AK" + r"IA|ASIA)[0-9A-Z]{16}\b")),
        ("secret assignment", re.compile(r"(?im)^\s*(?:api[_-]?key|secret|password|passwd|token)\s*[:=]\s*['\"]?[^\s'\"<>{}]{8,}")),
        ("email address", re.compile(r"\b[A-Z0-9._%+-]+" + "@" + r"[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I)),
        ("private IPv4 address", re.compile(r"\b(?:10\.(?:\d{1,3}\.){2}\d{1,3}|192\.168\.(?:\d{1,3}\.)\d{1,3}|172\.(?:1[6-9]|2\d|3[01])\.(?:\d{1,3}\.)\d{1,3})\b")),
        ("local endpoint", re.compile(r"(?i)(?:https?://(?:local" + r"host|127\.0\.0\.1|0\.0\.0\.0)(?::\d+)?(?:/|\b)|(?:localhost|127\.0\.0\.1|0\.0\.0\.0):\d+)")),
        ("macOS user home path", re.compile(re.escape(slash + "Users" + slash) + r"[^/\s]+/")),
        ("Linux user home path", re.compile(re.escape(slash + "home" + slash) + r"[^/\s]+/")),
        ("root home path", re.compile(re.escape(slash + "root" + slash) + r"[^/\s]+")),
        ("Windows user home path", re.compile(r"[A-Za-z]:" + re.escape(backslash + "Users" + backslash) + r"[^\\\s]+\\")),
    ]


def scan(paths: list[Path] | None = None) -> list[tuple[str, str, str]]:
    violations = []
    deny_terms = []
    if DENYLIST.exists():
        deny_terms = [x.strip() for x in DENYLIST.read_text(encoding="utf-8").splitlines() if x.strip() and not x.lstrip().startswith("#")]
    for path in paths or tracked_files():
        # A tracked path may be staged for deletion in a developer worktree.
        if not path.exists():
            continue
        relative = path.relative_to(ROOT).as_posix()
        if path.name.casefold() in CREDENTIAL_NAMES or path.suffix.casefold() in {".pem", ".key", ".p12", ".pfx", ".cer", ".crt"}:
            violations.append((relative, "credential/certificate filename", path.name))
        data = path.read_bytes()
        try: content = data.decode("utf-8")
        except UnicodeDecodeError:
            if relative not in BINARY_ALLOWLIST: violations.append((relative, "unexpected binary artefact", "non-UTF-8 tracked file"))
            continue
        if "\0" in content and relative not in BINARY_ALLOWLIST:
            violations.append((relative, "unexpected binary artefact", "NUL byte")); continue
        for label, pattern in signatures():
            for match in pattern.finditer(content): violations.append((relative, label, match.group(0)[:120]))
        folded = content.casefold()
        for term in deny_terms:
            if term.casefold() in folded: violations.append((relative, "local deny-list term", term))
    return violations


if __name__ == "__main__":
    findings = scan()
    if findings:
        print("PUBLIC SAFETY CHECK FAILED")
        for filename, label, sample in findings: print(f"- {filename}: {label}: {sample}")
        raise SystemExit(1)
    print("Public safety check passed.")
