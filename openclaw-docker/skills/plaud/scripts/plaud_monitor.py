#!/usr/bin/env python3
"""
Plaud Monitor — processes new recordings automatically.

Strategy:
  1. List all recordings via Plaud API
  2. For every new recording (not yet in state):
     a. Download audio
     b. Transcribe via Groq Whisper (PRIMARY path — always, regardless of is_trans)
     c. If native transcript is available (is_trans=True), add it as a bonus section
  3. Analyze with LLM → extract summary + tasks
  4. Write tasks as Obsidian checklist items directly in the transcript note
  5. Save formatted note to Obsidian vault

Working hours: 9:00–20:00 Tashkent time
"""

import os
import sys
import json
import time
import logging
import argparse
import tempfile
import subprocess
from pathlib import Path
from datetime import datetime, time as dt_time
from typing import Optional, Dict, Any, Tuple

# ── Paths (configurable via env) ───────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
SKILLS_DIR   = Path(__file__).resolve().parent

sys.path.insert(0, str(SKILLS_DIR))

# Environment variables with sensible defaults
PLAUD_TOKEN = os.getenv("PLAUD_TOKEN")
DATA_DIR   = Path(os.getenv("PLAUD_DATA_DIR",        str(PROJECT_ROOT / "data")))
STATE_FILE = Path(os.getenv("PLAUD_STATE_FILE",       str(DATA_DIR / "plaud_state.json")))
VAULT_ROOT = Path(os.getenv("USER_VAULT_PATH",        "/data/obsidian"))
WORK_TRANSCRIPTS_DIR = Path(os.getenv(
    "PLAUD_TRANSCRIPTS_DIR",
    str(VAULT_ROOT / "Work" / "Transcripts")
))
LOG_FILE = Path(os.getenv("PLAUD_LOG_FILE", "/tmp/plaud_monitor.log"))

# Telegram notifications (optional)
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID   = os.getenv("TELEGRAM_CHAT_ID")

# Groq (for Whisper transcription)
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_WHISPER_URL = "https://api.groq.com/openai/v1/audio/transcriptions"
GROQ_WHISPER_MODEL = "whisper-large-v3"

# WhisperSTT — import from workspace
AUDIO_WORKSPACE = PROJECT_ROOT / "workspace" / "plaud_audio"
sys.path.insert(0, str(AUDIO_WORKSPACE))
try:
    from audio import WhisperSTT
except ImportError:
    WhisperSTT = None  # will be handled at runtime

# Create directories
DATA_DIR.mkdir(parents=True, exist_ok=True)
WORK_TRANSCRIPTS_DIR.mkdir(parents=True, exist_ok=True)

if not PLAUD_TOKEN:
    print("Error: PLAUD_TOKEN not set")
    sys.exit(1)

# ── Imports ─────────────────────────────────────────────────────────────────
from plaud_client import PlaudClient
from plaud_analyze import extract_summary_and_tasks

from plaud_obsidian import format_obsidian_note


# ── Structured Logging Setup ───────────────────────────────────────────────
class StructuredLogger:
    def __init__(self, name: str, log_level: str = "INFO", log_file: Optional[Path] = None):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))
        self.logger.handlers = []

        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        ))
        self.logger.addHandler(console_handler)

        if log_file:
            try:
                file_handler = logging.FileHandler(log_file)
                file_handler.setFormatter(logging.Formatter(
                    '%(asctime)s | %(levelname)-8s | %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S'
                ))
                self.logger.addHandler(file_handler)
            except Exception as e:
                self.logger.warning(f"Could not create log file: {e}")

    def debug(self, msg: str): self.logger.debug(msg)
    def info(self,  msg: str): self.logger.info(msg)
    def warning(self, msg: str): self.logger.warning(msg)
    def error(self, msg: str): self.logger.error(msg)
    def critical(self, msg: str): self.logger.critical(msg)


logger = None


# ── Telegram Notifications ─────────────────────────────────────────────────
def send_telegram_message(message: str, critical: bool = False) -> bool:
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return False
    try:
        import requests
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        resp = requests.post(url, json={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": f"{'🔴 CRITICAL' if critical else 'ℹ️'} Plaud Monitor\n\n{message}",
            "parse_mode": "Markdown"
        }, timeout=10)
        return resp.status_code == 200
    except Exception as e:
        if logger:
            logger.warning(f"Telegram notification failed: {e}")
        return False


# ── Healthcheck Status ─────────────────────────────────────────────────────
class HealthCheck:
    def __init__(self):
        self.last_run_time: Optional[float] = None
        self.last_run_status: str = "unknown"
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
            "errors": self.errors[-5:],
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
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
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
        return True


