#!/usr/bin/env python3
"""
Plaud Monitor — processes new recordings using Plaud's native transcripts.

Strategy:
  1. List all recordings via Plaud API
  2. For recordings with is_trans=True (Plaud already transcribed them):
     → fetch trans_result.segments directly — no audio download needed
  3. For recordings without a native transcript yet:
     → skip with a note (will pick up next run when transcript is ready)
  4. Analyze transcript with LLM, extract tasks → Vikunja + Obsidian note

Working hours: 9:00–20:00 Tashkent time
"""

import os
import sys
import json
import time
from pathlib import Path
from datetime import datetime, time as dt_time

# ── Paths ────────────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
SKILLS_DIR = Path(__file__).resolve().parent

sys.path.insert(0, str(SKILLS_DIR))

PLAUD_TOKEN = os.getenv("PLAUD_TOKEN")
if not PLAUD_TOKEN:
    print("Error: PLAUD_TOKEN not set")
    sys.exit(1)

DATA_DIR = PROJECT_ROOT / "data"
STATE_FILE = DATA_DIR / "plaud_state.json"
INBOX_DIR = Path(os.getenv(
    "USER_VAULT_PATH",
    str(PROJECT_ROOT.parent / "obsidian/vault")
)) / "Inbox"

DATA_DIR.mkdir(parents=True, exist_ok=True)
INBOX_DIR.mkdir(parents=True, exist_ok=True)

# ── Imports ───────────────────────────────────────────────────────────────────
from plaud_client import PlaudClient
from plaud_analyze import extract_summary_and_tasks
from plaud_vikunja import push_tasks_to_vikunja
from plaud_obsidian import format_obsidian_note


# ── State helpers ─────────────────────────────────────────────────────────────

def load_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except json.JSONDecodeError:
            return {}
    return {}


def save_state(state: dict):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))


# ── Working hours ─────────────────────────────────────────────────────────────

def is_within_working_hours() -> bool:
    try:
        import zoneinfo
        tz = zoneinfo.ZoneInfo("Asia/Tashkent")
        now = datetime.now(tz).time()
        return dt_time(9, 0) <= now <= dt_time(20, 0)
    except Exception:
        return True  # fail open


# ── Main ──────────────────────────────────────────────────────────────────────

