#!/usr/bin/env python3
"""
import_sms_history.py — one-time import of Kapitalbank/Uzum/NBU SMS from chat.db

Uses parsers directly (no LLM) — fast.
Transactions land in finance.db with is_enriched=0 → nightly enricher handles LLM.

Usage:
    python3 import_sms_history.py --dry-run   # preview counts
    python3 import_sms_history.py             # import all
    python3 import_sms_history.py --no-sure   # only finance.db, skip Sure API
"""
import argparse
import shutil
import sqlite3
import time
from datetime import datetime
from pathlib import Path
import sys

BASE = Path(__file__).parent
sys.path.insert(0, str(BASE))

from parsers.kapital import parse_kapital
from parsers.uzum    import parse_uzum
from parsers.nbu     import parse as parse_nbu
from sink            import push_to_sure, save_to_finance_db, _transaction_exists

CHAT_DB  = Path.home() / "Library/Messages/chat.db"
CHAT_TMP = Path("/tmp/chat_sms_copy.db")
DB       = BASE / "finance.db"

SENDER_PARSER = {
    "kapital":    parse_kapital,  # matches Kapital, Kapitalbank, KapitalBank, KAPITALBANK
    "uzum":       parse_uzum,     # matches Uzum, UzumBank, Uzum_Bank, etc.
    "nbu":        parse_nbu,      # matches NBU
}


def _get_chat_db() -> Path:
    """Return path to a readable copy of chat.db."""
    # Try fresh copy first
    if CHAT_TMP.exists():
        age = time.time() - CHAT_TMP.stat().st_mtime
        if age < 300:
            return CHAT_TMP
    # Try to copy ourselves
    try:
        shutil.copy2(CHAT_DB, CHAT_TMP)
        return CHAT_TMP
    except PermissionError:
        if CHAT_TMP.exists():
            print("⚠️  Using stale chat.db copy (no FDA)")
            return CHAT_TMP
        raise RuntimeError("Cannot read chat.db — grant Full Disk Access to Terminal")


def _pick_parser(sender: str):
    s = sender.lower()
    if "nbu" in s:
        return parse_nbu
    if "uzum" in s:
        return parse_uzum
    return parse_kapital


def fetch_sms() -> list[tuple]:
    """Return all bank SMS from chat.db as (rowid, sender, text, date_str)."""
    db_path = _get_chat_db()
    conn = sqlite3.connect(db_path)
    cur  = conn.cursor()
    cur.execute("""
        SELECT m.ROWID, h.id, m.text,
               datetime(m.date/1000000000 + 978307200, 'unixepoch', 'localtime')
        FROM message m
        JOIN handle h ON m.handle_id = h.ROWID
        WHERE (h.id LIKE '%kapital%' OR h.id LIKE '%uzum%' OR h.id LIKE '%nbu%')
          AND m.is_from_me = 0
          AND m.text IS NOT NULL AND m.text != ''
        ORDER BY m.ROWID ASC
    """)
    rows = cur.fetchall()
    conn.close()
    return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run",  action="store_true", help="Preview only, no writes")
    parser.add_argument("--no-sure",  action="store_true", help="Skip Sure API, only finance.db")
    parser.add_argument("--limit",    type=int, default=0, help="Max SMS to process (0=all)")
    args = parser.parse_args()

    print("📥 Reading SMS from chat.db...")
    rows = fetch_sms()
    print(f"   Found {len(rows)} bank SMS total")

    if args.limit:
        rows = rows[-args.limit:]  # take most recent
        print(f"   Limited to last {args.limit}")

    parsed_count  = 0
    skipped_count = 0
    dup_count     = 0
    sure_ok       = 0

    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row

    for rowid, sender, text, msg_date in rows:
        parse_fn = _pick_parser(sender)
        parsed   = parse_fn(text)

        if parsed is None:
            skipped_count += 1
            continue

        # Build imported_id for dedup
        card   = parsed.get("card_last4") or "X"
        imp_id = f"{parsed['source']}-{parsed['date']}-{parsed['amount']}-{card}"

        # Check dedup in finance.db
        cur = conn.cursor()
        cur.execute(
            "SELECT id FROM transactions WHERE source=? AND date=? AND amount=? AND (card_last4=? OR (card_last4 IS NULL AND ?='X'))",
            (parsed["source"], parsed["date"], parsed["amount"], card, card)
        )
        if cur.fetchone():
            dup_count += 1
            continue

        if args.dry_run:
            print(f"  [DRY] {parsed['source']} *{card} | {parsed['date']} | "
                  f"{parsed['amount']:,.0f} {parsed['currency']} | {parsed.get('merchant','')[:30]}")
            parsed_count += 1
            continue

        # Save to finance.db
        save_to_finance_db({}, parsed, text)
        parsed_count += 1

        # Push to Sure (unless --no-sure)
        if not args.no_sure:
            account_name = f"{parsed['source']} *{card}" if card != "X" else parsed["source"]
            ok = push_to_sure(parsed, account_name=account_name)
            if ok:
                sure_ok += 1

        if parsed_count % 50 == 0:
            print(f"  ... {parsed_count} imported")

    conn.close()

    print(f"\n{'[DRY] ' if args.dry_run else ''}Done:")
    print(f"  Parsed:    {parsed_count}")
    print(f"  Skipped:   {skipped_count} (promo/info/unrecognized)")
    print(f"  Duplicate: {dup_count}")
    if not args.dry_run and not args.no_sure:
        print(f"  Sure:      {sure_ok} pushed")

    if not args.dry_run and parsed_count > 0:
        print(f"\n→ Run enricher to categorize: python3 enricher.py")


if __name__ == "__main__":
    main()
