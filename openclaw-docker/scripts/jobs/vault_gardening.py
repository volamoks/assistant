#!/usr/bin/env python3
"""
Vault Gardening — finds empty files and broken wikilinks in Obsidian vault.
No LLM needed. Pure Python file system checks.
Target: ~5s, vs 30s+ agent approach.
"""

import os
import re
import sys
from pathlib import Path

VAULT_PATH = Path(os.getenv("USER_VAULT_PATH", "/data/obsidian"))
SKIP_DIRS = {".git", ".obsidian", ".trash"}

MAX_BROKEN_LINKS = 30


def iter_md_files():
    for f in VAULT_PATH.rglob("*.md"):
        if any(part in SKIP_DIRS for part in f.parts):
            continue
        yield f


def main():
    if not VAULT_PATH.exists():
        print(f"Vault not found: {VAULT_PATH}")
        sys.exit(1)

    # Build set of known filenames (without extension) for wikilink lookup
    known_stems = set()
    all_md = list(iter_md_files())
    for f in all_md:
        known_stems.add(f.stem.lower())

    issues = []

    # 1. Empty files
    empty = [f for f in all_md if f.stat().st_size == 0]
    if empty:
        issues.append("=== Empty Files ===")
        for f in empty:
            issues.append(f"  {f.relative_to(VAULT_PATH)}")

    # 2. Broken wikilinks
    wikilink_re = re.compile(r"\[\[([^\]]+)\]\]")
    broken = []
    checked = 0

    for f in all_md:
        try:
            text = f.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        for match in wikilink_re.finditer(text):
            raw = match.group(1)
            # Strip alias (|) and anchor (#)
            target = raw.split("|")[0].split("#")[0].strip()
            if not target:
                continue
            target_lower = target.lower()
            # Also try just the filename part (ignore path)
            target_stem = Path(target_lower).stem
            if target_lower not in known_stems and target_stem not in known_stems:
                broken.append(f"  {f.relative_to(VAULT_PATH)} → [[{raw}]]")
                checked += 1
                if checked >= MAX_BROKEN_LINKS:
                    break
        if checked >= MAX_BROKEN_LINKS:
            break

    if broken:
        issues.append("\n=== Broken Wikilinks ===")
        issues.extend(broken)
        if checked >= MAX_BROKEN_LINKS:
            issues.append(f"  (showing first {MAX_BROKEN_LINKS})")

    if issues:
        print("\n".join(issues))
    else:
        print("OK — no empty files, no broken wikilinks")


if __name__ == "__main__":
    main()
