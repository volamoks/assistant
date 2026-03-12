#!/usr/bin/env python3
"""
bot_files_index.py — Index bot's own files into ChromaDB 'bot_files' collection.

Indexes:
  - SOUL_*.md prompts  → /home/node/.openclaw/prompts/ (type=prompt)
  - workspace context  → AGENTS.md, BACKLOG.md, IDENTITY.md (type=context)
  - scripts/*.{sh,py}  → automation scripts (type=script)
  - scripts/jobs/*.{sh,py}                  (type=script)

Incremental: skips unchanged files (mtime+size hash).

Usage (inside container):
    python3 /data/bot/openclaw-docker/scripts/jobs/bot_files_index.py
    python3 /data/bot/openclaw-docker/scripts/jobs/bot_files_index.py --force
    python3 /data/bot/openclaw-docker/scripts/jobs/bot_files_index.py --dry-run
"""

import os
import sys
import json
import time
import hashlib
import argparse
import re
import urllib.request
import urllib.error
from pathlib import Path

# ─── Config ───────────────────────────────────────────────────────────────────
BOT_DIR            = Path(os.environ.get("BOT_DIR",           "/data/bot/openclaw-docker"))
PROMPTS_DIR        = Path(os.environ.get("PROMPTS_DIR",       "/home/node/.openclaw/prompts"))
WORKSPACE          = Path(os.environ.get("WORKSPACE",         "/home/node/.openclaw/workspace"))
LITELLM_HOST       = os.environ.get("LITELLM_HOST",           "http://litellm:4000")
LITELLM_MASTER_KEY = os.environ.get("LITELLM_MASTER_KEY",     "")
OLLAMA_HOST        = os.environ.get("OLLAMA_HOST",            "http://host.docker.internal:11434")
CHROMA_HOST        = os.environ.get("CHROMA_HOST",            "http://chromadb:8000")
COLLECTION         = "bot_files"
EMBED_MODEL        = "nomic-embed-text"
COLLECTION_META = {"type": "bot_files", "description": "Bot SOUL prompts, context docs, and scripts"}

SCAN_TARGETS = [
    # (directory, glob, file_type, description_prefix)
    # Agent persona SOUL files — correct path is prompts/, NOT workspace/
    (PROMPTS_DIR,         "SOUL_*.md",          "prompt",   "Agent persona: "),
    # Workspace context docs useful for agent self-awareness
    # Note: BACKLOG.md is a symlink to obsidian — indexed there via obsidian_vault
    (WORKSPACE,           "AGENTS.md",          "context",  "Agents config: "),
    (WORKSPACE,           "IDENTITY.md",        "context",  "Bot identity: "),
    # Automation scripts
    (BOT_DIR / "scripts", "*.sh",               "script",   "Script: "),
    (BOT_DIR / "scripts", "*.py",               "script",   "Script: "),
    (BOT_DIR / "scripts/jobs", "*.sh",          "script",   "Cron job: "),
    (BOT_DIR / "scripts/jobs", "*.py",          "script",   "Cron job: "),
]

# ─── Helpers ──────────────────────────────────────────────────────────────────

def log(msg: str):
    print(f"[bot-files-index] {msg}", flush=True)

def http_post(url: str, data: dict) -> dict:
    body = json.dumps(data).encode()
    req = urllib.request.Request(url, data=body,
                                  headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())

def http_get(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=30) as r:
        return json.loads(r.read())

def file_hash(path: Path) -> str:
    h = hashlib.md5()
    h.update(str(path.stat().st_mtime).encode())
    h.update(str(path.stat().st_size).encode())
    return h.hexdigest()

# ─── File parsing ─────────────────────────────────────────────────────────────

def parse_prompt_file(path: Path) -> dict:
    """Parse SOUL_*.md: extract role, key topics from content."""
    text = path.read_text(encoding="utf-8", errors="replace")
    name = path.stem  # e.g. SOUL_FINANCE

    # Role from first non-empty line or H1
    role = ""
    for line in text.splitlines()[:10]:
        line = line.strip()
        if line.startswith("# "):
            role = line[2:].strip()
            break
        elif line and not line.startswith("#"):
            role = line[:100]
            break

    # First paragraph as description
    description = ""
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    if paragraphs:
        # Skip if it's just a heading
        first = paragraphs[0].lstrip("#").strip()
        description = first[:400]

    # Extract keywords (words after "- " in first 30 lines)
    lines = text.splitlines()[:30]
    keywords = []
    for line in lines:
        m = re.match(r"^\s*[-*]\s+(.+)", line)
        if m:
            keywords.append(m.group(1).strip()[:60])

    return {
        "name": name,
        "role": role or name,
        "description": description,
        "keywords": keywords[:8],
        "full_text": text[:3000],
    }


