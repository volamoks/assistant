#!/usr/bin/env python3
"""
Task Briefing — finds unchecked tasks in Obsidian vault and groups by folder.
No LLM needed. Pure Python. ~2s vs 90s+ agent approach.
"""

import os
import sys
from pathlib import Path
from collections import defaultdict

VAULT_PATH = Path(os.getenv("USER_VAULT_PATH", "/data/obsidian"))
SKIP_DIRS = {".git", ".obsidian", ".trash", "Archive", "Templates"}
MAX_TASKS_PER_GROUP = 5
PRIORITY_FOLDERS = {"Work", "Claw"}


def iter_md_files():
    for f in VAULT_PATH.rglob("*.md"):
        if any(part in SKIP_DIRS for part in f.parts):
            continue
        yield f


def get_group_name(path: Path) -> str:
    """Return top 2 folder levels relative to vault root."""
    rel = path.relative_to(VAULT_PATH)
    parts = rel.parts
    if len(parts) >= 3:
        return f"{parts[0]}/{parts[1]}"
    elif len(parts) == 2:
        return parts[0]
    return "Root"


def main():
    if not VAULT_PATH.exists():
        print(f"Vault not found: {VAULT_PATH}")
        sys.exit(1)

    groups = defaultdict(list)

    for f in iter_md_files():
        try:
            lines = f.read_text(encoding="utf-8", errors="ignore").splitlines()
        except Exception:
            continue

        tasks = [l.strip() for l in lines if l.strip().startswith("- [ ]")]
        if not tasks:
            continue

        group = get_group_name(f)
        for task in tasks:
            groups[group].append(task)

    if not groups:
        print("No pending tasks found.")
        return

    total = sum(len(v) for v in groups.values())
    print(f"# Morning Task Briefing — {total} pending tasks\n")

    # Priority groups first
    def sort_key(g):
        top = g.split("/")[0]
        return (0 if top in PRIORITY_FOLDERS else 1, g)

    for group in sorted(groups.keys(), key=sort_key):
        tasks = groups[group]
        print(f"## {group} ({len(tasks)} tasks)")
        for t in tasks[:MAX_TASKS_PER_GROUP]:
            print(f"  {t}")
        if len(tasks) > MAX_TASKS_PER_GROUP:
            print(f"  ... and {len(tasks) - MAX_TASKS_PER_GROUP} more")
        print()


if __name__ == "__main__":
    main()
