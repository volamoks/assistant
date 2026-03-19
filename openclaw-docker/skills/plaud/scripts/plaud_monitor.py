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
import logging
import argparse
from pathlib import Path
from datetime import datetime, time as dt_time
from typing import Optional, Dict, Any

# ── Paths (configurable via env) ───────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
SKILLS_DIR = Path(__file__).resolve().parent

sys.path.insert(0, str(SKILLS_DIR))

# Environment variables with sensible defaults
PLAUD_TOKEN = os.getenv("PLAUD_TOKEN")
DATA_DIR = Path(os.getenv("PLAUD_DATA_DIR", str(PROJECT_ROOT / "data")))
STATE_FILE = Path(os.getenv("PLAUD_STATE_FILE", str(DATA_DIR / "plaud_state.json")))
VAULT_ROOT = Path(os.getenv("USER_VAULT_PATH", "/data/obsidian"))
WORK_TRANSCRIPTS_DIR = Path(os.getenv(
    "PLAUD_TRANSCRIPTS_DIR",
    str(VAULT_ROOT / "Work" / "Transcripts")
))
LOG_FILE = Path(os.getenv("PLAUD_LOG_FILE", "/tmp/plaud_monitor.log"))

# Telegram notifications (optional)
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Create directories
DATA_DIR.mkdir(parents=True, exist_ok=True)
WORK_TRANSCRIPTS_DIR.mkdir(parents=True, exist_ok=True)

if not PLAUD_TOKEN:
    print("Error: PLAUD_TOKEN not set")
    sys.exit(1)

# ── Imports ─────────────────────────────────────────────────────────────────
from plaud_client import PlaudClient
from plaud_analyze import extract_summary_and_tasks
from plaud_vikunja import push_tasks_to_vikunja
from plaud_obsidian import format_obsidian_note


# ── Structured Logging Setup ───────────────────────────────────────────────
class StructuredLogger:
    """Logger with timestamp, level, and structured message output."""
    
    def __init__(self, name: str, log_level: str = "INFO", log_file: Optional[Path] = None):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))
        self.logger.handlers = []  # Clear any existing handlers
        
        # Console handler with structured format
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        ))
        self.logger.addHandler(console_handler)
        
        # File handler (optional)
        if log_file:
            try:
                file_handler = logging.FileHandler(log_file)
                file_handler.setFormatter(logging.Formatter(
                    '%(asctime)s | %(levelname)-8s | %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S'
                ))
                self.logger.addHandler(file_handler)
            except Exception as e:
                console_handler.setFormatter(logging.Formatter(
                    '%(asctime)s | %(levelname)-8s | %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S'
                ))
                self.logger.warning(f"Could not create log file: {e}")
        
        self._log_level = log_level.upper()
    
    def debug(self, msg: str):
        self.logger.debug(msg)
    
    def info(self, msg: str):
        self.logger.info(msg)
    
    def warning(self, msg: str):
        self.logger.warning(msg)
    
    def error(self, msg: str):
        self.logger.error(msg)
    
    def critical(self, msg: str):
        self.logger.critical(msg)
    
    def set_level(self, level: str):
        self.logger.setLevel(getattr(logging, level.upper(), logging.INFO))
        self._log_level = level.upper()


# Global logger instance
logger = None


