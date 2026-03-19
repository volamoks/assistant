#!/usr/bin/env python3
"""
vault_keeper.py — Intelligent Obsidian Vault Caretaker

Design: script-first (no LLM for mechanical work), LLM only for
classification decisions and tag suggestions.

Registry: /home/node/.openclaw/vault-keeper-registry.json
Output:   /home/node/.openclaw/memory/cleanup/YYYY-MM-DD.md
Telegram: only on critical issues (disk >90%, chroma stale >24h, etc.)
"""

import os
import sys
import json
import re
import shutil
import hashlib
import logging
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import URLError

# ── Config ────────────────────────────────────────────────────────────────────
VAULT_PATH      = Path(os.getenv("USER_VAULT_PATH", "/data/obsidian"))
INBOX_DIR       = VAULT_PATH / "Inbox"
BOT_PATH        = Path("/data/bot/openclaw-docker")
REGISTRY_PATH   = Path("/home/node/.openclaw/vault-keeper-registry.json")
REPORT_DIR      = Path("/home/node/.openclaw/memory/cleanup")
OPENCLAW_PATH   = Path("/home/node/.openclaw")

OLLAMA_HOST     = os.getenv("OLLAMA_HOST", "http://host.docker.internal:11434")
LITELLM_HOST    = os.getenv("LITELLM_HOST", "http://litellm:4000")
LITELLM_KEY     = os.getenv("LITELLM_MASTER_KEY", "")
CHROMA_HOST     = os.getenv("CHROMA_HOST", "http://chromadb:8000")

MAX_PREVIEW     = 500   # chars per file for LLM
MAX_FILES_LLM   = 15    # max files per LLM batch
PROTECTED_FILES = {"README.md", "00_HOME.md", "00_STRUCTURE.md"}
ORPHAN_SCRIPTS  = {
    "morning_digest.sh", "morning_system_status.sh",
    "morning_task_briefing.sh", "task_briefing.py", "daily_report.py",
}

# Destination folders mapping
DEST_FOLDERS = {
    "ai": "Work/Knowledge/",
    "llm": "Work/Knowledge/",
    "automation": "Work/Knowledge/",
    "tech": "Work/Knowledge/",
    "ideas": "Work/Knowledge/",
    "fintech": "Work/Knowledge/FinTech/",
    "banking": "Work/Knowledge/FinTech/",
    "payments": "Work/Knowledge/FinTech/",
    "api": "Work/Knowledge/API_Specs/",
    "spec": "Work/Knowledge/API_Specs/",
    "docs": "Work/Knowledge/API_Specs/",
    "task": "Work/Tasks/",
    "todo": "Work/Tasks/",
    "kanban": "Work/Tasks/",
    "career": "Personal/Career/",
    "resume": "Personal/Career/",
    "interview": "Personal/Career/",
    "job": "Personal/Career/",
    "finance": "Personal/Finance/",
    "crypto": "Personal/Finance/",
    "budget": "Personal/Finance/",
    "travel": "Personal/Travel/",
    "books": "Personal/Books/",
    "reading": "Personal/Books/",
    "diary": "Personal/Diary/",
    "personal": "Personal/Diary/",
    "reflection": "Personal/Diary/",
    "bot": "Claw/",
    "claw": "Claw/",
    "automation": "Claw/",
    "diagram": "Assets/",
    "image": "Assets/",
    "media": "Assets/",
}

# ── Logging ───────────────────────────────────────────────────────────────────
log = logging.getLogger("vault_keeper")
logging.basicConfig(
    level=logging.INFO,
    format="[vault_keeper] %(levelname)s: %(message)s",
)
# Suppress noisy libraries
for noisy in ["urllib3", "requests"]:
    logging.getLogger(noisy).setLevel(logging.WARNING)


# ── Registry ──────────────────────────────────────────────────────────────────

