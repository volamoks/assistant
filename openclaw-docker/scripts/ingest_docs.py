#!/usr/bin/env python3
"""
ingest_docs.py — Ingest binary documents (PDF, DOCX, RTF, XLSX, PPTX) from
Obsidian vault into ChromaDB using markitdown for conversion and Ollama for embeddings.

Runs alongside ingest.js (which handles .md files) to provide unified RAG search.

Usage:
    python3 /data/bot/openclaw-docker/scripts/ingest_docs.py
    python3 /data/bot/openclaw-docker/scripts/ingest_docs.py --dry-run
    python3 /data/bot/openclaw-docker/scripts/ingest_docs.py --force  # re-index all
"""

import os
import sys
import json
import time
import hashlib
import argparse
import urllib.request
import urllib.error
from pathlib import Path

# ─── FIX: Broken numpy in /opt/pip-packages (macOS .so on Linux) ────────────
# Install numpy==1.26.4 to /tmp/pip_numpy if not present
_NUMPY_FIX_PATH = "/tmp/pip_numpy"
if os.path.exists(_NUMPY_FIX_PATH) and _NUMPY_FIX_PATH not in sys.path:
    sys.path.insert(0, _NUMPY_FIX_PATH)

# ─── Config ──────────────────────────────────────────────────────────────────
SYS_VAULT_ENV  = os.environ.get("SYSTEM_VAULT_PATH", "/data/obsidian/vault")
USER_VAULT_ENV = os.environ.get("USER_VAULT_PATH", "/data/abror_vault")
OLLAMA_HOST    = os.environ.get("OLLAMA_HOST", "http://host.docker.internal:11434")
CHROMA_HOST    = os.environ.get("CHROMA_HOST", "http://chromadb:8000")
COLLECTION     = "obsidian_vault"  # same collection as ingest.js
EMBED_MODEL    = "nomic-embed-text"
CHUNK_SIZE     = 800   # chars per chunk
CHUNK_OVERLAP  = 100

SUPPORTED_EXT  = {".pdf", ".docx", ".rtf", ".xlsx", ".pptx", ".doc", ".odt"}

# ─── Helpers ─────────────────────────────────────────────────────────────────

def log(msg: str):
    print(f"[ingest-docs] {msg}", flush=True)

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

# ─── markitdown conversion ───────────────────────────────────────────────────

def ensure_markitdown():
    """Check markitdown is available."""
    try:
        import markitdown  # noqa
        return True
    except ImportError:
        log("❌ markitdown not found.")
        log("   Install once with:")
        log("   docker exec -u root openclaw-latest pip3 install 'markitdown[all]' --break-system-packages")
        return False

def convert_to_text(file_path: Path) -> str | None:
    """Convert doc/docx/pdf/other to text using markitdown."""
    ext = file_path.suffix.lower()
    
    # .doc (old Word format) → try catdoc first, fall back to markitdown
    if ext == ".doc":
        # Try catdoc if available
        try:
            import subprocess
            result = subprocess.run(
                ["catdoc", str(file_path)],
                capture_output=True, text=True, timeout=60
            )
            if result.returncode == 0 and len(result.stdout.strip()) > 50:
                return result.stdout.strip()
        except FileNotFoundError:
            pass  # catdoc not installed
        except Exception as e:
            log(f"  ⚠️  catdoc failed for {file_path.name}: {e}")
        
        # Fall back to markitdown (works for some .doc files via olefile)
        try:
            from markitdown import MarkItDown
            md = MarkItDown(enable_plugins=False)
            result = md.convert(str(file_path))
            text = result.text_content
            if text and len(text.strip()) > 50:
                return text.strip()
        except Exception as e:
            log(f"  ❌ markitdown failed for {file_path.name}: {e}")
        return None
    
    # .docx, .pdf, .xlsx, .pptx, .rtf, .odt → markitdown
    try:
        from markitdown import MarkItDown
        md = MarkItDown(enable_plugins=False)
        result = md.convert(str(file_path))
        text = result.text_content
        if text and len(text.strip()) > 50:
            return text.strip()
        log(f"  ⚠️  Empty result for {file_path.name}")
        return None
    except Exception as e:
        log(f"  ❌ Failed to convert {file_path.name}: {e}")
        return None

# ─── Chunking ────────────────────────────────────────────────────────────────

def chunk_text(text: str, source: str) -> list[dict]:
    """Split text into overlapping chunks."""
    chunks = []
    start = 0
    idx = 0
    while start < len(text):
        end = start + CHUNK_SIZE
        chunk = text[start:end]
        if chunk.strip():
            chunks.append({
                "id": f"{source}::chunk{idx}",
                "text": chunk,
                "source": source,
                "chunk_index": idx
            })
            idx += 1
        start = end - CHUNK_OVERLAP
    return chunks

# ─── Ollama Embeddings ────────────────────────────────────────────────────────

def get_embedding(text: str) -> list[float] | None:
    try:
        resp = http_post(f"{OLLAMA_HOST}/api/embeddings", {
            "model": EMBED_MODEL,
            "prompt": text
        })
        return resp.get("embedding")
    except Exception as e:
        log(f"  ❌ Embedding error: {e}")
        return None

# ─── ChromaDB ────────────────────────────────────────────────────────────────

def get_collection_id() -> str | None:
    try:
        data = http_get(f"{CHROMA_HOST}/api/v1/collections/{COLLECTION}")
        return data.get("id")
    except Exception:
        return None