def parse_script_file(path: Path) -> dict:
    """Parse .sh/.py: extract shebang description, purpose, usage."""
    text = path.read_text(encoding="utf-8", errors="replace")
    name = path.name

    description = ""
    usage = ""

    lines = text.splitlines()
    for line in lines[:20]:
        # Description comment
        m = re.match(r"^#\s*(.+\.py|\.sh)\s*[—-]+\s*(.+)$", line)
        if m:
            description = m.group(2).strip()
            break
        m = re.match(r'^"""(.+?)"""', line, re.DOTALL)
        if m:
            description = m.group(1).strip()[:200]
            break
        # First descriptive comment
        if line.startswith("# ") and len(line) > 15 and not line.startswith("#!"):
            candidate = line[2:].strip()
            if len(candidate) > 20 and not candidate.startswith("Usage"):
                description = candidate[:200]
                break

    # Extract Usage: line
    for line in lines[:40]:
        if re.match(r"#.*[Uu]sage:", line) or re.match(r"Usage:", line):
            usage = line.strip().lstrip("#").strip()
            break

    # First docstring for Python
    if not description and path.suffix == ".py":
        doc_match = re.search(r'"""(.+?)"""', text[:500], re.DOTALL)
        if doc_match:
            description = doc_match.group(1).strip().split("\n")[0][:200]

    return {
        "name": name,
        "description": description or f"Script: {name}",
        "usage": usage,
        "full_text": text[:2000],
    }


# ─── Embedding ────────────────────────────────────────────────────────────────

def _http_post_with_headers(url: str, data: dict, headers: dict) -> dict:
    body = json.dumps(data).encode()
    req = urllib.request.Request(url, data=body, headers=headers)
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())

def get_embedding(text: str) -> list | None:
    """Get embedding via LiteLLM (primary) with Ollama fallback."""
    # ── Primary: LiteLLM (OpenAI-compatible) ──
    try:
        headers = {"Content-Type": "application/json"}
        if LITELLM_MASTER_KEY:
            headers["Authorization"] = f"Bearer {LITELLM_MASTER_KEY}"
        resp = _http_post_with_headers(
            f"{LITELLM_HOST}/embeddings",
            {"model": EMBED_MODEL, "input": text},
            headers
        )
        emb = resp.get("data", [{}])[0].get("embedding")
        if emb:
            return emb
    except Exception:
        pass
    # ── Fallback: Direct Ollama ──
    try:
        resp = http_post(f"{OLLAMA_HOST}/api/embeddings",
                         {"model": EMBED_MODEL, "prompt": text})
        return resp.get("embedding")
    except Exception as e:
        log(f"  Embedding error (both LiteLLM and Ollama failed): {e}")
        return None

# ─── ChromaDB ─────────────────────────────────────────────────────────────────

def get_or_create_collection() -> str:
    try:
        data = http_get(f"{CHROMA_HOST}/api/v1/collections/{COLLECTION}")
        col_id = data.get("id")
        if col_id:
            return col_id
    except Exception:
        pass
    data = http_post(f"{CHROMA_HOST}/api/v1/collections",
                     {"name": COLLECTION, "metadata": COLLECTION_META})
    return data["id"]

def get_existing_ids(col_id: str) -> set:
    try:
        data = http_post(f"{CHROMA_HOST}/api/v1/collections/{col_id}/get",
                         {"include": []})
        return set(data.get("ids", []))
    except Exception as e:
        log(f"Could not get existing IDs: {e}")
        return set()

def upsert_doc(col_id, doc_id, document, metadata, embedding):
    http_post(f"{CHROMA_HOST}/api/v1/collections/{col_id}/upsert", {
        "ids": [doc_id],
        "documents": [document],
        "metadatas": [metadata],
        "embeddings": [embedding],
    })