def load_registry() -> dict:
    """Load existing registry or return fresh skeleton."""
    if REGISTRY_PATH.exists():
        try:
            with open(REGISTRY_PATH) as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            log.warning("Registry corrupted/invalid, starting fresh: %s", e)
    return fresh_registry()


def fresh_registry() -> dict:
    return {
        "version": 1,
        "last_full_scan": None,
        "last_inbox_scan": None,
        "files": {},
        "unclassified": [],
        "chroma_index": {"last_check": None, "status": "unknown"},
    }


def save_registry(reg: dict):
    tmp = REGISTRY_PATH.with_suffix(".tmp")
    with open(tmp, "w") as f:
        json.dump(reg, f, indent=2, ensure_ascii=False)
    tmp.rename(REGISTRY_PATH)


# ── File Discovery ────────────────────────────────────────────────────────────

def file_hash(path: Path) -> str:
    """Quick hash from mtime+size for change detection."""
    st = path.stat()
    h = hashlib.md5()
    h.update(f"{st.st_mtime}:{st.st_size}".encode())
    return h.hexdigest()


def get_inbox_files(reg: dict) -> list[Path]:
    """Return list of new/modified .md files in Inbox (skip README/protected)."""
    if not INBOX_DIR.exists():
        return []

    now_iso = datetime.now(timezone.utc).isoformat()
    changed = []

    for f in sorted(INBOX_DIR.iterdir()):
        if not f.is_file() or f.suffix != ".md":
            continue
        if f.name in PROTECTED_FILES:
            continue

        key = f"inbox/{f.name}"
        stored = reg["files"].get(key, {})
        current_hash = file_hash(f)
        stored_hash = stored.get("content_hash", "")

        if current_hash != stored_hash:
            changed.append(f)

    return changed


def get_stray_files(reg: dict) -> list[Path]:
    """Return stray .md files in vault root (not in expected list)."""
    ALLOWED_ROOT = {"00_HOME.md", "00_STRUCTURE.md", ".gitignore", "README.md",
                    "Inbox", "Work", "Personal", "Assets", "Claw",
                    "03_System", "Attachments", ".obsidian", ".git", "vault"}
    changed = []
    for f in sorted(VAULT_PATH.iterdir()):
        if not f.is_file() or f.suffix != ".md":
            continue
        if f.name in ALLOWED_ROOT or f.name in PROTECTED_FILES:
            continue
        key = f"stray/{f.name}"
        current_hash = file_hash(f)
        if current_hash != reg["files"].get(key, {}).get("content_hash", "x"):
            changed.append(f)
    return changed


def read_preview(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")[:MAX_PREVIEW].strip()
    except Exception:
        return "(unreadable)"


# ── LLM Classification ────────────────────────────────────────────────────────

LLM_SYSTEM_PROMPT = """\
You are an Obsidian vault classifier and tagger for a Senior PM in FinTech.

For each file: determine the correct destination folder AND suggest 2-5 semantic tags.
Tags must be Obsidian-compatible: lowercase, hyphenated, hierarchical like #topic or #topic/subtopic.

Destination folders (use trailing slash):
- Work/Knowledge/ — AI/LLM/tech research, ideas
- Work/Tasks/ — todos, kanban items
- Work/Knowledge/FinTech/ — banking, payments, financial tech
- Work/Knowledge/API_Specs/ — API specs, tech docs
- Personal/Career/ — resume, job, interviews
- Personal/Finance/ — budget, investments, crypto
- Personal/Travel/ — travel plans
- Personal/Books/ — books, reading notes
- Personal/Diary/ — personal reflections
- Claw/ — bot, automation notes
- Assets/ — diagrams, media

OUTPUT: Return ONLY valid JSON (no markdown fences, no extra text):
{
  "files": [
    {
      "filename": "my-note.md",
      "dest_folder": "Work/Knowledge/",
      "tags": ["api", "fintech", "research"],
      "reason": "brief reason for classification"
    }
  ]
}"""


def call_llm(prompt: str, model: str = "llama3.3") -> dict | None:
    """Call Ollama (primary) or LiteLLM (fallback). Returns parsed JSON or None."""
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": LLM_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.2,
        "format": "json",
    }

    # Try Ollama
    for host, path, key_name in [
        (OLLAMA_HOST, "/api/chat", None),
        (LITELLM_HOST, "/v1/chat/completions", LITELLM_KEY),
    ]:
        try:
            headers = {"Content-Type": "application/json"}
            if key_name:
                headers["Authorization"] = f"Bearer {key_name}"
            data = json.dumps(payload).encode()
            req = Request(f"{host}{path}", data=data, headers=headers)
            with urlopen(req, timeout=60) as r:
                raw = json.loads(r.read())
            content = raw.get("message", {}).get("content", "") or \
                      raw.get("choices", [{}])[0].get("message", {}).get("content", "")
            return json.loads(content.strip())
        except Exception as e:
            log.debug("LLM call to %s failed: %s", host, e)
            continue
    return None


