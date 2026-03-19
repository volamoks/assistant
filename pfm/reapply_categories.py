#!/usr/bin/env python3
"""
reapply_categories.py — one-time script to push categories from finance.db to Sure.

Runs after fixing CATEGORY_ID_MAP with full UUIDs.
Only touches enriched transactions that have a mapped category.
"""
import sqlite3
import requests
import sys
from pathlib import Path

BASE = Path(__file__).parent
sys.path.insert(0, str(BASE))
from sink import SURE_URL, _sure_headers, CATEGORY_ID_MAP

DB = BASE / "finance.db"

def reapply(dry_run: bool = False, limit: int = 0):
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("""
        SELECT id, source, date, amount, currency, card_last4,
               enriched_category, merchant_clean, merchant
        FROM transactions
        WHERE is_enriched = 1
          AND enriched_category IS NOT NULL
          AND enriched_category NOT IN ('OTHER', 'TRANSFER', 'SUBSCRIPTION', 'ENTERTAINMENT')
        ORDER BY date DESC
    """ + (f" LIMIT {limit}" if limit else ""))
    rows = cur.fetchall()
    conn.close()

    print(f"Found {len(rows)} transactions to re-apply categories")
    ok_count = 0
    fail_count = 0

    for row in rows:
        category = row["enriched_category"]
        category_id = CATEGORY_ID_MAP.get(category)
        if not category_id:
            continue

        card = row["card_last4"] or "X"
        imported_id = f"{row['source']}-{row['date']}-{row['amount']}-{card}"
        merchant = row["merchant_clean"] or row["merchant"] or ""

        if dry_run:
            print(f"  [DRY] {imported_id} → {category} ({category_id[:8]}...)")
            ok_count += 1
            continue

        # Find transaction in Sure by imported_id in notes
        try:
            r = requests.get(
                f"{SURE_URL}/api/v1/transactions",
                headers=_sure_headers(),
                params={"search": imported_id, "per_page": 5},
                timeout=10,
            )
            txs = [t for t in r.json().get("transactions", [])
                   if imported_id in (t.get("notes") or "")]
            if not txs:
                fail_count += 1
                continue

            tx_id = txs[0]["id"]
            payload = {"transaction": {"category_id": category_id}}
            if merchant:
                payload["transaction"]["name"] = merchant

            r2 = requests.patch(
                f"{SURE_URL}/api/v1/transactions/{tx_id}",
                headers=_sure_headers(),
                json=payload,
                timeout=10,
            )
            if r2.ok:
                ok_count += 1
                if ok_count % 50 == 0:
                    print(f"  ... {ok_count}/{len(rows)} done")
            else:
                print(f"  ⚠️  PATCH failed for {imported_id}: {r2.status_code} {r2.text[:100]}")
                fail_count += 1
        except Exception as e:
            print(f"  ⚠️  Error for {imported_id}: {e}")
            fail_count += 1

    print(f"\nDone: {ok_count} updated, {fail_count} failed/missing")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()
    reapply(dry_run=args.dry_run, limit=args.limit)