def main(dry_run: bool = False, limit: int = None):
    if not is_within_working_hours():
        print(f"[{datetime.now()}] Outside working hours (9:00-20:00), skipping...")
        return

    print(f"[{datetime.now()}] Starting Plaud Monitor check...")

    client = PlaudClient()  # reads PLAUD_TOKEN + PLAUD_API_DOMAIN from env

    # ── Fetch file list ───────────────────────────────────────────────────────
    try:
        files = client.list_files()
    except Exception as e:
        print(f"Error fetching file list: {e}")
        return

    if not files:
        print("No files found.")
        return

    if limit is not None:
        files = files[:limit]

    state = load_state()
    processed_count = 0
    skipped_no_transcript = 0

    for f in files:
        file_id = f["id"]
        filename = f.get("filename", "Unknown")
        is_trans  = bool(f.get("is_trans"))
        is_summary = bool(f.get("is_summary"))
        edit_time = int(f.get("edit_time", time.time()))

        # Already processed → check if AI summary appeared since last run
        if file_id in state:
            if is_summary and not state[file_id].get("has_ai_summary"):
                _try_append_ai_summary(client, file_id, state, dry_run)
            continue

        # Not yet processed
        print(f"[{file_id[:8]}] New recording: {filename}")

        if not is_trans:
            print(f"  → No Plaud transcript yet (is_trans=False). Will retry later.")
            skipped_no_transcript += 1
            continue

        if dry_run:
            print(f"  → (DRY RUN) Would process with native transcript.")
            continue

        # ── Fetch native transcript ──────────────────────────────────────────
        print(f"  → Fetching native Plaud transcript...")
        try:
            detail_body = client.get_file_details(file_id)
        except Exception as e:
            print(f"  → Failed to fetch detail: {e}")
            continue

        data = detail_body.get("data") or {}
        tr = data.get("trans_result") or {}
        segments = tr.get("segments", []) if isinstance(tr, dict) else []

        if not segments:
            print(f"  → trans_result empty for {file_id[:8]} despite is_trans=True. Skipping.")
            skipped_no_transcript += 1
            continue

        transcript = " ".join(s.get("text", "") for s in segments if s.get("text"))
        print(f"  → Got transcript: {len(transcript)} chars, {len(segments)} segments")

        # ── AI summary from Plaud (if available) ────────────────────────────
        ai_content = data.get("ai_content") or {}
        ai_summary_text = ""
        if ai_content and isinstance(ai_content, dict):
            # ai_content may have keys like "summary", "action_items", etc.
            for key in ("summary", "full_summary", "content", "overview"):
                if ai_content.get(key):
                    ai_summary_text = str(ai_content[key])
                    break
            if not ai_summary_text:
                ai_summary_text = json.dumps(ai_content, ensure_ascii=False, indent=2)
            print(f"  → Found Plaud AI summary ({len(ai_summary_text)} chars)")

        # ── LLM analysis + task extraction ───────────────────────────────────
        print(f"  → Analysing transcript with LLM...")
        try:
            analysis = extract_summary_and_tasks(transcript)
        except Exception as e:
            print(f"  → Analysis error: {e}")
            analysis = "Error generating summary."

        # ── Push tasks to Vikunja ──────────────────────────────────────────
        try:
            tasks_added = push_tasks_to_vikunja(analysis, filename, dry_run=False)
            if tasks_added > 0:
                print(f"  → Pushed {tasks_added} tasks to Vikunja")
        except Exception as e:
            print(f"  → Vikunja error: {e}")

        # ── Save Obsidian note ─────────────────────────────────────────────
        created_dt = datetime.fromtimestamp(edit_time)
        note_filename = f"Plaud_{created_dt.strftime('%Y-%m-%d_%H%M')}_{file_id[:8]}.md"
        note_path = INBOX_DIR / note_filename

        content_list = data.get("content_list") or []
        note_content = format_obsidian_note(
            file_id, filename, edit_time, transcript, analysis, content_list
        )

        # Append Plaud's own AI summary if available
        if ai_summary_text:
            note_content += f"\n\n## Plaud AI Summary\n\n{ai_summary_text}\n"

        print(f"  → Saving note: {note_filename}")
        note_path.write_text(note_content)

        state[file_id] = {
            "processed_at": time.time(),
            "obsidian_file": str(note_path),
            "has_native_transcript": True,
            "has_ai_summary": bool(ai_summary_text),
            "transcript_length": len(transcript),
        }
        save_state(state)
        processed_count += 1

    # ── Summary ────────────────────────────────────────────────────────────
    if processed_count > 0:
        print(f"✅ Processed {processed_count} new recording(s).")
    if skipped_no_transcript > 0:
        print(f"⏳ Skipped {skipped_no_transcript} recording(s) waiting for Plaud transcript.")


def _try_append_ai_summary(client: PlaudClient, file_id: str, state: dict, dry_run: bool):
    """Append newly available Plaud AI summary to existing Obsidian note."""
    note_path_str = state[file_id].get("obsidian_file")
    if not note_path_str or not Path(note_path_str).exists():
        return
    try:
        detail_body = client.get_file_details(file_id)
        ai = (detail_body.get("data") or {}).get("ai_content")
        if not ai:
            return
        ai_text = ""
        for key in ("summary", "full_summary", "content", "overview"):
            if isinstance(ai, dict) and ai.get(key):
                ai_text = str(ai[key])
                break
        if not ai_text and isinstance(ai, dict):
            ai_text = json.dumps(ai, ensure_ascii=False, indent=2)
        if not ai_text:
            return
        if dry_run:
            print(f"  → (DRY RUN) Would append AI summary to {note_path_str}")
            return
        with open(note_path_str, "a") as nf:
            nf.write(f"\n\n## Plaud AI Summary\n\n{ai_text}\n")
        state[file_id]["has_ai_summary"] = True
        save_state(state)
        print(f"  → Appended Plaud AI summary to existing note.")
    except Exception as e:
        print(f"  → Could not fetch AI summary: {e}")


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(description="Plaud Monitor")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--limit", type=int, default=None)
    args = p.parse_args()
    main(dry_run=args.dry_run, limit=args.limit)