def classify_batch(files: list[Path]) -> list[dict]:
    """Batch-classify up to MAX_FILES_LLM files via single LLM call."""
    if not files:
        return []

    batch = files[:MAX_FILES_LLM]
    parts = []
    for f in batch:
        preview = read_preview(f)
        parts.append(f"=== {f.name} ===\n{preview}")

    prompt = "Classify these Obsidian files:\n\n" + "\n\n".join(parts)

    result = call_llm(prompt)
    if not result:
        return []

    files_list = result.get("files", [])
    if isinstance(files_list, dict):
        # single file response
        files_list = [files_list]

    # Validate: require filename + dest_folder
    validated = []
    for item in files_list:
        if isinstance(item, dict) and item.get("filename") and item.get("dest_folder"):
            item.setdefault("tags", [])
            item.setdefault("reason", "")
            validated.append(item)
    return validated


# ── File Processing ───────────────────────────────────────────────────────────

FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)
TAG_RE = re.compile(r"^\s*tags\s*:\s*\[(.*?)\]|^\s*tags\s*:\s*(.+?)$", re.MULTILINE)
CREATED_RE = re.compile(r"^\s*created\s*:\s*(.+)$", re.MULTILINE)


def read_file_content(path: Path) -> tuple[str, str]:
    """Returns (frontmatter, body) from a markdown file."""
    text = path.read_text(encoding="utf-8", errors="replace")
    m = FRONTMATTER_RE.match(text)
    if m:
        return m.group(1), text[m.end():]
    return "", text


def write_with_frontmatter(path: Path, frontmatter: str, body: str):
    """Write file with frontmatter block."""
    content = f"---\n{frontmatter}\n---\n{body}"
    path.write_text(content, encoding="utf-8")


def merge_tags(existing_fm: str, new_tags: list[str]) -> str:
    """Merge new_tags into existing frontmatter, avoid duplicates."""
    # Extract existing tags
    existing = []
    for line in existing_fm.splitlines():
        m = TAG_RE.match(line)
        if m:
            raw = m.group(1) or m.group(2)
            if raw:
                existing = [t.strip().lstrip("- ").strip("'\"")
                            for t in raw.replace("[", "").replace("]", "").split(",")]
            break

    merged = existing + [t for t in new_tags if t not in existing]

    # Rebuild frontmatter lines (remove old tags line)
    lines = []
    has_tags = False
    for line in existing_fm.splitlines():
        if TAG_RE.match(line):
            if not has_tags:
                lines.append(f"tags: [{', '.join(merged)}]")
                has_tags = True
        else:
            lines.append(line)
    if not has_tags:
        # Append tags before end (find last line)
        lines.append(f"tags: [{', '.join(merged)}]")

    return "\n".join(lines)


def add_created(existing_fm: str) -> str:
    """Add created date to frontmatter if missing."""
    for line in existing_fm.splitlines():
        if CREATED_RE.match(line):
            return existing_fm  # already has created
    today = datetime.now().strftime("%Y-%m-%d")
    return existing_fm.rstrip() + f"\ncreated: {today}\n"


