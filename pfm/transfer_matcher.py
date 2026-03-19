#!/usr/bin/env python3
"""
transfer_matcher.py — match debit/credit pairs across own cards = internal transfers

Logic:
  For every unmatched credit on an own card, search for a debit with:
    - same amount + currency
    - same date (or ±1 day for midnight crossings)
    - time difference ≤ 15 minutes (default)
    - different card/source (can't transfer to yourself on the same card)

  When a pair is found:
    - Both rows → type=transfer, matched_transfer_id=each other
    - Sure: delete wrong income entry, create proper linked Transfer via Rails

  Also promotes expired pending_match credits (>30 min, no pair) → income.

Usage:
    python3 transfer_matcher.py            # match all unmatched + promote expired
    python3 transfer_matcher.py --dry-run  # show pairs without writing
    python3 transfer_matcher.py --window 15  # time window in minutes (default 15)
"""
import os
import sys
import sqlite3
import requests
import argparse
from datetime import datetime, timedelta
from pathlib import Path

BASE       = Path(__file__).parent
DOCKER_DIR = BASE.parent / "openclaw-docker"
sys.path.insert(0, str(BASE))

from sink import SURE_URL, _sure_headers, push_transfers_batch

def _env(key: str, default: str = "") -> str:
    val = os.environ.get(key, "")
    if val:
        return val
    for p in [DOCKER_DIR / ".env", BASE.parent / ".env"]:
        try:
            for line in p.read_text().splitlines():
                if line.strip().startswith(f"{key}="):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
        except Exception:
            pass
    return default

FINANCE_DB = BASE / "finance.db"

OWN_SOURCES    = {"HUMO", "KAPITAL", "KAPITALBANK", "UZUM", "UZUMBANK", "SMS", "NBU"}
OWN_CARD_LAST4 = {"9396", "1066", "5175", "6079", "6807", "4521", "7936", "7834", "8515", "9445"}

def _sure_headers_local():
    return _sure_headers()

def _to_minutes(time_str: str) -> int | None:
    if not time_str:
        return None
    try:
        parts = time_str.strip().split(":")
        return int(parts[0]) * 60 + int(parts[1])
    except Exception:
        return None

def _time_diff_minutes(t1: str, t2: str) -> int:
    m1, m2 = _to_minutes(t1), _to_minutes(t2)
    if m1 is None or m2 is None:
        return 999
    return abs(m1 - m2)

def find_sure_tx(imported_id: str) -> str | None:
    """Find Sure transaction ID by imported_id stored in notes."""
    try:
        r = requests.get(
            f"{SURE_URL}/api/v1/transactions",
            headers=_sure_headers_local(),
            params={"search": imported_id, "per_page": 5},
            timeout=10,
        )
        for tx in r.json().get("transactions", []):
            if imported_id in (tx.get("notes") or ""):
                return tx["id"]
    except Exception:
        pass
    return None

def delete_sure_tx(sure_id: str) -> bool:
    try:
        r = requests.delete(
            f"{SURE_URL}/api/v1/transactions/{sure_id}",
            headers=_sure_headers_local(),
            timeout=10,
        )
        return r.ok
    except Exception:
        return False

def promote_sure_income(imported_id: str, from_name: str, amount: float,
                        currency: str, date: str, merchant: str) -> bool:
    """Push a pending_match credit to Sure as income (no debit pair found)."""
    from sink import _get_or_create_account, _transaction_exists, _sure_headers
    try:
        acc_id = _get_or_create_account(from_name, currency)
        if _transaction_exists(acc_id, imported_id):
            return True
        tx = {
            "account_id": acc_id,
            "date":       date,
            "amount":     abs(amount),
            "currency":   currency,
            "name":       merchant or from_name,
            "notes":      f"{imported_id} | promoted-income",
            "nature":     "income",
        }
        r = requests.post(f"{SURE_URL}/api/v1/transactions",
                          headers=_sure_headers(), json={"transaction": tx}, timeout=15)
        return r.ok
    except Exception as e:
        print(f"     ⚠️  promote income error: {e}")
        return False