def get_existing_ids(col_id: str) -> set[str]:
    """Get all document IDs already in the collection."""
    try:
        data = http_post(f"{CHROMA_HOST}/api/v1/collections/{col_id}/get",
                         {"include": []})
        ids = data.get("ids", [])
        return set(ids)
    except Exception as e:
        log(f"  ⚠️  Could not get existing IDs: {e} — treating as empty")
        return set()

def delete_chunks_for_file(col_id: str, source: str, existing_ids: set[str]):
    """Remove all existing chunks for a given source file."""
    to_delete = [id_ for id_ in existing_ids if id_.startswith(f"{source}::")]
    if not to_delete:
        return
    try:
        http_post(f"{CHROMA_HOST}/api/v1/collections/{col_id}/delete",
                  {"ids": to_delete})
        log(f"  🗑  Removed {len(to_delete)} old chunks for {source}")
    except Exception as e:
        log(f"  ⚠️  Could not delete old chunks: {e}")

def upsert_chunks(col_id: str, chunks: list[dict]):
    """Embed and upsert chunks into ChromaDB in batches."""
    batch_size = 5  # small batches to avoid OOM
    total = len(chunks)
    for i in range(0, total, batch_size):
        batch = chunks[i:i + batch_size]
        ids, docs, metas, embeds = [], [], [], []
        for c in batch:
            emb = get_embedding(c["text"])
            if emb is None:
                continue
            ids.append(c["id"])
            docs.append(c["text"])
            metas.append({"source": c["source"], "chunk": c["chunk_index"]})
            embeds.append(emb)
        if ids:
            http_post(f"{CHROMA_HOST}/api/v1/collections/{col_id}/upsert", {
                "ids": ids,
                "documents": docs,
                "metadatas": metas,
                "embeddings": embeds
            })
            pct = min(100, int((i + batch_size) / total * 100))
            print(f"  [{pct}%] {i+len(ids)}/{total} chunks", flush=True)

# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="List files only")
    parser.add_argument("--force", action="store_true", help="Re-index all files")
    args = parser.parse_args()

    log(f"Vaults: {SYS_VAULT_ENV}, {USER_VAULT_ENV}")
    log(f"ChromaDB: {CHROMA_HOST} | Ollama: {OLLAMA_HOST}")

    vault_paths = []
    
    # Handle both /data/obsidian/vault and /data/obsidian (root with sibling dirs)
    sys_vault = Path(SYS_VAULT_ENV)
    if sys_vault.name == "vault" and sys_vault.parent.exists():
        # /data/obsidian/vault -> also scan sibling dirs like Inbox, Assets, etc.
        vault_paths.append(sys_vault)  # Claw subfolder
        for sibling in sys_vault.parent.iterdir():
            if sibling.is_dir() and not sibling.name.startswith(".") and sibling.name != "vault":
                vault_paths.append(sibling)
    else:
        vault_paths.append(sys_vault)
    
    if Path(USER_VAULT_ENV).exists() and USER_VAULT_ENV != SYS_VAULT_ENV:
        vault_paths.append(Path(USER_VAULT_ENV))

    docs = []
    for vault in vault_paths:
        if not vault.exists():
            log(f"⚠️ Vault path not found: {vault}")
            continue
        docs.extend([p for p in vault.rglob("*")
                if p.suffix.lower() in SUPPORTED_EXT
                and not any(part.startswith(".") for part in p.parts)])

    log(f"Found {len(docs)} documents: {', '.join(ext for ext in SUPPORTED_EXT)}")

    if not docs:
        log("No documents found. Done.")
        return

    if args.dry_run:
        for d in docs:
            print(f"  {d}")
        return

    # Setup
    if not ensure_markitdown():
        log("❌ Cannot proceed without markitdown.")
        sys.exit(1)

    col_id = get_collection_id()
    if not col_id:
        log("❌ ChromaDB collection 'obsidian_vault' not found. Run ingest.js first.")
        sys.exit(1)

    existing_ids = get_existing_ids(col_id)
    log(f"ChromaDB has {len(existing_ids)} total chunks (including .md)")

    # Process each doc
    processed = 0
    skipped = 0

    for doc_path in docs:
        rel = str(doc_path)
        fhash = file_hash(doc_path)
        hash_id = f"{rel}::hash::{fhash}"

        # Skip if already indexed (unless --force)
        if not args.force and hash_id in existing_ids:
            skipped += 1
            continue

        log(f"📄 Processing: {rel}")
        text = convert_to_text(doc_path)
        if not text:
            continue

        try:
            chunks = chunk_text(text, rel)
            log(f"  → {len(chunks)} chunks from {len(text)} chars")

            # Remove old chunks for this file
            delete_chunks_for_file(col_id, rel, existing_ids)

            # Add hash marker chunk (to track file version)
            chunks.append({"id": hash_id, "text": f"[file marker] {rel}", "source": rel, "chunk_index": -1})

            upsert_chunks(col_id, chunks)
            log(f"  ✅ Indexed {rel}")
            processed += 1
        except Exception as e:
            import traceback
            log(f"  ❌ Failed to index {rel}: {e}")
            traceback.print_exc()
            continue
        time.sleep(0.2)  # Rate limit Ollama

    log(f"\n✅ Done: {processed} new/updated, {skipped} unchanged")

if __name__ == "__main__":
    main()