def safe_dest(dest_folder: str, filename: str) -> Path:
    """Resolve destination path, create dirs, handle collisions."""
    dest = VAULT_PATH / dest_folder.strip("/") / filename
    dest.parent.mkdir(parents=True, exist_ok=True)
    if not dest.exists():
        return dest
    stem, suffix = dest.stem, dest.suffix
    for i in range(2, 20):
        candidate = dest.parent / f"{stem}-{i}{suffix}"
        if not candidate.exists():
            return candidate
    return dest


def process_file(src: Path, classification: dict, reg: dict) -> dict:
    """Move file, update frontmatter, update registry. Returns stats dict."""
    filename = classification.get("filename", src.name)
    dest_folder = classification.get("dest_folder", "Work/Knowledge/")
    tags = classification.get("tags", [])
    reason = classification.get("reason", "")
    file_type = "inbox" if "inbox" in str(src).lower() else "stray"
    key = f"{file_type}/{filename}"

    dest = safe_dest(dest_folder, filename)

    # Read + update frontmatter
    try:
        fm, body = read_file_content(src)
        fm = merge_tags(fm, tags)
        fm = add_created(fm)
    except Exception as e:
        log.warning("Could not read %s: %s", src.name, e)
        fm, body = "", src.read_text(encoding="utf-8", errors="replace")

    try:
        shutil.move(str(src), str(dest))
        write_with_frontmatter(dest, fm, body)
    except Exception as e:
        log.error("Move failed for %s → %s: %s", src.name, dest, e)
        return {"moved": False, "tagged": False, "error": str(e)}

    # Update registry
    reg["files"][key] = {
        "path": str(dest.relative_to(VAULT_PATH)),
        "dest_folder": dest_folder,
        "tags": tags,
        "processed_at": datetime.now(timezone.utc).isoformat(),
        "content_hash": file_hash(dest),
        "reason": reason,
    }

    return {"moved": True, "tagged": len(tags) > 0, "dest": str(dest)}


# ── ChromaDB Health ───────────────────────────────────────────────────────────

def check_chroma_status(reg: dict) -> tuple[str, str]:
    """Check ChromaDB health. Returns (status, action)."""
    last_check = reg.get("chroma_index", {}).get("last_check")
    last_status = reg.get("chroma_index", {}).get("status", "unknown")

    # Check if ChromaDB is reachable
    try:
        req = Request(f"{CHROMA_HOST}/api/v1/heartbeat",
                      headers={"Content-Type": "application/json"})
        with urlopen(req, timeout=10):
            pass
        status = "ok"
        action = "none"
    except Exception:
        # Check if it's been stale for >24h
        if last_check and last_status == "stale":
            try:
                last_dt = datetime.fromisoformat(last_check.replace("Z", "+00:00"))
                age_h = (datetime.now(timezone.utc) - last_dt).total_seconds() / 3600
                if age_h > 24:
                    return "stale", "escalate"
            except Exception:
                pass
        status = "unreachable"
        action = "none"

    reg["chroma_index"] = {
        "last_check": datetime.now(timezone.utc).isoformat(),
        "status": status,
    }
    return status, action


def trigger_chroma_reindex() -> bool:
    """Trigger bot_files_index.py --incremental if available."""
    script = BOT_PATH / "scripts/jobs/bot_files_index.py"
    if not script.exists():
        return False
    try:
        result = subprocess.run(
            ["python3", str(script), "--force"],
            capture_output=True, text=True, timeout=120,
        )
        log.info("ChromaDB reindex: %s", result.stdout[:200] if result.stdout else result.stderr[:200])
        return result.returncode == 0
    except Exception as e:
        log.warning("ChromaDB reindex failed: %s", e)
        return False


# ── Technical Cleanup ─────────────────────────────────────────────────────────

