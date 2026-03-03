#!/usr/bin/env python3
"""
Obsidian FTS5 Query — searches the pre-built SQLite index from inside the container.
Fast, zero-indexing overhead. Run obsidian_index.py on host to update the index.

Usage:
  python3 obsidian_query.py "POST /users"
  python3 obsidian_query.py "API key" --limit 5
  python3 obsidian_query.py "loan balance" --limit 3 --snippet 30
"""

import sys
import sqlite3
import argparse
from pathlib import Path

DB_PATH = Path("/data/obsidian/vault/Bot/obsidian.db")


def search(query, limit=3, snippet_lines=40):
    if not DB_PATH.exists():
        print(f"Index not found at {DB_PATH}")
        print("Run obsidian_index.py on the host to build the index first.")
        sys.exit(1)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    try:
        rows = conn.execute("""
            SELECT file_path, section_title, content, rank
            FROM chunks
            WHERE chunks MATCH ?
            ORDER BY rank
            LIMIT ?
        """, (query, limit)).fetchall()
    except sqlite3.OperationalError:
        # Fallback for queries with special FTS5 chars
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

    print(f'Results for: "{query}"\n')
    for row in rows:
        print(f"FILE: {row['file_path']}")
        print(f"SECTION: {row['section_title']}")
        print("---")
        lines = row['content'].splitlines()[:snippet_lines]
        print("\n".join(lines))
        total = len(row['content'].splitlines())
        if total > snippet_lines:
            print(f"... ({total} lines total, showing {snippet_lines})")
        print()

    print(f"[{len(rows)} result(s)]")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("query", help="Search query")
    parser.add_argument("--limit", "-l", type=int, default=3)
    parser.add_argument("--snippet", "-s", type=int, default=40,
                        help="Lines per result snippet (default 40)")
    args = parser.parse_args()
    search(args.query, args.limit, args.snippet)