# ── Telegram Notifications ─────────────────────────────────────────────────
def send_telegram_message(message: str, critical: bool = False) -> bool:
    """Send message via Telegram if credentials are configured."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return False
    
    try:
        import requests
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": f"{'🔴 CRITICAL' if critical else 'ℹ️'} Plaud Monitor\n\n{message}",
            "parse_mode": "Markdown"
        }
        resp = requests.post(url, json=payload, timeout=10)
        return resp.status_code == 200
    except Exception as e:
        if logger:
            logger.warning(f"Telegram notification failed: {e}")
        return False


# ── Healthcheck Status ─────────────────────────────────────────────────────
class HealthCheck:
    """Track last run status for healthcheck endpoint."""
    
    def __init__(self):
        self.last_run_time: Optional[float] = None
        self.last_run_status: str = "unknown"  # success, error, skipped
        self.last_run_message: str = ""
        self.recordings_processed: int = 0
        self.recordings_skipped: int = 0
        self.errors: list = []
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.last_run_status,
            "last_run_time": datetime.fromtimestamp(self.last_run_time).isoformat() if self.last_run_time else None,
            "last_run_message": self.last_run_message,
            "recordings_processed": self.recordings_processed,
            "recordings_skipped": self.recordings_skipped,
            "errors": self.errors[-5:]  # Last 5 errors
        }


healthcheck = HealthCheck()


# ── State helpers ─────────────────────────────────────────────────────────────

def load_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"Failed to load state: {e}")
            return {}
    return {}


def save_state(state: dict):
    """Save state to file. Creates parent directories and handles interruptions."""
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        # Write to temp file first, then atomic rename
        temp_file = STATE_FILE.with_suffix('.json.tmp')
        temp_file.write_text(json.dumps(state, indent=2))
        temp_file.rename(STATE_FILE)
    except Exception as e:
        logger.error(f"Failed to save state: {e}")


# ── Working hours ─────────────────────────────────────────────────────────────

def is_within_working_hours() -> bool:
    try:
        import zoneinfo
        tz = zoneinfo.ZoneInfo("Asia/Tashkent")
        now = datetime.now(tz).time()
        return dt_time(9, 0) <= now <= dt_time(20, 0)
    except Exception:
        return True  # fail open


# ── Determine note subdirectory based on recording type ─────────────────────
def get_transcript_subdir(filename: str) -> Path:
    """Determine which subdirectory to save the note in based on filename."""
    filename_lower = filename.lower()
    
    if "call" in filename_lower or "звонок" in filename_lower:
        return WORK_TRANSCRIPTS_DIR / "Calls"
    elif "meeting" in filename_lower or "встреча" in filename_lower or "совещание" in filename_lower:
        return WORK_TRANSCRIPTS_DIR / "Meetings"
    elif "idea" in filename_lower or "идея" in filename_lower:
        return WORK_TRANSCRIPTS_DIR / "Ideas"
    else:
        # Default to Meetings for unclassified
        return WORK_TRANSCRIPTS_DIR / "Meetings"


# ── Main ──────────────────────────────────────────────────────────────────────

def main(dry_run: bool = False, limit: int = None, log_level: str = "INFO", healthcheck_mode: bool = False):
    global logger
    
    # Initialize logger
    logger = StructuredLogger("plaud_monitor", log_level=log_level, log_file=LOG_FILE)
    
    # Healthcheck mode - just return JSON status
    if healthcheck_mode:
        print(json.dumps(healthcheck.to_dict(), indent=2))
        return
    
    logger.info("Starting Plaud Monitor check...")
    
    # Check working hours
    if not is_within_working_hours():
        logger.info("Outside working hours (9:00-20:00 Tashkent), skipping...")
        healthcheck.last_run_status = "skipped"
        healthcheck.last_run_message = "Outside working hours"
        healthcheck.last_run_time = time.time()
        return

    # Initialize client
    try:
        client = PlaudClient()  # reads PLAUD_TOKEN + PLAUD_API_DOMAIN from env
    except Exception as e:
        logger.error(f"Failed to initialize Plaud client: {e}")
        healthcheck.last_run_status = "error"
        healthcheck.last_run_message = f"Client init failed: {e}"
        healthcheck.last_run_time = time.time()
        healthcheck.errors.append(str(e))
        send_telegram_message(f"Failed to initialize: {e}", critical=True)
        return

    # ── Fetch file list ─────────────────────────────────────────────────────
    try:
        files = client.list_files()
    except Exception as e:
        logger.error(f"Error fetching file list: {e}")
        healthcheck.last_run_status = "error"
        healthcheck.last_run_message = f"Fetch failed: {e}"
        healthcheck.last_run_time = time.time()
        healthcheck.errors.append(str(e))
        send_telegram_message(f"Error fetching file list: {e}", critical=True)
        return

    if not files:
        logger.info("No files found.")
        healthcheck.last_run_status = "success"
        healthcheck.last_run_message = "No files found"
        healthcheck.last_run_time = time.time()
        return

    if limit is not None:
        files = files[:limit]

    state = load_state()
    processed_count = 0
    skipped_no_transcript = 0
    
    # Track errors for summary
    run_errors = []

    for f in files:
        file_id = f["id"]
        filename = f.get("filename", "Unknown")
        is_trans  = bool(f.get("is_trans"))
        is_summary = bool(f.get("is_summary"))
        edit_time = int(f.get("edit_time", time.time()))

        # Already processed → check if AI summary appeared since last run
        if file_id in state:
            try:
                if is_summary and not state[file_id].get("has_ai_summary"):
                    _try_append_ai_summary(client, file_id, state, dry_run, logger)
            except Exception as e:
                logger.warning(f"Error checking AI summary for {file_id[:8]}: {e}")
                run_errors.append(f"{file_id[:8]}: {e}")
            continue

        # Not yet processed
        logger.info(f"[{file_id[:8]}] New recording: {filename}")

        if not is_trans:
            logger.info(f"  → No Plaud transcript yet (is_trans=False). Will retry later.")
            skipped_no_transcript += 1
            continue

        if dry_run:
            logger.info(f"  → (DRY RUN) Would process with native transcript.")
            continue

        # ── Fetch native transcript ──────────────────────────────────────────
        logger.info(f"  → Fetching native Plaud transcript...")
        try:
            detail_body = client.get_file_details(file_id)
        except Exception as e:
            logger.error(f"  → Failed to fetch detail: {e}")
            run_errors.append(f"{file_id[:8]} detail: {e}")
            continue

        data = detail_body.get("data") or {}

        # Try trans_result first (legacy), then fall back to content_list
        transcript = ""
        segments = []
        trans_result = data.get("trans_result")
        if trans_result and isinstance(trans_result, dict):
            segments = trans_result.get("segments", [])

        if not segments:
            # Fetch from S3 URL in content_list
            content_list = data.get("content_list", [])
            for item in content_list:
                if item.get("data_type") == "transaction" and item.get("task_status") == 1:
                    data_link = item.get("data_link")
                    if data_link:
                        try:
                            import requests as req
                            resp = req.get(data_link, timeout=30)
                            if resp.status_code == 200:
                                segments = resp.json()
                                logger.info(f"  → Fetched {len(segments)} segments from S3")
                                break
                        except Exception as se:
                            logger.error(f"  → Failed to download transcript: {se}")
                            run_errors.append(f"{file_id[:8]} S3: {se}")
                            break

        if not segments:
            logger.warning(f"  → No transcript available for {file_id[:8]}. Skipping.")
            skipped_no_transcript += 1
            continue

        transcript_text = " ".join(s.get("content", s.get("text", "")) for s in segments if s.get("content") or s.get("text"))
        logger.info(f"  → Got transcript: {len(transcript_text)} chars, {len(segments)} segments")

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
            logger.info(f"  → Found Plaud AI summary ({len(ai_summary_text)} chars)")

        # ── LLM analysis + task extraction ───────────────────────────────────
        logger.info(f"  → Analyzing transcript with LLM...")
        try:
            analysis = extract_summary_and_tasks(transcript_text)
        except Exception as e:
            logger.error(f"  → Analysis error: {e}")
            analysis = f"Error generating summary: {e}"
            run_errors.append(f"{file_id[:8]} analysis: {e}")

        # ── Push tasks to Vikunja ──────────────────────────────────────────
        vikunja_success = False
        try:
            tasks_added = push_tasks_to_vikunja(analysis, filename, dry_run=False)
            
            # Verify task creation (function returns count, 0 means no tasks or failure)
            if tasks_added and tasks_added > 0:
                vikunja_success = True
                logger.info(f"  → Pushed {tasks_added} tasks to Vikunja ✓")
            elif tasks_added == 0:
                logger.info(f"  → No tasks to push to Vikunja")
            else:
                logger.warning(f"  → Vikunja push returned unexpected value: {tasks_added}")
        except Exception as e:
            logger.error(f"  → Vikunja error: {e}")
            run_errors.append(f"{file_id[:8]} Vikunja: {e}")

        # ── Save Obsidian note ─────────────────────────────────────────────
        created_dt = datetime.fromtimestamp(edit_time)
        
        # Determine subdirectory based on recording type
        subdir = get_transcript_subdir(filename)
        subdir.mkdir(parents=True, exist_ok=True)
        
        note_filename = f"Plaud_{created_dt.strftime('%Y-%m-%d_%H%M')}_{file_id[:8]}.md"
        note_path = subdir / note_filename

        content_list = data.get("content_list") or []
        note_content = format_obsidian_note(
            file_id, filename, edit_time, transcript, analysis, content_list
        )

        # Append Plaud's own AI summary if available
        if ai_summary_text:
            note_content += f"\n\n## Plaud AI Summary\n\n{ai_summary_text}\n"

        try:
            note_path.write_text(note_content)
            logger.info(f"  → Saved note: {note_path}")
        except Exception as e:
            logger.error(f"  → Failed to save note: {e}")
            run_errors.append(f"{file_id[:8]} note save: {e}")
            # Continue - don't lose the state
        
        # ── Update state (save after each successful processing) ───────────
        try:
            state[file_id] = {
                "processed_at": time.time(),
                "obsidian_file": str(note_path),
                "has_native_transcript": True,
                "has_ai_summary": bool(ai_summary_text),
                "transcript_length": len(transcript_text),
                "vikunja_tasks": tasks_added if vikunja_success else 0,
            }
            save_state(state)  # Save after each successful recording
            processed_count += 1
        except Exception as e:
            logger.error(f"  → Failed to save state: {e}")
            run_errors.append(f"{file_id[:8]} state: {e}")
        
        # Clean up: remove local audio file if it exists (to save disk space)
        audio_path = f"/tmp/{file_id}.mp3"
        if os.path.exists(audio_path):
            try:
                os.remove(audio_path)
                logger.debug(f"  → Deleted local audio file: {audio_path}")
            except Exception as e:
                logger.warning(f"  → Could not delete audio file: {e}")

    # ── Summary ───────────────────────────────────────────────────────────
    healthcheck.last_run_time = time.time()
    healthcheck.recordings_processed = processed_count
    healthcheck.recordings_skipped = skipped_no_transcript
    
    if run_errors:
        healthcheck.last_run_status = "error"
        healthcheck.last_run_message = f"Processed {processed_count}, skipped {skipped_no_transcript}, {len(run_errors)} errors"
        healthcheck.errors.extend(run_errors)
    else:
        healthcheck.last_run_status = "success"
        healthcheck.last_run_message = f"Processed {processed_count}, skipped {skipped_no_transcript}"
    
    if processed_count > 0:
        logger.info(f"✅ Processed {processed_count} new recording(s).")
    if skipped_no_transcript > 0:
        logger.info(f"⏳ Skipped {skipped_no_transcript} recording(s) waiting for Plaud transcript.")
    if run_errors:
        logger.warning(f"⚠️ Encountered {len(run_errors)} error(s) during run.")
    
    # Send Telegram notification with run summary
    if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
        summary_msg = (
            f"Run complete:\n"
            f"• Processed: {processed_count}\n"
            f"• Skipped: {skipped_no_transcript}\n"
            f"• Errors: {len(run_errors)}"
        )
        send_telegram_message(summary_msg, critical=bool(run_errors))


def _try_append_ai_summary(client: PlaudClient, file_id: str, state: dict, dry_run: bool, logger):
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
            logger.info(f"  → (DRY RUN) Would append AI summary to {note_path_str}")
            return
        with open(note_path_str, "a") as nf:
            nf.write(f"\n\n## Plaud AI Summary\n\n{ai_text}\n")
        state[file_id]["has_ai_summary"] = True
        save_state(state)
        logger.info(f"  → Appended Plaud AI summary to existing note.")
    except Exception as e:
        logger.warning(f"  → Could not fetch AI summary: {e}")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Plaud Monitor")
    p.add_argument("--dry-run", action="store_true", help="Simulate processing without making changes")
    p.add_argument("--limit", type=int, default=None, help="Limit number of files to process")
    p.add_argument("--log-level", type=str, default="INFO", 
                   choices=["DEBUG", "INFO", "WARNING", "ERROR"],
                   help="Set logging verbosity")
    p.add_argument("--healthcheck", action="store_true", help="Return JSON status of last run")
    args = p.parse_args()
    
    main(
        dry_run=args.dry_run, 
        limit=args.limit, 
        log_level=args.log_level,
        healthcheck_mode=args.healthcheck
    )