def check_disk_space() -> int:
    """Return disk usage percentage for /."""
    try:
        out = subprocess.check_output(["df", "-h", "/"],
                                       text=True, timeout=5)
        pct = int(out.splitlines()[1].split()[4].rstrip("%"))
        return pct
    except Exception:
        return -1


def remove_orphaned_scripts() -> int:
    """Remove known orphaned scripts. Returns count removed."""
    removed = 0
    jobs_dir = BOT_PATH / "scripts/jobs"
    for script in ORPHAN_SCRIPTS:
        p = jobs_dir / script
        if p.exists() and p.is_file():
            try:
                p.unlink()
                log.info("Removed orphan: %s", script)
                removed += 1
            except Exception as e:
                log.warning("Could not remove %s: %s", script, e)
    return removed


def find_empty_files() -> list[str]:
    """Find empty .md files in vault (excluding protected)."""
    PROTECTED = {"Tasks-Dashboard.md", "index.md"}
    empty = []
    try:
        for f in VAULT_PATH.rglob("*.md"):
            if f.name in PROTECTED:
                continue
            if f.stat().st_size == 0:
                empty.append(str(f.relative_to(VAULT_PATH)))
    except Exception as e:
        log.warning("Empty file scan failed: %s", e)
    return empty


def find_broken_wikilinks() -> list[str]:
    """Find broken [[wikilinks]] in vault. Returns list of (file, link) strings."""
    broken = []
    # Build known file stems (lowercase) for fast lookup
    try:
        stems = set()
        for f in VAULT_PATH.rglob("*.md"):
            stems.add(f.stem.lower())
    except Exception:
        return broken

    try:
        for f in VAULT_PATH.rglob("*.md"):
            if "/.git/" in str(f) or "/.obsidian/" in str(f):
                continue
            text = f.read_text(encoding="utf-8", errors="ignore")
            for m in re.finditer(r'\[\[([^]]+)\]\]', text):
                raw = m.group(1).split("|")[0].split("#")[0].strip()
                if raw.lower() not in stems and raw:
                    broken.append(f"[[{raw}]] → not found ({f.relative_to(VAULT_PATH)})")
    except Exception as e:
        log.warning("Wikilink scan failed: %s", e)

    return broken[:30]


def cleanup_old_sessions() -> int:
    """Compress session logs older than 30 days. Returns count."""
    sessions_dir = OPENCLAW_PATH / "agents/main/sessions"
    if not sessions_dir.exists():
        return 0
    removed = 0
    try:
        for f in sessions_dir.glob("*.jsonl"):
            age_days = (datetime.now() - datetime.fromtimestamp(f.stat().st_mtime)).days
            if age_days > 30:
                try:
                    gz = Path(str(f) + ".gz")
                    subprocess.run(["gzip", "-c", str(f)], stdout=open(gz, "wb"),
                                   timeout=30)
                    f.unlink()
                    removed += 1
                except Exception:
                    pass
    except Exception as e:
        log.warning("Session cleanup failed: %s", e)
    return removed


def check_memory_bloat() -> tuple[bool, int]:
    """Check MEMORY.md for bloat. Trim to 50 lines if >100. Returns (trimmed, current_lines)."""
    mem_path = OPENCLAW_PATH / "workspace-main/MEMORY.md"
    if not mem_path.exists():
        return False, 0
    try:
        lines = mem_path.read_text(encoding="utf-8").splitlines()
        if len(lines) > 100:
            trimmed = lines[-50:]
            mem_path.write_text("\n".join(trimmed), encoding="utf-8")
            return True, len(lines)
        return False, len(lines)
    except Exception as e:
        log.warning("MEMORY.md check failed: %s", e)
        return False, 0


# ── Report Writing ────────────────────────────────────────────────────────────