def imported_id_for(row: sqlite3.Row) -> str:
    return f"{row['source']}-{row['date']}-{row['amount']}-{row['card_last4'] or 'X'}"

def resolve_account(source: str, card_last4: str | None) -> str:
    s = (source or "").upper()
    if s in ("HUMO", "HUMOCARD") and card_last4:
        return f"HUMO *{card_last4}"
    if s in ("KAPITAL", "KAPITALBANK") and card_last4:
        return f"KAPITAL *{card_last4}"
    if s in ("UZUM", "UZUMBANK") and card_last4:
        return f"Uzum *{card_last4}"
    if s == "NBU" and card_last4:
        return f"NBU *{card_last4}"
    if card_last4 == "7834":
        return "Visa *7834"
    return f"{source} *{card_last4}" if card_last4 else (source or "Unknown")

def promote_expired_pending(conn: sqlite3.Connection, dry_run: bool) -> int:
    """Promote pending_match credits older than 30 min to income."""
    cur = conn.cursor()
    cutoff = (datetime.now() - timedelta(minutes=30)).isoformat()
    cur.execute("""
        SELECT id, date, time, amount, currency, source, card_last4, merchant, sms_text
        FROM transactions
        WHERE type = 'pending_match'
          AND pending_until IS NOT NULL
          AND pending_until < ?
    """, (cutoff,))
    expired = cur.fetchall()
    if not expired:
        return 0

    print(f"\n⏰ Promoting {len(expired)} expired pending_match → income")
    count = 0
    for row in expired:
        from_name   = resolve_account(row["source"], row["card_last4"])
        imported_id = imported_id_for(row)
        merchant    = row["merchant"] or from_name

        print(f"  💰 {row['date']} {row['amount']:,.0f} {row['currency']} [{from_name}]")
        if dry_run:
            continue

        ok = promote_sure_income(imported_id, from_name, row["amount"],
                                 row["currency"] or "UZS", row["date"], merchant)
        cur.execute("""
            UPDATE transactions
            SET type='income', pending_until=NULL
            WHERE id=?
        """, (row["id"],))
        conn.commit()
        status = "✅" if ok else "💾 (Sure failed)"
        print(f"     → income {status}")
        count += 1

    return count

