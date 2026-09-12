#!/usr/bin/env python3
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
SKIP_DIRS = {".git", ".venv", "dist", "build", "__pycache__"}
TEXT_SUFFIXES = {
    ".md", ".txt", ".json", ".yaml", ".yml", ".py", ".sh",
    ".swift", ".toml", ".ini", ".cfg", ".xml"
}

# Build certain signatures in pieces so this checker does not match its own source.
slash = "/"
backslash = "\\"

patterns = [
    ("private key", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----")),
    ("generic bearer token", re.compile(r"\bBearer\s+[A-Za-z0-9._~+/\-=]{20,}", re.I)),
    ("GitHub token", re.compile(r"\b(?:ghp|github_pat)_[A-Za-z0-9_]{20,}\b")),
    ("AWS access key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("email address", re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I)),
    ("private IPv4 address", re.compile(
        r"\b(?:10\.(?:\d{1,3}\.){2}\d{1,3}|"
        r"192\.168\.(?:\d{1,3}\.)\d{1,3}|"
        r"172\.(?:1[6-9]|2\d|3[01])\.(?:\d{1,3}\.)\d{1,3})\b"
    )),
    ("macOS user home path", re.compile(re.escape(slash + "Users" + slash) + r"[^/\s]+/")),
    ("Linux user home path", re.compile(re.escape(slash + "home" + slash) + r"[^/\s]+/")),
    ("Windows user home path", re.compile(r"[A-Za-z]:" + re.escape(backslash + "Users" + backslash) + r"[^\\\s]+\\")),
]

denylist_path = ROOT / ".public-safety-denylist.txt"
deny_terms = []
if denylist_path.exists():
    deny_terms = [
        line.strip() for line in denylist_path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]

violations = []

for path in ROOT.rglob("*"):
    if not path.is_file():
        continue
    if any(part in SKIP_DIRS for part in path.parts):
        continue
    if path.name == ".public-safety-denylist.txt":
        continue
    if path.suffix.lower() not in TEXT_SUFFIXES and path.name != ".gitignore":
        continue

    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        continue

    relative = path.relative_to(ROOT)

    for label, pattern in patterns:
        for match in pattern.finditer(text):
            violations.append((str(relative), label, match.group(0)[:120]))

    lowered = text.casefold()
    for term in deny_terms:
        if term.casefold() in lowered:
            violations.append((str(relative), "local deny-list term", term))

if violations:
    print("PUBLIC SAFETY CHECK FAILED")
    for filename, label, sample in violations:
        print(f"- {filename}: {label}: {sample}")
    sys.exit(1)

print("Public safety check passed.")
