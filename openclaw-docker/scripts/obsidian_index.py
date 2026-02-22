#!/usr/bin/env python3
"""
Obsidian FTS5 Indexer — chunks markdown by headers into SQLite full-text search index.
Runs on host (macOS). Index stored in Obsidian vault, accessible from container.

Usage:
  python3 obsidian_index.py           # index/update
  python3 obsidian_index.py --search "POST /users"  # search
  python3 obsidian_index.py --search "API key" --limit 5
"""

import sys
import sqlite3
import re
import argparse
from pathlib import Path

VAULT_HOST = Path("/Users/abror_mac_mini/Library/Mobile Documents/iCloud~md~obsidian/Documents/My Docs")
DB_PATH = VAULT_HOST / "To claw" / "Bot" / "obsidian.db"
MAX_CHUNK_LINES = 200

def get_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS files (
            path TEXT PRIMARY KEY,
            mtime REAL
        )
    """)
    conn.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS chunks USING fts5(
            file_path,
            section_title,
            content,
            tokenize='unicode61 remove_diacritics 1'
        )
    """)
    conn.commit()
    return conn

def chunk_markdown(text, file_path):
    """Split markdown into sections by headers."""
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
            # Split oversized chunks mid-section
            if len(current_lines) >= MAX_CHUNK_LINES:
                chunks.append((file_path, current_title + " [cont]", "\n".join(current_lines)))
                current_lines = []

    if current_lines:
        chunks.append((file_path, current_title, "\n".join(current_lines)))

    return chunks

def index(vault_path=None):
    vault = Path(vault_path) if vault_path else VAULT_HOST
    conn = get_db()
    cur = conn.cursor()

    added = updated = skipped = 0

    for md_file in vault.rglob("*.md"):
        rel = str(md_file.relative_to(vault))
        mtime = md_file.stat().st_mtime

        row = cur.execute("SELECT mtime FROM files WHERE path=?", (rel,)).fetchone()
        if row and abs(row[0] - mtime) < 1:
            skipped += 1
            continue

        try:
            text = md_file.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        # Remove old chunks for this file
        cur.execute("DELETE FROM chunks WHERE file_path=?", (rel,))

        # Insert new chunks
        chunks = chunk_markdown(text, rel)
        cur.executemany(
            "INSERT INTO chunks(file_path, section_title, content) VALUES(?,?,?)",
            chunks
        )

        if row:
            cur.execute("UPDATE files SET mtime=? WHERE path=?", (mtime, rel))
            updated += 1
        else:
            cur.execute("INSERT INTO files(path, mtime) VALUES(?,?)", (rel, mtime))
            added += 1

    conn.commit()
    conn.close()
    print(f"Index updated: +{added} new, ~{updated} updated, {skipped} unchanged")

def search(query, limit=3):
    if not DB_PATH.exists():
        print("Index not found. Run without --search first to build index.")
        sys.exit(1)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    # Try FTS5 match first
    try:
        rows = conn.execute("""
            SELECT file_path, section_title, content,
                   rank
            FROM chunks
            WHERE chunks MATCH ?
            ORDER BY rank
            LIMIT ?
        """, (query, limit)).fetchall()
    except sqlite3.OperationalError:
        # Fallback: LIKE search if query has special chars
        rows = conn.execute("""
            SELECT file_path, section_title, content, 0 as rank
            FROM chunks
            WHERE content LIKE ?
            LIMIT ?
        """, (f"%{query}%", limit)).fetchall()

    conn.close()

    if not rows:
        print(f"No results for: {query}")
        return

    print(f'🔍 Results for: "{query}"\n')
    for i, row in enumerate(rows, 1):
        print(f"📄 {row['file_path']}")
        print(f"   § {row['section_title']}")
        print("────────────────────────────────")
        # Show snippet: first 60 lines of chunk
        lines = row['content'].splitlines()[:60]
        print("\n".join(lines))
        if len(row['content'].splitlines()) > 60:
            print(f"   ... ({len(row['content'].splitlines())} lines total, showing 60)")
        print()

    print(f"[{len(rows)} result(s), limit={limit}]")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--search", "-s", help="Search query")
    parser.add_argument("--limit", "-l", type=int, default=3)
    parser.add_argument("--vault", help="Vault path override")
    args = parser.parse_args()

    if args.search:
        search(args.search, args.limit)
    else:
        index(args.vault)