def write_report(report_path: Path, stats: dict):
    """Write cleanup report to markdown file."""
    today = datetime.now().strftime("%Y-%m-%d")
    now = datetime.now().isoformat()
    report_path.parent.mkdir(parents=True, exist_ok=True)

    lines = [
        f"# Vault Keeper Report — {today}",
        "",
        f"_Generated: {now}_",
        "",
        "## Inbox Processing",
        f"- New files: {stats.get('new_files', 0)}",
        f"- Classified: {stats.get('classified', 0)}",
        f"- Moved: {stats.get('moved', 0)}",
        f"- Tagged: {stats.get('tagged', 0)}",
        f"- Unclassified: {stats.get('unclassified', 0)} (see registry)",
        "",
        "## ChromaDB Index",
        f"- Status: {stats.get('chroma_status', 'unknown')}",
        f"- Action taken: {stats.get('chroma_action', 'none')}",
        "",
        "## Technical Cleanup",
        f"- Disk: {stats.get('disk_pct', '?')}%",
        f"- Orphaned scripts removed: {stats.get('orphans_removed', 0)}",
        f"- Empty files found: {stats.get('empty_files', 0)}",
        f"- Broken wikilinks: {stats.get('broken_links', 0)}",
        f"- Old session logs cleaned: {stats.get('sessions_cleaned', 0)}",
        "",
        "## Issues",
    ]

    issues = stats.get("issues", [])
    if issues:
        for iss in issues:
            lines.append(f"- {iss}")
    else:
        lines.append("- None")

    unclassified = stats.get("unclassified_files", [])
    lines += ["", "## Unclassified Files", ""]
    if unclassified:
        for u in unclassified:
            lines.append(f"- `{u}`")
    else:
        lines.append("- None")

    lines += ["", f"_Last full scan: {now}_"]

    report_path.write_text("\n".join(lines), encoding="utf-8")
    log.info("Report written: %s", report_path)


# ── Critical Escalation ───────────────────────────────────────────────────────

