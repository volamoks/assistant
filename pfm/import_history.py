"""
One-time import: fetch all historical messages from @HUMOcardbot → finance.db → Actual Budget

Usage:
    python3 import_history.py               # import from @HUMOcardbot
    python3 import_history.py --dry-run     # preview only
    python3 import_history.py --limit 500   # limit messages (default: all)
    python3 import_history.py --no-actual   # only write to finance.db, skip Actual
"""

import argparse
import asyncio
import os
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

from telethon import TelegramClient

from config import find_db, validate_actual_config
from actual_client import get_actual_client, get_or_create_account, add_transaction

# Add handler path
sys.path.insert(0, str(Path(__file__).parent.parent / "openclaw-docker/workspace/telegram"))
from handlers.humo_pfm import parse_message
import re as _re

def strip_markdown(text: str) -> str:
    """Remove Telegram markdown: **bold**, __italic__, `code`."""
    text = _re.sub(r'\*\*(.+?)\*\*', r'\1', text, flags=_re.DOTALL)
    text = _re.sub(r'__(.+?)__',     r'\1', text, flags=_re.DOTALL)
    text = _re.sub(r'`(.+?)`',       r'\1', text, flags=_re.DOTALL)
    return text

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / "openclaw-docker/workspace/telegram/.env")

API_ID   = int(os.getenv("TELEGRAM_API_ID", "0"))
API_HASH = os.getenv("TELEGRAM_API_HASH", "")
SESSION  = str(Path(__file__).parent.parent / "openclaw-docker/workspace/telegram/session")

SOURCES = ["@HUMOcardbot", "@abror_komalov"]

DB_PATH = find_db()


def init_db(con: sqlite3.Connection):
    con.execute("""
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL, time TEXT, amount REAL NOT NULL,
            currency TEXT DEFAULT 'UZS', category TEXT, merchant TEXT,
            payment_method TEXT, card_last4 TEXT,
            transaction_type TEXT DEFAULT 'debit', source TEXT DEFAULT 'HUMO',
            raw_text TEXT, tags TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            is_enriched INTEGER DEFAULT 0, enriched_at TEXT,
            enriched_category TEXT, merchant_type TEXT, enriched_tags TEXT,
            is_recurring INTEGER DEFAULT 0, llm_confidence REAL, llm_notes TEXT,
            actual_synced INTEGER DEFAULT 0, actual_tx_id TEXT
        )
    """)
    # Ensure all columns exist (for existing DBs)
    for col, typedef in [
        ("card_last4", "TEXT"),
        ("actual_synced", "INTEGER DEFAULT 0"),
        ("actual_tx_id", "TEXT"),
    ]:
        try:
            con.execute(f"ALTER TABLE expenses ADD COLUMN {col} {typedef}")
        except sqlite3.OperationalError:
            pass
    con.execute("CREATE INDEX IF NOT EXISTS idx_date ON expenses(date)")
    con.execute("CREATE INDEX IF NOT EXISTS idx_card ON expenses(card_last4)")
    con.commit()


def is_duplicate(con: sqlite3.Connection, date: str, amount: float, card_last4: str) -> bool:
    row = con.execute(
        "SELECT id FROM expenses WHERE date=? AND amount=? AND card_last4=?",
        (date, amount, card_last4)
    ).fetchone()
    return row is not None


def save_to_db(con: sqlite3.Connection, parsed: dict) -> int:
    cur = con.execute("""
        INSERT INTO expenses
          (date, time, amount, currency, category, merchant,
           payment_method, card_last4, transaction_type, source, raw_text)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'HUMO', ?)
    """, (
        parsed["date"], parsed["time"], parsed["amount"], parsed["currency"],
        parsed["category"], parsed["merchant"], parsed["payment_method"],
        parsed["card_last4"], parsed["transaction_type"], parsed["raw_text"],
    ))
    con.commit()
    return cur.lastrowid


def push_to_actual(rows: list):
    from actual import get_accounts

    with get_actual_client() as actual:
        s = actual.session
        accounts = get_accounts(s)

        for row_id, parsed in rows:
            card_last4 = parsed["card_last4"]
            acc_name = f"HUMO *{card_last4}" if card_last4 else "HUMO"
            acc = get_or_create_account(s, accounts, acc_name)

            try:
                tx_date = datetime.strptime(parsed["date"], "%Y-%m-%d").date()
            except (ValueError, TypeError):
                tx_date = datetime.now().date()

            actual_amount = -parsed["amount"] if parsed["transaction_type"] == "debit" else parsed["amount"]
            
            # Use 'General' as a fallback if the category isn't properly mapped during parsing yet
            from config import CATEGORY_MAP
            actual_category = CATEGORY_MAP.get((parsed.get("category") or "OTHER").upper(), "General")

            tx = add_transaction(
                session=s,
                account=acc,
                date=tx_date,
                payee=parsed["merchant"],
                notes=parsed["payment_method"] or "",
                category=actual_category,
                amount=actual_amount,
                imported_id=f"humo-{row_id}-{parsed['date']}-{parsed['amount']}",
            )
            # Mark synced in DB
            # (done in batch after commit below)

        actual.commit()
        print(f"  Pushed {len(rows)} transactions to Actual Budget")


async def fetch_history(dry_run: bool, limit: int, no_actual: bool):
    con = sqlite3.connect(DB_PATH)
    init_db(con)

    async with TelegramClient(SESSION, API_ID, API_HASH) as client:
        total_parsed = 0
        total_skipped = 0
        total_duplicate = 0
        new_rows = []  # (row_id, parsed) for Actual push

        for source in SOURCES:
            print(f"\n📥 Fetching history from {source}...")
            try:
                entity = await client.get_entity(source)
            except Exception as e:
                print(f"  ⚠️  Cannot access {source}: {e}")
                continue

            msg_count = 0
            async for msg in client.iter_messages(entity, limit=limit or None):
                if not msg.text:
                    continue
                msg_count += 1

                parsed = parse_message(strip_markdown(msg.text))
                if not parsed:
                    total_skipped += 1
                    continue

                if is_duplicate(con, parsed["date"], parsed["amount"], parsed["card_last4"]):
                    total_duplicate += 1
                    continue

                if dry_run:
                    print(f"  [DRY] {parsed['date']} | *{parsed['card_last4']} | "
                          f"{parsed['category']} | {parsed['amount']:,.0f} {parsed['currency']} | "
                          f"{parsed['merchant']}")
                else:
                    row_id = save_to_db(con, parsed)
                    new_rows.append((row_id, parsed))
                    print(f"  ✓ {parsed['date']} | *{parsed['card_last4']} | "
                          f"{parsed['category']} | {parsed['amount']:,.0f} {parsed['currency']} | "
                          f"{parsed['merchant']}")

                total_parsed += 1

            print(f"  Messages scanned: {msg_count}")

        con.close()

        print(f"\n{'[DRY RUN] ' if dry_run else ''}Summary:")
        print(f"  Parsed:     {total_parsed}")
        print(f"  Duplicates: {total_duplicate} (skipped)")
        print(f"  No match:   {total_skipped}")

        if not dry_run and new_rows and not no_actual:
            print(f"\n🔄 Pushing {len(new_rows)} new transactions to Actual Budget...")
            push_to_actual(new_rows)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run",   action="store_true")
    parser.add_argument("--limit",     type=int, default=0, help="Max messages per source (0 = all)")
    parser.add_argument("--no-actual", action="store_true", help="Skip Actual Budget push")
    args = parser.parse_args()

    asyncio.run(fetch_history(args.dry_run, args.limit, args.no_actual))


if __name__ == "__main__":
    main()
