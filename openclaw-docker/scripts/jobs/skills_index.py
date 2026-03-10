#!/usr/bin/env python3
"""
skills_index.py — Index all SKILL.md files into ChromaDB 'skills' collection.

Uses Ollama nomic-embed-text for embeddings (local, free).
Incremental: skips unchanged skills (checks mtime+size hash).

Usage (inside container):
    python3 /data/bot/openclaw-docker/scripts/jobs/skills_index.py
    python3 /data/bot/openclaw-docker/scripts/jobs/skills_index.py --force
    python3 /data/bot/openclaw-docker/scripts/jobs/skills_index.py --dry-run
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
SKILLS_DIR     = Path(os.environ.get("SKILLS_DIR", "/home/node/.openclaw/skills"))
OLLAMA_HOST    = os.environ.get("OLLAMA_HOST", "http://host.docker.internal:11434")
CHROMA_HOST    = os.environ.get("CHROMA_HOST", "http://chromadb:8000")
COLLECTION     = "skills"
EMBED_MODEL    = "nomic-embed-text"

# ─── Helpers ──────────────────────────────────────────────────────────────────

def log(msg: str):
    print(f"[skills-index] {msg}", flush=True)

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

# ─── SKILL.md parsing ─────────────────────────────────────────────────────────

def parse_skill_md(path: Path) -> dict:
    """Parse SKILL.md frontmatter + first description paragraph."""
    text = path.read_text(encoding="utf-8", errors="replace")

    name = path.parent.name  # fallback: directory name
    description = ""
    triggers = []

    # Extract YAML frontmatter
    fm_match = re.match(r"^---\s*\n(.*?)\n---", text, re.DOTALL)
    if fm_match:
        fm = fm_match.group(1)
        # name
        m = re.search(r"^name:\s*['\"]?(.+?)['\"]?\s*$", fm, re.MULTILINE)
        if m:
            name = m.group(1).strip()
        # description
        m = re.search(r"^description:\s*['\"](.+?)['\"]", fm, re.DOTALL | re.MULTILINE)
        if m:
            description = m.group(1).strip().replace("\n", " ")
        # triggers (YAML list)
        t_match = re.search(r"^triggers:\s*\n((?:\s+-\s*.+\n?)*)", fm, re.MULTILINE)
        if t_match:
            triggers = re.findall(r"-\s*(.+)", t_match.group(1))
            triggers = [t.strip() for t in triggers]

    # If no description from frontmatter, grab first non-empty paragraph after ---
    if not description:
        body = re.sub(r"^---.*?---\s*\n", "", text, flags=re.DOTALL).strip()
        # First heading line or first paragraph
        lines = [l.strip() for l in body.splitlines() if l.strip()]
        for line in lines[:5]:
            if not line.startswith("#"):
                description = line[:300]
                break
        if not description and lines:
            description = lines[0].lstrip("#").strip()[:300]

    return {
        "name": name,
        "description": description,
        "triggers": triggers,
        "full_text": text[:4000],  # truncate for embedding
    }

# ─── Embedding ────────────────────────────────────────────────────────────────

def get_embedding(text: str) -> list | None:
    try:
        resp = http_post(f"{OLLAMA_HOST}/api/embeddings", {
            "model": EMBED_MODEL,
            "prompt": text
        })
        return resp.get("embedding")
    except Exception as e:
        log(f"  Embedding error: {e}")
        return None

# ─── ChromaDB ─────────────────────────────────────────────────────────────────

def get_or_create_collection() -> str:
    """Return collection UUID, create if missing."""
    try:
        data = http_get(f"{CHROMA_HOST}/api/v1/collections/{COLLECTION}")
        col_id = data.get("id")
        if col_id:
            return col_id
    except Exception:
        pass

    # Create collection
    try:
        data = http_post(f"{CHROMA_HOST}/api/v1/collections", {
            "name": COLLECTION,
            "metadata": {"type": "skills"}
        })
        return data["id"]
    except Exception as e:
        log(f"Failed to create collection: {e}")
        sys.exit(1)

def get_existing_ids(col_id: str) -> set:
    try:
        data = http_post(f"{CHROMA_HOST}/api/v1/collections/{col_id}/get",
                         {"include": []})
        return set(data.get("ids", []))
    except Exception as e:
        log(f"Could not get existing IDs: {e}")
        return set()

def upsert_skill(col_id: str, skill_id: str, document: str, metadata: dict, embedding: list):
    http_post(f"{CHROMA_HOST}/api/v1/collections/{col_id}/upsert", {
        "ids": [skill_id],
        "documents": [document],
        "metadatas": [metadata],
        "embeddings": [embedding],
    })

def delete_ids(col_id: str, ids: list):
    if ids:
        http_post(f"{CHROMA_HOST}/api/v1/collections/{col_id}/delete", {"ids": ids})

# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="List files only, no indexing")
    parser.add_argument("--force", action="store_true", help="Re-index all skills")
    args = parser.parse_args()

    if not SKILLS_DIR.exists():
        log(f"Skills dir not found: {SKILLS_DIR}")
        sys.exit(1)

    # Find all SKILL.md files
    skill_files = sorted(SKILLS_DIR.glob("*/SKILL.md"))
    log(f"Found {len(skill_files)} SKILL.md files in {SKILLS_DIR}")

    if args.dry_run:
        for f in skill_files:
            print(f"  {f.parent.name}/SKILL.md")
        return

    col_id = get_or_create_collection()
    log(f"Collection UUID: {col_id}")

    existing_ids = get_existing_ids(col_id)
    log(f"Already indexed: {len([i for i in existing_ids if not i.endswith('::hash')])} skills")

    indexed = 0
    skipped = 0
    errors = 0

    for skill_file in skill_files:
        skill_dir = skill_file.parent.name
        skill_id = skill_dir
        hash_id = f"{skill_dir}::hash::{file_hash(skill_file)}"

        # Skip if unchanged (hash marker exists)
        if not args.force and hash_id in existing_ids:
            skipped += 1
            continue

        log(f"Indexing: {skill_dir}")
        skill = parse_skill_md(skill_file)

        # Build document text for embedding: name + description + triggers + content
        triggers_str = " | ".join(skill["triggers"]) if skill["triggers"] else ""
        embed_text = f"Skill: {skill['name']}\n{skill['description']}\nTriggers: {triggers_str}\n\n{skill['full_text'][:2000]}"

        emb = get_embedding(embed_text)
        if emb is None:
            log(f"  Failed to embed {skill_dir}")
            errors += 1
            continue

        metadata = {
            "name": skill["name"],
            "path": f"skills/{skill_dir}/SKILL.md",
            "description": skill["description"][:500],
            "triggers": json.dumps(skill["triggers"]),
        }

        # Remove old hash marker
        old_hashes = [i for i in existing_ids if i.startswith(f"{skill_dir}::hash::")]
        if old_hashes:
            delete_ids(col_id, old_hashes)

        # Upsert skill document + hash marker
        upsert_skill(col_id, skill_id, embed_text, metadata, emb)

        # Store hash marker (no embedding needed, just a sentinel)
        hash_emb = get_embedding(f"[marker] {skill_dir}")
        if hash_emb:
            upsert_skill(col_id, hash_id, f"[file marker] {skill_dir}", {"source": skill_dir, "type": "hash"}, hash_emb)

        log(f"  ✓ {skill['name']} ({len(skill['triggers'])} triggers)")
        indexed += 1
        time.sleep(0.1)  # gentle rate limit

    log(f"\nDone: {indexed} indexed, {skipped} unchanged, {errors} errors")

    # Print final count
    final_ids = get_existing_ids(col_id)
    skill_count = len([i for i in final_ids if "::hash::" not in i])
    log(f"Total in ChromaDB skills collection: {skill_count} skills")

if __name__ == "__main__":
    main()