def send_telegram_alert(message: str):
    """Send critical escalation to Telegram (direct subprocess call)."""
    notify = BOT_PATH / "skills/telegram/notify.py"
    if notify.exists():
        try:
            subprocess.run(
                ["python3", str(notify), "--message", message,
                 "--chat-id", "6053956251"],
                capture_output=True, timeout=15,
            )
            log.info("Telegram alert sent")
        except Exception as e:
            log.warning("Telegram alert failed: %s", e)


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    today = datetime.now().strftime("%Y-%m-%d")
    report_path = REPORT_DIR / f"{today}.md"

    log.info("=== Vault Keeper run started ===")

    # 1. Load registry
    reg = load_registry()
    now_iso = datetime.now(timezone.utc).isoformat()

    stats = {
        "new_files": 0, "classified": 0, "moved": 0, "tagged": 0,
        "unclassified": 0, "unclassified_files": [],
        "chroma_status": "unknown", "chroma_action": "none",
        "disk_pct": "?", "orphans_removed": 0, "empty_files": 0,
        "broken_links": 0, "sessions_cleaned": 0,
        "issues": [],
    }

    # 2. Find new/modified inbox + stray files
    inbox_files = get_inbox_files(reg)
    stray_files = get_stray_files(reg)
    all_new = inbox_files + stray_files
    stats["new_files"] = len(all_new)

    log.info("New files: %d inbox + %d stray", len(inbox_files), len(stray_files))

    # 3. LLM classification (if new files)
    classifications = []
    if all_new:
        classifications = classify_batch(all_new)
        stats["classified"] = len(classifications)

        if not classifications:
            log.warning("LLM classification failed for %d files", len(all_new))
            # Register as unclassified (no duplicates)
            existing_keys = {u.get("key") for u in reg["unclassified"]}
            for f in all_new:
                key = f"inbox/{f.name}" if INBOX_DIR in f.parents else f"stray/{f.name}"
                if key not in existing_keys:
                    reg["unclassified"].append({
                        "filename": f.name, "key": key,
                        "reason": "LLM classification failed", "detected_at": now_iso,
                    })
                    stats["unclassified"] += 1
                    stats["unclassified_files"].append(f.name)

    # 4. Process each classified file
    processed_keys = set()
    existing_unclassified_keys = {u.get("key") for u in reg["unclassified"]}
    lookup = {c.get("filename"): c for c in classifications}
    for f in all_new:
        key = f"inbox/{f.name}" if INBOX_DIR in f.parents else f"stray/{f.name}"
        info = lookup.get(f.name)
        if not info:
            if key not in processed_keys and key not in existing_unclassified_keys:
                reg["unclassified"].append({
                    "filename": f.name, "key": key,
                    "reason": "not in LLM response", "detected_at": now_iso,
                })
                stats["unclassified"] += 1
                stats["unclassified_files"].append(f.name)
            processed_keys.add(key)
            continue

        result = process_file(f, info, reg)
        if result.get("moved"):
            stats["moved"] += 1
        if result.get("tagged"):
            stats["tagged"] += 1
        if result.get("error"):
            stats["issues"].append(f"{f.name}: {result['error']}")
        processed_keys.add(key)

    reg["last_inbox_scan"] = now_iso

    # 5. ChromaDB health check
    chroma_status, chroma_action = check_chroma_status(reg)
    stats["chroma_status"] = chroma_status
    stats["chroma_action"] = chroma_action

    if chroma_action == "escalate":
        stats["issues"].append(
            f"ChromaDB unreachable + stale for >24h (last check: {reg['chroma_index'].get('last_check', 'unknown')})"
        )
    elif chroma_status == "ok" and all_new:
        # Files changed → trigger incremental reindex
        triggered = trigger_chroma_reindex()
        if triggered:
            stats["chroma_action"] = "re-indexed"
        else:
            stats["chroma_action"] = "checked"

    # 6. Technical cleanup (script-first, no model)
    disk_pct = check_disk_space()
    stats["disk_pct"] = disk_pct
    if disk_pct >= 90:
        stats["issues"].append(f"Disk usage critical: {disk_pct}%")

    stats["orphans_removed"] = remove_orphaned_scripts()
    stats["empty_files"] = len(find_empty_files())
    stats["broken_links"] = len(find_broken_wikilinks())
    stats["sessions_cleaned"] = cleanup_old_sessions()

    trimmed, mem_lines = check_memory_bloat()
    if trimmed:
        stats["issues"].append(f"MEMORY.md was bloated ({mem_lines} lines) — trimmed to 50")

    # Check registry integrity
    try:
        # Simple validation: can we re-read it?
        with open(REGISTRY_PATH) as f:
            json.load(f)
    except Exception:
        stats["issues"].append("Registry was corrupted — regenerated")
        reg = fresh_registry()

    reg["last_full_scan"] = now_iso

    # 7. Save registry
    save_registry(reg)

    # 8. Write report
    write_report(report_path, stats)
    log.info("Report: %s", report_path)

    # 9. Critical escalation only
    critical = (
        disk_pct >= 90 or
        chroma_action == "escalate" or
        any("corrupted" in i.lower() for i in stats["issues"])
    )

    if critical:
        msg = (
            f"[🧹 Vault Keeper — {today}]\n"
            f"Disk: {disk_pct}% | Files processed: {stats['moved']} | "
            f"ChromaDB: {chroma_status}\n"
            f"📋 Full report: memory/cleanup/"
        )
        send_telegram_alert(msg)

    # Summary to stdout
    log.info(
        "Done: %d new, %d moved, %d tagged, %d unclassified | "
        "Disk: %s%% | ChromaDB: %s | Issues: %d",
        stats["new_files"], stats["moved"], stats["tagged"],
        stats["unclassified"], disk_pct, chroma_status, len(stats["issues"]),
    )

    return 0 if not stats["issues"] else 0  # always exit 0 (silent unless critical)


if __name__ == "__main__":
    sys.exit(main())
