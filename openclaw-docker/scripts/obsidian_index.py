#!/usr/bin/env python3
"""
Obsidian FTS5 Indexer v2.0 (Stable)
Supports MD, PDF, DOCX, XLSX via Unstructured.io API.
"""

import sys
import sqlite3
import re
import argparse
import time
import requests
from pathlib import Path

# --- Configuration ---
VAULT_HOST = Path("/Users/abror_mac_mini/Library/Mobile Documents/iCloud~md~obsidian/Documents/My Docs")
DB_DEFAULT = VAULT_HOST / "To claw" / "Bot" / "obsidian.db"
MAX_CHUNK_LINES = 200
UNSTRUCTURED_URL = "http://unstructured-api:8000/general/v0/general"

# Resolved at runtime from args
DB_PATH = DB_DEFAULT

def get_db():
    try:
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(DB_PATH)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("CREATE TABLE IF NOT EXISTS files (path TEXT PRIMARY KEY, mtime REAL)")
        conn.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS chunks USING fts5(
                file_path, section_title, content,
                tokenize='unicode61 remove_diacritics 1'
            )
        """)
        conn.commit()
        return conn
    except Exception as e:
        print(f"CRITICAL: Database error: {e}")
        sys.exit(1)

def chunk_markdown(text, file_path):
    lines = text.splitlines()
    chunks = []
    current_title = "(intro)"
    current_lines = []

    for line in lines:
        header = re.match(r'^(#{1,4})\s+(.+)', line)
        if header:
            if current_lines:
                chunks.append((file_path, current_title, "\n".join(current_lines)))
            current_title = header.group(2).strip()
            current_lines = [line]
        else:
            current_lines.append(line)
            if len(current_lines) >= MAX_CHUNK_LINES:
                chunks.append((file_path, current_title + " [cont]", "\n".join(current_lines)))
                current_lines = []

    if current_lines:
        chunks.append((file_path, current_title, "\n".join(current_lines)))
    return chunks

def wait_for_unstructured():
    print(">>> Waiting for Unstructured API...")
    for i in range(15):
        try:
            # Try to get root or health
            res = requests.get("http://unstructured-api:8000/", timeout=3)
            if res.status_code in [200, 404]:
                print(f">>> API is UP (Status: {res.status_code})")
                return True
        except Exception:
            pass
        print(f"    [{i+1}/15] Still waiting...")
        time.sleep(3)
    return False

def get_text_from_unstructured(file_path):
    try:
        print(f"    ...extracting text via API: {file_path.name}")
        with open(file_path, "rb") as f:
            files = {"files": (file_path.name, f)}
            # No complex data params to avoid 422 errors
            response = requests.post(UNSTRUCTURED_URL, files=files, timeout=300)
            if response.status_code == 200:
                elements = response.json()
                text = "\n\n".join([el.get("text", "") for el in elements if "text" in el])
                print(f"    ✅ Success: {len(text)} chars extracted.")
                return text
            else:
                print(f"    ❌ API Error {response.status_code}: {response.text[:100]}")
                return ""
    except Exception as e:
        print(f"    ❌ Extraction Exception: {e}")
        return ""

def index(vault_path=None, force=False):
    vault = Path(vault_path) if vault_path else VAULT_HOST
    print(f"Starting indexer. Vault: {vault}")
    
    conn = get_db()
    cur = conn.cursor()

    if force:
        cur.execute("DELETE FROM chunks")
        cur.execute("DELETE FROM files")
        conn.commit()
        print("Force mode: Index cleared.")

    # Find all supported files
    extensions = ["*.md", "*.pdf", "*.docx", "*.xlsx"]
    files_to_index = []
    for ext in extensions:
        files_to_index.extend(list(vault.rglob(ext)))

    print(f"Found {len(files_to_index)} files total.")

    # Check for Unstructured API if needed
    if any(f.suffix != ".md" for f in files_to_index):
        if not wait_for_unstructured():
            print("ERROR: Unstructured API is not responding. Skipping PDF/Office files.")
            # Filter out complex files to avoid errors
            files_to_index = [f for f in files_to_index if f.suffix == ".md"]

    added = updated = skipped = 0
    for doc_file in files_to_index:
        try:
            rel = str(doc_file.relative_to(vault))
        except ValueError:
            rel = str(doc_file)
            
        mtime = doc_file.stat().st_mtime
        row = cur.execute("SELECT mtime FROM files WHERE path=?", (rel,)).fetchone()
        
        if not force and row and abs(row[0] - mtime) < 1:
            skipped += 1
            continue

        print(f"[{added+updated+skipped+1}/{len(files_to_index)}] Indexing: {rel}")
        
        try:
            if doc_file.suffix == ".md":
                text = doc_file.read_text(encoding="utf-8", errors="ignore")
            else:
                text = get_text_from_unstructured(doc_file)
        except Exception as e:
            print(f"    ⚠️ Skipping {rel}: {e}")
            continue

        if not text:
            continue

        cur.execute("DELETE FROM chunks WHERE file_path=?", (rel,))
        chunks = chunk_markdown(text, rel)
        cur.executemany("INSERT INTO chunks(file_path, section_title, content) VALUES(?,?,?)", chunks)

        if row:
            cur.execute("UPDATE files SET mtime=? WHERE path=?", (mtime, rel))
            updated += 1
        else:
            cur.execute("INSERT INTO files(path, mtime) VALUES(?,?)", (rel, mtime))
            added += 1
        
        conn.commit()

    conn.close()
    print(f"\nFINISH: +{added} new, ~{updated} updated, {skipped} skipped.")

def search(query, limit=3):
    if not DB_PATH.exists():
        print("Index not found. Build it first.")
        sys.exit(1)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute("""
            SELECT file_path, section_title, content, rank 
            FROM chunks WHERE chunks MATCH ? ORDER BY rank LIMIT ?
        """, (query, limit)).fetchall()
    except sqlite3.OperationalError:
        rows = conn.execute("""
            SELECT file_path, section_title, content, 0 as rank 
            FROM chunks WHERE content LIKE ? LIMIT ?
        """, (f"%{query}%", limit)).fetchall()
    conn.close()

    if not rows:
        print(f"No results for: {query}")
        return

    print(f'🔍 Results for: "{query}"\n')
    for row in rows:
        print(f"📄 {row['file_path']} [§ {row['section_title']}]")
        print("────────────────────────────────")
        print("\n".join(row['content'].splitlines()[:40]))
        print()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--search", "-s")
    parser.add_argument("--limit", "-l", type=int, default=3)
    parser.add_argument("--vault")
    parser.add_argument("--db")
    parser.add_argument("--force", "-f", action="store_true")
    args = parser.parse_args()

    if args.db: DB_PATH = Path(args.db)
    if args.search:
        search(args.search, args.limit)
    else:
        index(args.vault, force=args.force)