def run(window_minutes: int = 15, dry_run: bool = False):
    conn = sqlite3.connect(FINANCE_DB)
    conn.row_factory = sqlite3.Row
    cur  = conn.cursor()

    # 1. Promote expired pending_match first
    promote_expired_pending(conn, dry_run)

    # 2. All unmatched expense/transfer from own cards (debit side)
    cur.execute("""
        SELECT id, date, time, amount, currency, source, card_last4, merchant, type
        FROM transactions
        WHERE matched_transfer_id IS NULL
          AND type IN ('expense', 'transfer', 'pending_match')
          AND source IN ('HUMO','KAPITAL','KAPITALBANK','UZUM','UZUMBANK','SMS','NBU')
        ORDER BY date, time
    """)
    debits = cur.fetchall()

    # 3. All unmatched income/pending_match from own cards (credit side)
    cur.execute("""
        SELECT id, date, time, amount, currency, source, card_last4, merchant, type
        FROM transactions
        WHERE matched_transfer_id IS NULL
          AND type IN ('income', 'transfer', 'pending_match')
          AND source IN ('HUMO','KAPITAL','KAPITALBANK','UZUM','UZUMBANK','SMS','NBU')
        ORDER BY date, time
    """)
    credits = cur.fetchall()

    print(f"🔍 Matching {len(debits)} debits × {len(credits)} credits "
          f"(window={window_minutes}min, dry_run={dry_run})")

    matched_ids = set()
    pairs = []

    for debit in debits:
        if debit["id"] in matched_ids:
            continue

        for credit in credits:
            if credit["id"] in matched_ids:
                continue
            if credit["id"] == debit["id"]:
                continue

            # Same amount + currency
            if abs(debit["amount"] - credit["amount"]) > 0.01:
                continue
            if (debit["currency"] or "UZS") != (credit["currency"] or "UZS"):
                continue

            # Same date (or ±1 day)
            try:
                d1 = datetime.strptime(debit["date"], "%Y-%m-%d")
                d2 = datetime.strptime(credit["date"], "%Y-%m-%d")
                if abs((d1 - d2).days) > 1:
                    continue
            except Exception:
                continue

            # Time within window
            if _time_diff_minutes(debit["time"], credit["time"]) > window_minutes:
                continue

            # Must be different card (can't transfer to yourself on same card)
            if debit["card_last4"] and credit["card_last4"]:
                if debit["card_last4"] == credit["card_last4"]:
                    continue

            pairs.append((debit, credit))
            matched_ids.add(debit["id"])
            matched_ids.add(credit["id"])
            break

    print(f"✅ Found {len(pairs)} transfer pair(s)\n")

    for debit, credit in pairs:
        from_name   = resolve_account(debit["source"],  debit["card_last4"])
        to_name     = resolve_account(credit["source"], credit["card_last4"])
        merchant    = debit["merchant"] or credit["merchant"] or "Transfer"
        date        = debit["date"]
        amount      = debit["amount"]
        currency    = debit["currency"] or "UZS"

        debit_iid    = imported_id_for(debit)
        credit_iid   = imported_id_for(credit)
        transfer_iid = f"transfer-{debit['id']}-{credit['id']}"

        print(f"  💱 {date} {debit['time']} | {amount:,.0f} {currency}")
        print(f"     {from_name} → {to_name}  [{merchant}]")
        print(f"     debit={debit_iid}  credit={credit_iid}")

        if dry_run:
            print()
            continue

        # Update finance.db — both rows
        cur.execute("""
            UPDATE transactions
            SET type='transfer', is_transfer=1, matched_transfer_id=?,
                from_account=?, to_account=?, pending_until=NULL
            WHERE id=?
        """, (credit["id"], from_name, to_name, debit["id"]))
        cur.execute("""
            UPDATE transactions
            SET type='transfer', is_transfer=1, matched_transfer_id=?,
                from_account=?, to_account=?, pending_until=NULL
            WHERE id=?
        """, (debit["id"], from_name, to_name, credit["id"]))
        conn.commit()

        # Sure: delete the wrong income/pending entry (credit side)
        sure_credit_id = find_sure_tx(credit_iid)
        if sure_credit_id:
            deleted = delete_sure_tx(sure_credit_id)
            print(f"     🗑️  Deleted income entry from Sure: {sure_credit_id[:8]}…  {'✅' if deleted else '⚠️'}")

        # Sure: delete the expense entry (will be replaced by Transfer)
        sure_debit_id = find_sure_tx(debit_iid)
        if sure_debit_id:
            deleted = delete_sure_tx(sure_debit_id)
            print(f"     🗑️  Deleted expense entry from Sure: {sure_debit_id[:8]}…  {'✅' if deleted else '⚠️'}")

        # Sure: create proper linked Transfer using sink's working implementation
        ok = push_transfers_batch([{
            "from_name":   from_name,
            "to_name":     to_name,
            "amount":      amount,
            "currency":    currency,
            "date":        date,
            "merchant":    merchant,
            "imported_id": transfer_iid,
        }])
        print(f"     🔗 Sure Transfer created: {'✅' if ok else '⚠️ failed — check manually'}")
        print()

    conn.close()
    if not dry_run:
        print(f"Done. {len(pairs)} pair(s) matched and linked.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Match transfer pairs across own cards")
    parser.add_argument("--window",  type=int, default=15,   help="Time window in minutes (default 15)")
    parser.add_argument("--dry-run", action="store_true",    help="Show matches without writing")
    args = parser.parse_args()
    run(window_minutes=args.window, dry_run=args.dry_run)
