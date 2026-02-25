"""
Sync finance.db → Actual Budget
- Reads unsynced expenses (actual_synced = 0) from finance.db
- Pushes them to Actual Budget via actualpy
- Marks synced rows with actual_synced = 1 + actual_tx_id

Usage:
    python3 sync_to_actual.py            # sync new only
    python3 sync_to_actual.py --all      # re-sync everything
    python3 sync_to_actual.py --dry-run  # preview, no writes
"""

import argparse
import os
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

from actual import Actual, get_accounts
from actual.queries import create_account, create_transaction

# ── Config ────────────────────────────────────────────
ACTUAL_URL      = os.environ.get("ACTUAL_URL") or os.getenv("ACTUAL_URL", "http://localhost:5006")
ACTUAL_PASSWORD = os.environ.get("ACTUAL_PASSWORD")
ACTUAL_FILE     = os.environ.get("ACTUAL_FILE")

# Validate required environment variables
if not ACTUAL_PASSWORD:
    sys.exit("❌ Error: ACTUAL_PASSWORD environment variable is required")
if not ACTUAL_FILE:
    sys.exit("❌ Error: ACTUAL_FILE environment variable is required")

DB_PATHS = [
    Path.home() / "Library/Mobile Documents/iCloud~md~obsidian/Documents/My Docs/Attachments/finance.db",
    Path.home() / "Library/Mobile Documents/com~apple~CloudDocs/abror/Attachments/finance.db",
    Path("/data/obsidian/Attachments/finance.db"),
]

# Map our categories → Actual Budget category names
CATEGORY_MAP = {
    "FOOD":       "Food",
    "TRANSPORT":  "Transport",
    "SHOPPING":   "Shopping",
    "HEALTH":     "Health",
    "UTILITIES":  "Utilities",
    "TELECOM":    "Telecom",
    "ATM":        "ATM",
    "TRANSFER":   "Transfer",
    "OTHER":      "General",
}


def find_db() -> Path:
    for p in DB_PATHS:
        if p.exists():
            return p
    sys.exit("❌ finance.db not found")


def ensure_actual_synced_column(con: sqlite3.Connection) -> None:
    try:
        con.execute("ALTER TABLE expenses ADD COLUMN actual_synced INTEGER DEFAULT 0")
        con.execute("ALTER TABLE expenses ADD COLUMN actual_tx_id TEXT")
        con.commit()
    except sqlite3.OperationalError:
        pass  # columns already exist


def get_or_create_account(s, accounts: list, card_last4: str):
    name = f"HUMO *{card_last4}" if card_last4 else "HUMO"
    acc = next((a for a in accounts if a.name == name), None)
    if not acc:
        acc = create_account(s, name, initial_balance=0)
        accounts.append(acc)
        print(f"  Created account: {name}")
    return acc


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--all",     action="store_true", help="Re-sync all rows")
    parser.add_argument("--dry-run", action="store_true", help="Preview only")
    args = parser.parse_args()

    db_path = find_db()
    con = sqlite3.connect(db_path)
    ensure_actual_synced_column(con)

    where = "" if args.all else "WHERE actual_synced = 0 OR actual_synced IS NULL"
    rows = con.execute(f"""
        SELECT id, date, amount, currency, category, merchant,
               card_last4, transaction_type, payment_method, raw_text
        FROM expenses
        {where}
        ORDER BY date ASC, time ASC
    """).fetchall()

    if not rows:
        print("✅ Nothing to sync")
        con.close()
        return

    print(f"{'[DRY RUN] ' if args.dry_run else ''}Syncing {len(rows)} rows → Actual Budget")

    if args.dry_run:
        for r in rows:
            print(f"  {r[1]} | {r[6] or '????'} | {r[4]} | {r[2]:,.0f} {r[3]} | {r[5]}")
        con.close()
        return

    with Actual(base_url=ACTUAL_URL, password=ACTUAL_PASSWORD, file=ACTUAL_FILE) as actual:
        actual.download_budget()
        s = actual.session
        accounts = get_accounts(s)

        synced = 0
        for row in rows:
            row_id, date_str, amount, currency, category, merchant, \
                card_last4, tx_type, payment_method, raw_text = row

            acc = get_or_create_account(s, accounts, card_last4)

            try:
                tx_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            except (ValueError, TypeError):
                tx_date = datetime.now().date()

            # Actual: negative amount = expense (debit), positive = income (credit)
            actual_amount = -amount if tx_type == "debit" else amount
            actual_category = CATEGORY_MAP.get((category or "OTHER").upper(), "General")
            imported_id = f"humo-{row_id}-{date_str}-{amount}"

            tx = create_transaction(
                s,
                date=tx_date,
                account=acc,
                payee=merchant or "Unknown",
                notes=f"{payment_method or ''} | {currency}",
                category=actual_category,
                amount=actual_amount,
                imported_id=imported_id,
                cleared=True,
            )

            con.execute(
                "UPDATE expenses SET actual_synced = 1, actual_tx_id = ? WHERE id = ?",
                (str(tx.id), row_id),
            )
            synced += 1
            print(f"  ✓ {date_str} | *{card_last4 or '????'} | {category} | {amount:,.0f} {currency} | {merchant}")

        actual.commit()
        con.commit()
        print(f"\n✅ Synced {synced} transactions")

    con.close()


if __name__ == "__main__":
    main()
