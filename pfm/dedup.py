"""
dedup.py — Smart deduplication and transfer-linking for the PFM pipeline.

When push_to_actual() is called, this module checks Actual Budget for:

  1. DUPLICATE — same amount + same direction + same account, within DATE_WINDOW days
     → returned as "duplicate", transaction is skipped

  2. TRANSFER — same amount + OPPOSITE direction + a DIFFERENT account, within DATE_WINDOW days
               AND no card number visible in the SMS (we can't know which account counterpart is)
     → returned as "transfer", create_transfer() is called to link both sides

  3. NEW — no match found
     → normal create_transaction()

Usage (called automatically from sink.py):
    result = check_and_handle(s, parsed, date, actual_amount, account_obj, accounts_all)
    # result is one of: "duplicate", "transfer", "new"
"""
from __future__ import annotations

import datetime
from typing import Optional

DATE_WINDOW = 1   # days ± to search for a matching transaction
# Actual stores amounts as integers (cents × 100), so 1 700 UZS → -170000
# We compare using the same rounding that create_transaction uses internally.


def _actual_int(amount_float: float) -> int:
    """Convert float amount to Actual internal integer (×100, rounded)."""
    return round(amount_float * 100)


def find_match(
    s,                          # SQLAlchemy session (from `actual.session`)
    date: datetime.date,
    amount_float: float,        # positive float (e.g. 1700.0)
    tx_type: str,               # 'debit' or 'credit'
    current_account_id: str,    # Actual account UUID to exclude from same-acct search
) -> Optional[object]:          # returns Transactions object or None
    """
    Search Actual for a transaction matching amount within ±DATE_WINDOW days.
    Returns (transaction, match_type) where match_type is:
      'duplicate' — same account, same direction
      'transfer'  — different account, opposite direction
      None        — no match
    """
    from actual.database import Transactions
    from actual.queries import _transactions_base_query  # noqa (internal)

    start = date - datetime.timedelta(days=DATE_WINDOW)
    end   = date + datetime.timedelta(days=DATE_WINDOW + 1)

    # Actual stores debit as negative, credit as positive integers (×100)
    debit_int  = -_actual_int(amount_float)   # e.g. -170000
    credit_int = +_actual_int(amount_float)   # e.g. +170000

    same_direction_int = debit_int  if tx_type == "debit"  else credit_int
    oppo_direction_int = credit_int if tx_type == "debit"  else debit_int

    query = _transactions_base_query(s, start, end)
    results = s.exec(query).all()

    # Filter out already-linked transfer transactions (they have transferred_id set)
    unlinked = [t for t in results if not t.transferred_id and not t.tombstone]

    # 1. Same account + same direction → duplicate
    for t in unlinked:
        if t.acct == current_account_id and t.amount == same_direction_int:
            return t, "duplicate"

    # 2. Different account + opposite direction → potential transfer
    for t in unlinked:
        if t.acct != current_account_id and t.amount == oppo_direction_int:
            return t, "transfer"

    return None, None


def check_and_handle(
    s,
    parsed: dict,
    date: datetime.date,
    actual_amount: float,       # signed float as used in sink.py (negative for debit)
    current_account,            # Accounts object (already fetched)
    all_accounts: list,         # all Accounts objects
) -> str:
    """
    Main entry point called from sink.py before create_transaction.

    Returns:
      'duplicate' → caller must skip this transaction
      'transfer:<notes>' → caller must call create_transfer() instead
      'new'        → caller proceeds with normal create_transaction()
    """
    from actual.queries import create_transfer

    amount_abs = abs(actual_amount)     # always positive
    tx_type    = parsed.get("transaction_type", "debit")

    match_tx, match_type = find_match(
        s,
        date,
        amount_abs,
        tx_type,
        current_account.id,
    )

    if match_type is None:
        return "new"

    if match_type == "duplicate":
        acct_name = current_account.name
        print(f"  ♻️  Duplicate detected — skipping "
              f"{amount_abs:,.0f} UZS on {acct_name} (already in Actual)")
        return "duplicate"

    if match_type == "transfer":
        # Find the Accounts object for the matching transaction
        other_account = next(
            (a for a in all_accounts if a.id == match_tx.acct), None
        )
        if not other_account:
            # Can't resolve account — treat as new transaction
            return "new"

        # Determine which is source and which is destination
        if tx_type == "debit":
            source_acc = current_account
            dest_acc   = other_account
        else:
            source_acc = other_account
            dest_acc   = current_account

        notes = (f"Auto-linked transfer | "
                 f"{parsed.get('payment_method', '')} | "
                 f"{parsed.get('currency', 'UZS')}")

        try:
            # Remove the existing "orphan" credit transaction before creating the linked pair.
            # We tombstone it so Actual syncs the deletion cleanly.
            match_tx.tombstone = 1
            s.add(match_tx)

            create_transfer(s, date, source_acc, dest_acc, amount_abs, notes=notes)
            print(f"  🔗 Transfer linked: {source_acc.name} → {dest_acc.name} "
                  f"{amount_abs:,.0f} {parsed.get('currency', 'UZS')}")
            return "transfer"
        except Exception as e:
            print(f"  ⚠️  Transfer link failed ({e}), saving as regular transaction")
            return "new"

    return "new"
