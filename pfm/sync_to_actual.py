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
import sqlite3
import sys
from datetime import datetime

from actual import get_accounts

from config import CATEGORY_MAP, find_db
from actual_client import get_actual_client, get_or_create_account, add_transaction

def ensure_actual_synced_column(con: sqlite3.Connection) -> None:
    try:
        con.execute("ALTER TABLE expenses ADD COLUMN actual_synced INTEGER DEFAULT 0")
        con.execute("ALTER TABLE expenses ADD COLUMN actual_tx_id TEXT")
        con.commit()
    except sqlite3.OperationalError:
        pass  # columns already exist

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

    with get_actual_client() as actual:
        s = actual.session
        accounts = get_accounts(s)

        synced = 0
        for row in rows:
            row_id, date_str, amount, currency, category, merchant, \
                card_last4, tx_type, payment_method, raw_text = row

            account_name = f"HUMO *{card_last4}" if card_last4 else "HUMO"
            acc = get_or_create_account(s, accounts, account_name)

            try:
                tx_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            except (ValueError, TypeError):
                tx_date = datetime.now().date()

            # Actual: negative amount = expense (debit), positive = income (credit)
            actual_amount = -amount if tx_type == "debit" else amount
            actual_category = CATEGORY_MAP.get((category or "OTHER").upper(), "General")
            imported_id = f"humo-{row_id}-{date_str}-{amount}"

            tx = add_transaction(
                session=s,
                account=acc,
                date=tx_date,
                payee=merchant,
                notes=f"{payment_method or ''} | {currency}",
                category=actual_category,
                amount=actual_amount,
                imported_id=imported_id,
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