def delete_ids(col_id: str, ids: list):
    if ids:
        http_post(f"{CHROMA_HOST}/api/v1/collections/{col_id}/delete", {"ids": ids})

# ─── Main ─────────────────────────────────────────────────────────────────────

def collect_files() -> list[tuple[Path, str, str]]:
    """Returns list of (path, file_type, prefix)."""
    results = []
    for directory, pattern, ftype, prefix in SCAN_TARGETS:
        d = Path(directory)
        if not d.exists():
            log(f"  Skip (not found): {d}")
            continue
        matches = sorted(d.glob(pattern))
        for f in matches:
            if f.is_file():
                results.append((f, ftype, prefix))
    return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="List files only")
    parser.add_argument("--force", action="store_true", help="Re-index all files")
    args = parser.parse_args()

    files = collect_files()
    log(f"Found {len(files)} files to index")

    if args.dry_run:
        for path, ftype, _ in files:
            print(f"  [{ftype}] {path}")
        return

    col_id = get_or_create_collection()
    log(f"Collection UUID: {col_id}")

    existing_ids = get_existing_ids(col_id)
    log(f"Already indexed: {len([i for i in existing_ids if '::hash::' not in i])} docs")

    indexed = 0
    skipped = 0
    errors = 0

    for path, ftype, prefix in files:
        doc_id = f"{ftype}::{path.name}"
        hash_id = f"{doc_id}::hash::{file_hash(path)}"

        # Skip if unchanged
        if not args.force and hash_id in existing_ids:
            skipped += 1
            continue

        log(f"Indexing [{ftype}] {path.name}")

        if ftype == "prompt":
            parsed = parse_prompt_file(path)
            keywords_str = " | ".join(parsed["keywords"]) if parsed["keywords"] else ""
            embed_text = (
                f"Agent persona: {parsed['name']}\n"
                f"Role: {parsed['role']}\n"
                f"{parsed['description']}\n"
                f"Topics: {keywords_str}\n\n"
                f"{parsed['full_text'][:1500]}"
            )
            metadata = {
                "type": ftype,
                "name": parsed["name"],
                "role": parsed["role"][:200],
                "description": parsed["description"][:400],
                "path": str(path),
            }
        elif ftype == "context":
            # Workspace context docs (AGENTS.md, BACKLOG.md, IDENTITY.md)
            text = path.read_text(encoding="utf-8", errors="replace")
            heading = ""
            for line in text.splitlines()[:5]:
                if line.startswith("# "):
                    heading = line[2:].strip()
                    break
            embed_text = (
                f"Bot context document: {path.name}\n"
                f"{heading}\n\n"
                f"{text[:2000]}"
            )
            metadata = {
                "type": ftype,
                "name": path.stem,
                "description": heading[:200] or path.stem,
                "path": str(path),
            }
        else:  # script
            parsed = parse_script_file(path)
            embed_text = (
                f"Script: {parsed['name']}\n"
                f"{parsed['description']}\n"
                f"{parsed['usage']}\n\n"
                f"{parsed['full_text'][:1500]}"
            )
            metadata = {
                "type": ftype,
                "name": parsed["name"],
                "description": parsed["description"][:400],
                "usage": parsed["usage"][:200],
                "path": str(path),
            }

        emb = get_embedding(embed_text)
        if emb is None:
            log(f"  Failed to embed {path.name}")
            errors += 1
            continue

        # Remove old hash markers
        old_hashes = [i for i in existing_ids if i.startswith(f"{doc_id}::hash::")]
        if old_hashes:
            delete_ids(col_id, old_hashes)

        upsert_doc(col_id, doc_id, embed_text, metadata, emb)

        # Store hash marker
        hash_emb = get_embedding(f"[marker] {path.name}")
        if hash_emb:
            upsert_doc(col_id, hash_id, f"[marker] {path.name}",
                       {"type": "hash", "source": str(path)}, hash_emb)

        log(f"  ✓ {path.name}")
        indexed += 1
        time.sleep(0.05)

    log(f"\nDone: {indexed} indexed, {skipped} unchanged, {errors} errors")
    final_ids = get_existing_ids(col_id)
    count = len([i for i in final_ids if "::hash::" not in i])
    log(f"Total in ChromaDB bot_files collection: {count} docs")


if __name__ == "__main__":
    main()