# ── Subdirectory routing ───────────────────────────────────────────────────────

def get_transcript_subdir(filename: str) -> Path:
    fn = filename.lower()
    if "call" in fn or "звонок" in fn or "консульт" in fn:
        return WORK_TRANSCRIPTS_DIR / "Calls"
    if "meeting" in fn or "встреча" in fn or "совещан" in fn or "семинар" in fn:
        return WORK_TRANSCRIPTS_DIR / "Meetings"
    if "idea" in fn or "идея" in fn:
        return WORK_TRANSCRIPTS_DIR / "Ideas"
    return WORK_TRANSCRIPTS_DIR / "Meetings"


# ── Audio format helpers ───────────────────────────────────────────────────────

def ensure_mp3(audio_path: str) -> str:
    """
    Convert audio to MP3 if needed using pydub/ffmpeg.
    Returns path to the MP3 file (may be the original if already MP3).
    """
    from pydub import AudioSegment
    import shutil

    ext = Path(audio_path).suffix.lower()
    if ext in (".mp3", ".wav"):
        return audio_path

    base = Path(audio_path).stem
    mp3_path = str(Path(tempfile.gettempdir()) / f"{base}.mp3")

    try:
        seg = AudioSegment.from_file(audio_path)
        seg.export(mp3_path, format="mp3")
        logger.info(f"  → Converted to MP3: {mp3_path}")
        return mp3_path
    except Exception as e:
        logger.warning(f"  → AudioSegment conversion failed ({e}), trying ffmpeg directly...")
        result = subprocess.run(
            ["ffmpeg", "-y", "-i", audio_path, "-acodec", "libmp3lame", "-ab", "128k", mp3_path],
            capture_output=True, text=True, timeout=300
        )
        if result.returncode == 0 and Path(mp3_path).exists():
            return mp3_path
        logger.error(f"  → ffmpeg conversion failed: {result.stderr[:200]}")
        return audio_path  # return original as fallback


# ── Groq Whisper Transcription ────────────────────────────────────────────────

def transcribe_via_groq_whisper(audio_path: str, file_id: str) -> Tuple[str, bool]:
    """
    Transcribe audio file via Groq Whisper API.
    Handles: format conversion, chunking for long files, retries.

    Returns: (transcript_text, success_bool)
    """
    if not GROQ_API_KEY:
        logger.error("  → GROQ_API_KEY not set — cannot transcribe")
        return "", False

    if WhisperSTT:
        try:
            stt = WhisperSTT()
            text = stt.transcribe(audio_path)
            if text and len(text.strip()) > 10:
                logger.info(f"  → WhisperSTT transcribed {len(text)} chars")
                return text, True
            logger.warning("  → WhisperSTT returned empty result, falling back to direct Groq")
        except Exception as e:
            logger.warning(f"  → WhisperSTT failed ({e}), falling back to direct Groq")

    # ── Direct Groq Whisper fallback ──────────────────────────────────────
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
    }

    # Ensure MP3 format
    mp3_path = ensure_mp3(audio_path)
    file_size = os.path.getsize(mp3_path)
    max_size = 25 * 1024 * 1024  # 25 MB

    # Check duration (rough estimate: 128kbps MP3 = ~960KB/min)
    estimated_minutes = file_size / 960 / 1024
    needs_chunking = file_size > max_size or estimated_minutes > 20

    if needs_chunking and not needs_chunking:
        # Actually chunk
        chunks = _chunk_audio(mp3_path, max_size=max_size)
        logger.info(f"  → Splitting into {len(chunks)} chunks for Groq Whisper...")
        transcripts = []
        for i, chunk_path in enumerate(chunks):
            logger.info(f"  → Transcribing chunk {i+1}/{len(chunks)}...")
            ok, text = _groq_whisper_chunk(chunk_path, headers)
            if ok and text:
                transcripts.append(text)
            else:
                transcripts.append(f"[chunk {i+1} failed]")
        return " ".join(transcripts), bool(transcripts)

    ok, text = _groq_whisper_chunk(mp3_path, headers)
    return text, ok


