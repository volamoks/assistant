#!/usr/bin/env python3
"""
fix_transfers.py — исправить 87 неправильно загруженных transfer транзакций в Sure.

Проблема: transfers из finance.db залиты как обычные expense.
Решение:
  - from+to заполнены → удалить из Sure, создать как Sure Transfer (два linked entry)
  - from/to = NULL (P2P к чужим) → удалить из Sure, создать как expense
"""
import sys, sqlite3, requests
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from sink import (
    SURE_URL, _sure_headers, _all_sure_accounts,
    _get_or_create_account, push_to_sure,
    _resolve_account_name, _push_transfer_rails,
)

DB = Path(__file__).parent / "finance.db"

def delete_from_sure(imported_id: str) -> bool:
    """Find and delete a Sure transaction by imported_id in notes."""
    headers = _sure_headers()
    r = requests.get(f"{SURE_URL}/api/v1/transactions",
                     headers=headers,
                     params={"search": imported_id, "per_page": 10},
                     timeout=10)
    if not r.ok:
        return False
    txs = [t for t in r.json().get("transactions", [])
           if imported_id in (t.get("notes") or "")]
    for tx in txs:
        tx_id = tx.get("id")
        d = requests.delete(f"{SURE_URL}/api/v1/transactions/{tx_id}",
                            headers=headers, timeout=10)
        if d.ok:
            print(f"  🗑️  Deleted Sure tx {tx_id}")
    return len(txs) > 0

def main():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("""
        SELECT date, amount, currency, card_last4, source, merchant,
               from_account, to_account, sms_text
        FROM transactions
        WHERE type = 'transfer'
        ORDER BY date DESC
    """)
    rows = cur.fetchall()
    conn.close()

    print(f"Found {len(rows)} transfers in finance.db\n")

    real_transfers = [r for r in rows if r["from_account"] and r["to_account"]]
    p2p_expenses   = [r for r in rows if not r["from_account"] or not r["to_account"]]

    print(f"  Real account transfers (from→to): {len(real_transfers)}")
    print(f"  P2P to others (treat as expense): {len(p2p_expenses)}\n")

    # ── 1. Fix real transfers (batch) ─────────────────────────────────────────
    print("=== Fixing real transfers ===")
    batch = []
    for row in real_transfers:
        imported_id = f"{row['source']}-{row['date']}-{row['amount']}-{row['card_last4'] or 'X'}"
        delete_from_sure(imported_id)
        batch.append({
            "from_name":   _resolve_account_name(row["from_account"], row["card_last4"]),
            "to_name":     _resolve_account_name(row["to_account"],   row["card_last4"]),
            "amount":      row["amount"],
            "currency":    row["currency"] or "UZS",
            "date":        row["date"],
            "merchant":    row["merchant"] or "Transfer",
            "imported_id": imported_id,
        })
    if batch:
        from sink import push_transfers_batch
        push_transfers_batch(batch)

    # ── 2. Fix P2P → expense ───────────────────────────────────────────────────
    print("\n=== Fixing P2P transfers → expense ===")
    for row in p2p_expenses:
        imported_id = f"{row['source']}-{row['date']}-{row['amount']}-{row['card_last4'] or 'X'}"

        # Delete wrong entry from Sure
        delete_from_sure(imported_id)

        # Re-push as expense
        parsed = {
            "date":             row["date"],
            "amount":           row["amount"],
            "currency":         row["currency"] or "UZS",
            "merchant":         row["merchant"] or "P2P Transfer",
            "category":         "TRANSFER",
            "transaction_type": "debit",
            "source":           row["source"] or "SMS",
            "card_last4":       row["card_last4"],
            "payment_method":   row["source"] or "",
            "raw_text":         row["sms_text"] or "",
        }
        acc_name = _resolve_account_name(row["source"] or "SMS", row["card_last4"])
        push_to_sure(parsed, account_name=acc_name)

    print("\nDone ✅")

if __name__ == "__main__":
    main()
