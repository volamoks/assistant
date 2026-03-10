#!/usr/bin/env python3
"""
Inbox Router — fast batch classification of Obsidian inbox files.

Design: ONE LLM call classifies all files → then moves them.
Target: ~15s total (vs 300s+ for the multi-LLM-call agent approach).
"""

import os
import sys
import json
import shutil
import requests
from pathlib import Path
from datetime import datetime

# ── Config ────────────────────────────────────────────────────────────────────
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
VAULT_PATH = Path(os.getenv("USER_VAULT_PATH", "/data/obsidian"))
INBOX_DIR = VAULT_PATH / "Inbox"
LOG_FILE = VAULT_PATH / "Claw/Memory/inbox-log.md"
README_FILE = INBOX_DIR / "README.md"

MAX_FILES = 10
MAX_PREVIEW = 800  # chars of each file to send to LLM

# Files/dirs that are expected in vault root (not stray)
ALLOWED_ROOT_FILES = {"00_HOME.md", "00_STRUCTURE.md", ".gitignore", "README.md"}
ALLOWED_ROOT_DIRS = {
    "Work", "Personal", "Assets", "Claw", "03_System",
    "Attachments", "Inbox", ".obsidian", ".git", "vault"
}

# ── Routing prompt ─────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """\
You are a file classifier for an Obsidian personal knowledge vault.
Given a list of files with their content previews, classify each into the correct destination folder.

ROUTING RULES:
- AI/LLM/automation/tools/tech research ideas → Work/Knowledge/
- Work tasks, todos, kanban → Work/Tasks/
- FinTech, banking, payments, financial tech → Work/Knowledge/FinTech/
- API specs, technical documentation → Work/Knowledge/API_Specs/
- Resume, job search, interview prep → Personal/Career/
- Personal finance, budget, investments, crypto portfolio → Personal/Finance/
- Travel plans, trip notes, tickets → Personal/Travel/
- Books (to read or notes from reading) → Personal/Books/
- Personal diary, daily reflections, emotions → Personal/Diary/
- Diagrams, models, media attachments → Assets/
- Claw bot memory, bot research, automation notes → Claw/
- Anything unclear or "quick thought" → Work/Knowledge/

OUTPUT: Return a JSON object with key "files" containing an array.
Each item: {"filename": "...", "dest_dir": "Work/Knowledge/", "reason": "short reason"}
No other text outside the JSON object.
"""


def get_files_to_process() -> list:
    """Collect files from Inbox/ and stray .md files from vault root."""
    files = []

    # 1. Inbox files (skip README.md)
    if INBOX_DIR.exists():
        for f in sorted(INBOX_DIR.iterdir()):
            if f.is_file() and f.suffix == ".md" and f.name != "README.md":
                files.append(f)

    # 2. Stray .md files in vault root
    if VAULT_PATH.exists():
        for f in sorted(VAULT_PATH.iterdir()):
            if (
                f.is_file()
                and f.suffix == ".md"
                and f.name not in ALLOWED_ROOT_FILES
            ):
                files.append(f)

    return files[:MAX_FILES]


def read_preview(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")[:MAX_PREVIEW].strip()
    except Exception:
        return "(unreadable)"


def classify_files_batch(files: list) -> list:
    """Call Groq once to classify all files. Returns list of dicts."""
    if not GROQ_API_KEY:
        print("Error: GROQ_API_KEY not set")
        sys.exit(1)

    parts = []
    for f in files:
        preview = read_preview(f)
        parts.append(f"=== {f.name} ===\n{preview}")

    user_msg = "Classify these files:\n\n" + "\n\n".join(parts)

    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
        ],
        "temperature": 0.1,
    }

    resp = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=30,
    )
    resp.raise_for_status()

    content = resp.json()["choices"][0]["message"]["content"].strip()

    # Extract JSON — might be wrapped in markdown code fence
    if "```" in content:
        start = content.find("{", content.find("```"))
        end = content.rfind("}") + 1
        content = content[start:end]

    parsed = json.loads(content)

    # Expect {"files": [...]} or fall back to bare list
    if isinstance(parsed, dict):
        return parsed.get("files", [])
    if isinstance(parsed, list):
        return parsed
    return []


def safe_dest_path(dest_dir: str, filename: str) -> Path:
    """Resolve dest path, creating dirs, handling filename collisions."""
    dest = VAULT_PATH / dest_dir.strip("/") / filename
    dest.parent.mkdir(parents=True, exist_ok=True)

    if not dest.exists():
        return dest

    stem, suffix = dest.stem, dest.suffix
    for i in range(2, 20):
        candidate = dest.parent / f"{stem}-{i}{suffix}"
        if not candidate.exists():
            return candidate

    return dest  # last resort: overwrite


def move_file(src: Path, dest: Path, dry_run: bool) -> bool:
    if dry_run:
        print(f"  [DRY RUN] {src.name} → {dest.relative_to(VAULT_PATH)}")
        return True
    try:
        shutil.move(str(src), str(dest))
        print(f"  ✓ {src.name} → {dest.relative_to(VAULT_PATH)}")
        return True
    except Exception as e:
        print(f"  ✗ {src.name}: {e}")
        return False


def append_log(entries: list, empty_run: bool, dry_run: bool):
    if dry_run:
        return
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            if empty_run:
                f.write(f"\n## {timestamp} — inbox empty\n")
            else:
                f.write(f"\n## {timestamp}\n")
                for src_name, dest_rel, reason in entries:
                    f.write(f"- {src_name} → {dest_rel} ({reason})\n")
    except Exception as e:
        print(f"  Warning: log write failed: {e}")


def update_readme(count: int, dry_run: bool):
    if dry_run:
        return
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    try:
        with open(README_FILE, "a", encoding="utf-8") as f:
            f.write(f"\nПоследняя обработка: {timestamp} — обработано {count} файлов\n")
    except Exception:
        pass


def main(dry_run: bool = False):
    files = get_files_to_process()

    if not files:
        print("Inbox empty, nothing to do.")
        append_log([], empty_run=True, dry_run=dry_run)
        return

    print(f"Found {len(files)} file(s). Classifying in one LLM call...")

    try:
        classifications = classify_files_batch(files)
    except Exception as e:
        print(f"LLM classification error: {e}")
        sys.exit(1)

    # Build filename → classification lookup
    lookup = {c["filename"]: c for c in classifications if isinstance(c, dict) and "filename" in c}

    log_entries = []
    moved = 0

    for f in files:
        info = lookup.get(f.name)
        if not info:
            print(f"  ? {f.name}: not in LLM response, skipping")
            continue

        dest_dir = info.get("dest_dir", "Work/Knowledge/")
        reason = info.get("reason", "")
        dest_path = safe_dest_path(dest_dir, f.name)

        if move_file(f, dest_path, dry_run):
            log_entries.append((f.name, str(dest_path.relative_to(VAULT_PATH)), reason))
            moved += 1

    append_log(log_entries, empty_run=False, dry_run=dry_run)
    update_readme(moved, dry_run=dry_run)
    print(f"Done: {moved}/{len(files)} files moved.")


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(description="Obsidian Inbox Router — batch LLM classifier")
    p.add_argument("--dry-run", action="store_true", help="Show what would happen without moving files")
    args = p.parse_args()
    main(dry_run=args.dry_run)