def _groq_whisper_chunk(audio_path: str, headers: dict, retries: int = 3) -> Tuple[str, bool]:
    """Transcribe a single audio chunk via Groq Whisper."""
    for attempt in range(retries):
        try:
            with open(audio_path, "rb") as f:
                files = {"file": (Path(audio_path).name, f, "audio/mpeg")}
                data = {"model": GROQ_WHISPER_MODEL, "language": "ru"}

                import requests as req
                resp = req.post(GROQ_WHISPER_URL, headers=headers, files=files, data=data, timeout=120)

                if resp.status_code == 429:
                    wait = int(resp.headers.get("Retry-After", 30))
                    logger.info(f"  → Groq rate limited, waiting {wait}s...")
                    time.sleep(wait)
                    continue

                if resp.status_code != 200:
                    logger.error(f"  → Groq Whisper error {resp.status_code}: {resp.text[:200]}")
                    resp.raise_for_status()

                result = resp.json()
                text = result.get("text", "").strip()
                return text, True

        except Exception as e:
            if attempt < retries - 1:
                wait = 2 ** attempt
                logger.warning(f"  → Groq Whisper attempt {attempt+1} failed: {e}. Retrying in {wait}s...")
                time.sleep(wait)
            else:
                logger.error(f"  → Groq Whisper failed after {retries} attempts: {e}")
                return "", False

    return "", False


def _chunk_audio(audio_path: str, max_size: int = 25 * 1024 * 1024) -> list:
    """
    Split audio file into chunks using pydub.
    Returns list of chunk file paths.
    """
    try:
        from pydub import AudioSegment
    except ImportError:
        logger.warning("  → pydub not available for chunking, using ffmpeg")
        return _chunk_audio_ffmpeg(audio_path)

    seg = AudioSegment.from_file(audio_path)
    duration_ms = len(seg)
    # Estimate: 20 min per chunk for safety with Groq free tier
    chunk_duration_ms = 20 * 60 * 1000

    chunks = []
    temp_dir = tempfile.gettempdir()
    for i in range(0, duration_ms, chunk_duration_ms):
        chunk = seg[i:i + chunk_duration_ms]
        chunk_path = str(Path(temp_dir) / f"chunk_{i//chunk_duration_ms:03d}.mp3")
        chunk.export(chunk_path, format="mp3")
        chunks.append(chunk_path)

    return chunks


def _chunk_audio_ffmpeg(audio_path: str, max_duration_sec: int = 20 * 60) -> list:
    """Fallback chunker using ffmpeg when pydub is unavailable."""
    chunks = []
    temp_dir = tempfile.gettempdir()

    result = subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_entries", "format=duration", "-of", "csv=p=0", audio_path],
        capture_output=True, text=True
    )
    try:
        total_sec = float(result.stdout.strip())
    except (ValueError, subprocess.CalledProcessError):
        total_sec = 0

    num_chunks = max(1, int(total_sec / max_duration_sec) + 1)
    for i in range(num_chunks):
        start = i * max_duration_sec
        chunk_path = str(Path(temp_dir) / f"chunk_{i:03d}.mp3")
        rc = subprocess.run([
            "ffmpeg", "-y", "-i", audio_path,
            "-ss", str(start), "-t", str(max_duration_sec),
            "-acodec", "libmp3lame", "-ab", "128k", chunk_path
        ], capture_output=True)
        if rc.returncode == 0 and Path(chunk_path).exists():
            chunks.append(chunk_path)

    return chunks


# ── Native transcript fetcher ─────────────────────────────────────────────────

def get_native_transcript(client: PlaudClient, file_id: str, logger) -> Tuple[str, int]:
    """
    Fetch native Plaud transcript if available.
    Returns (transcript_text, segment_count).
    """
    try:
        detail_body = client.get_file_details(file_id)
    except Exception as e:
        logger.warning(f"  → Failed to fetch detail: {e}")
        return "", 0

    data = detail_body.get("data") or {}
    segments = []

    # Try trans_result first (legacy)
    tr = data.get("trans_result")
    if tr and isinstance(tr, dict):
        segments = tr.get("segments", [])

    # Try content_list S3 fetch
    if not segments:
        content_list = data.get("content_list") or []
        for item in content_list:
            if item.get("data_type") == "transaction" and item.get("task_status") == 1:
                link = item.get("data_link")
                if link:
                    try:
                        import requests as req
                        resp = req.get(link, timeout=30)
                        if resp.status_code == 200:
                            segments = resp.json()
                            logger.info(f"  → Fetched {len(segments)} native segments from S3")
                            break
                    except Exception as se:
                        logger.warning(f"  → S3 fetch failed: {se}")

    if not segments:
        return "", 0

    text = " ".join(s.get("content", s.get("text", "")) for s in segments if s.get("content") or s.get("text"))
    return text, len(segments)


# ── Main ──────────────────────────────────────────────────────────────────────

