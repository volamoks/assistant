#!/usr/bin/env python3
"""
db_migrate.py — one-time schema migrations for finance.db

Run once:
    python3 pfm/db_migrate.py
"""
import sqlite3
from pathlib import Path

DB = Path(__file__).parent / "finance.db"

MIGRATIONS = [
    # Add pending_until for pending_match credits (ISO timestamp)
    "ALTER TABLE transactions ADD COLUMN pending_until TEXT",
    # Add clean merchant name after enrichment
    "ALTER TABLE transactions ADD COLUMN merchant_clean TEXT",
    # merchant_patterns: user/LLM confirmed categories per merchant keyword
    """CREATE TABLE IF NOT EXISTS merchant_patterns (
        merchant_keyword TEXT PRIMARY KEY,
        category         TEXT NOT NULL,
        confirmed_by     TEXT NOT NULL CHECK (confirmed_by IN ('user', 'llm')),
        confidence       REAL DEFAULT 1.0,
        use_count        INTEGER DEFAULT 1,
        created_at       TEXT DEFAULT (datetime('now'))
    )""",
    # pending_questions: tracks which txns await user category answer
    """CREATE TABLE IF NOT EXISTS pending_questions (
        tx_id      INTEGER PRIMARY KEY,
        sent_at    TEXT DEFAULT (datetime('now')),
        message_id INTEGER
    )""",
]

def run():
    conn = sqlite3.connect(DB)
    cur  = conn.cursor()
    for sql in MIGRATIONS:
        try:
            cur.execute(sql)
            print(f"✅ {sql[:60].strip()}...")
        except sqlite3.OperationalError as e:
            if "duplicate column" in str(e).lower() or "already exists" in str(e).lower():
                print(f"⏭️  Already applied: {sql[:60].strip()}...")
            else:
                print(f"❌ Error: {e}\n   SQL: {sql[:80]}")
    conn.commit()
    conn.close()
    print("\nMigration complete.")

if __name__ == "__main__":
    run()