def main(dry_run: bool = False, limit: int = None, log_level: str = "INFO", healthcheck_mode: bool = False):
    global logger
    logger = StructuredLogger("plaud_monitor", log_level=log_level, log_file=LOG_FILE)

    if healthcheck_mode:
        print(json.dumps(healthcheck.to_dict(), indent=2))
        return

    logger.info("Starting Plaud Monitor check...")

    if not is_within_working_hours():
        logger.info("Outside working hours (9:00-20:00 Tashkent), skipping...")
        healthcheck.last_run_status = "skipped"
        healthcheck.last_run_message = "Outside working hours"
        healthcheck.last_run_time = time.time()
        return

    try:
        client = PlaudClient()
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
    skipped_count = 0
    run_errors = []

    for f in files:
        file_id = f["id"]
        filename = f.get("filename", "Unknown")
        is_trans = bool(f.get("is_trans"))
        edit_time = int(f.get("edit_time", time.time()))

        # Skip already-processed
        if file_id in state:
            continue

        logger.info(f"[{file_id[:8]}] New recording: {filename} (native_transcript={is_trans})")

        if dry_run:
            logger.info(f"  → (DRY RUN) Would process via Groq Whisper")
            continue

        audio_path = None
        temp_audio = None

        try:
            # ── STEP 1: Download audio ────────────────────────────────────────
            logger.info(f"  → Downloading audio...")
            try:
                temp_audio = tempfile.NamedTemporaryFile(suffix=".audio", delete=False)
                temp_audio.close()
                audio_path = client.download_audio(file_id, output_path=temp_audio.name)
                if not audio_path or not os.path.exists(audio_path):
                    raise RuntimeError("Download returned empty path or file missing")
                logger.info(f"  → Audio saved: {audio_path} ({os.path.getsize(audio_path)/1024/1024:.1f} MB)")
            except Exception as e:
                logger.error(f"  → Audio download failed: {e}")
                run_errors.append(f"{file_id[:8]} download: {e}")
                continue

            # ── STEP 2: PRIMARY — Groq Whisper transcription ──────────────────
            logger.info(f"  → Transcribing via Groq Whisper...")
            whisper_ok = False
            try:
                transcript_text, whisper_ok = transcribe_via_groq_whisper(audio_path, file_id)
            except Exception as e:
                logger.error(f"  → Whisper transcription failed: {e}")
                run_errors.append(f"{file_id[:8]} whisper: {e}")
                transcript_text = ""

            if not whisper_ok or not transcript_text.strip():
                logger.warning(f"  → No transcript available for {file_id[:8]}. Skipping.")
                skipped_count += 1
                continue

            logger.info(f"  → Got Whisper transcript: {len(transcript_text)} chars")

            # ── STEP 3: BONUS — native transcript (if available) ─────────────
            native_text = ""
            native_segs = 0
            if is_trans:
                logger.info(f"  → Fetching native Plaud transcript (bonus)...")
                native_text, native_segs = get_native_transcript(client, file_id, logger)
                if native_text:
                    logger.info(f"  → Got native transcript: {len(native_text)} chars, {native_segs} segments")

            # ── STEP 4: LLM analysis ──────────────────────────────────────────
            logger.info(f"  → Analyzing transcript with LLM...")
            try:
                analysis = extract_summary_and_tasks(transcript_text)
            except Exception as e:
                logger.error(f"  → Analysis error: {e}")
                analysis = f"Error generating summary: {e}"
                run_errors.append(f"{file_id[:8]} analysis: {e}")

            # ── STEP 5: Extract tasks from LLM analysis ────────────────────────
            # Parse '- [ ] Task Title: description' lines from LLM output
            # and format as Obsidian Tasks plugin items
            import re
            task_lines = re.findall(
                r"^\s*-\s*\[\s*\]\s*(.+)$",
                analysis,
                re.MULTILINE
            )
            tasks_text = ""
            tasks_count = 0
            if task_lines:
                for t in task_lines:
                    clean = re.sub(r"^\s*\*\*(.+?)\*\*\s*:?\s*", r"\1:", t).strip()
                    tasks_text += f"- [ ] {clean} #tasks\n"
                    tasks_count += 1
                logger.info(f"  → Extracted {tasks_count} tasks → embedded in Obsidian note")
            else:
                logger.info(f"  → No tasks found in analysis")

            # ── STEP 6: Save Obsidian note ────────────────────────────────────
            created_dt = datetime.fromtimestamp(edit_time)
            subdir = get_transcript_subdir(filename)
            subdir.mkdir(parents=True, exist_ok=True)
            note_filename = f"Plaud_{created_dt.strftime('%Y-%m-%d_%H%M')}_{file_id[:8]}.md"
            note_path = subdir / note_filename

            content_list = (client.list_files() and []) or []
            note_content = format_obsidian_note(
                file_id, filename, edit_time, transcript_text, analysis,
                tasks=tasks_text, native_links=content_list if content_list else None
            )

            # Append native transcript comparison if available
            if native_text and native_segs > 0:
                note_content += f"\n\n## Native Plaud Transcript (bonus, {native_segs} segments)\n\n{native_text[:5000]}"
                if len(native_text) > 5000:
                    note_content += f"\n\n_... (truncated, {len(native_text)} total chars)_"

            # Append Plaud AI summary if available
            try:
                detail_body = client.get_file_details(file_id)
                ai = (detail_body.get("data") or {}).get("ai_content")
                if ai and isinstance(ai, dict):
                    ai_text = ""
                    for key in ("summary", "full_summary", "content", "overview"):
                        if ai.get(key):
                            ai_text = str(ai[key])
                            break
                    if not ai_text:
                        ai_text = json.dumps(ai, ensure_ascii=False, indent=2)
                    if ai_text:
                        note_content += f"\n\n## Plaud AI Summary\n\n{ai_text}\n"
                        logger.info(f"  → Appended Plaud AI summary ({len(ai_text)} chars)")
            except Exception as ai_e:
                logger.warning(f"  → Could not fetch Plaud AI summary: {ai_e}")

            try:
                note_path.write_text(note_content, encoding="utf-8")
                logger.info(f"  → Saved note: {note_path}")
            except Exception as e:
                logger.error(f"  → Failed to save note: {e}")
                run_errors.append(f"{file_id[:8]} note save: {e}")

            # ── STEP 7: Update state ─────────────────────────────────────────
            try:
                state[file_id] = {
                    "processed_at": time.time(),
                    "obsidian_file": str(note_path),
                    "has_whisper_transcript": bool(transcript_text.strip()),
                    "has_native_transcript": bool(native_text.strip()),
                    "has_ai_summary": "Plaud AI Summary" in note_content,
                    "transcript_length": len(transcript_text),
                    "tasks_created": tasks_count,
                }
                save_state(state)
                processed_count += 1
            except Exception as e:
                logger.error(f"  → Failed to save state: {e}")
                run_errors.append(f"{file_id[:8]} state: {e}")

        finally:
            # Clean up temp audio
            if audio_path and temp_audio and audio_path != temp_audio.name:
                pass  # audio_path already has the real path
            if temp_audio and os.path.exists(temp_audio.name):
                try:
                    os.remove(temp_audio.name)
                except Exception:
                    pass
            if audio_path and os.path.exists(audio_path):
                try:
                    os.remove(audio_path)
                except Exception:
                    pass

    # ── Summary ─────────────────────────────────────────────────────────────
    healthcheck.last_run_time = time.time()
    healthcheck.recordings_processed = processed_count
    healthcheck.recordings_skipped = skipped_count

    if run_errors:
        healthcheck.last_run_status = "error"
        healthcheck.last_run_message = f"Processed {processed_count}, skipped {skipped_count}, {len(run_errors)} errors"
        healthcheck.errors.extend(run_errors)
    else:
        healthcheck.last_run_status = "success"
        healthcheck.last_run_message = f"Processed {processed_count}, skipped {skipped_count}"

    if processed_count > 0:
        logger.info(f"✅ Processed {processed_count} new recording(s).")
    if skipped_count > 0:
        logger.info(f"⏳ Skipped {skipped_count} recording(s).")
    if run_errors:
        logger.warning(f"⚠️ Encountered {len(run_errors)} error(s) during run.")

    if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
        summary_msg = (
            f"Run complete:\n"
            f"• Processed: {processed_count}\n"
            f"• Skipped: {skipped_count}\n"
            f"• Errors: {len(run_errors)}"
        )
        send_telegram_message(summary_msg, critical=bool(run_errors))


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Plaud Monitor")
    p.add_argument("--dry-run", action="store_true", help="Simulate without making changes")
    p.add_argument("--limit", type=int, default=None, help="Limit number of files to process")
    p.add_argument("--log-level", type=str, default="INFO",
                   choices=["DEBUG", "INFO", "WARNING", "ERROR"],
                   help="Set logging verbosity")
    p.add_argument("--healthcheck", action="store_true", help="Return JSON status")
    args = p.parse_args()

    main(
        dry_run=args.dry_run,
        limit=args.limit,
        log_level=args.log_level,
        healthcheck_mode=args.healthcheck,
    )
