"""
sink.py — single entry point to write a parsed transaction to Actual Budget.

Usage:
    from sink import push_to_actual
    push_to_actual(parsed_dict, account_name="HUMO *9396")

Deduplication & transfer-linking:
    Before writing, dedup.check_and_handle() is called:
    - 'duplicate' → same amount+direction on same account within ±1 day → skipped
    - 'transfer'  → same amount, opposite direction, different account  → create_transfer()
    - 'new'       → normal create_transaction()
"""
import os
import time
from datetime import datetime
from typing import Optional

from config import CATEGORY_MAP, validate_actual_config
from actual_client import get_actual_client, get_or_create_account, add_transaction

def push_to_actual(parsed: dict, account_name: Optional[str] = None, retries: int = 3) -> bool:
    """
    Write one parsed transaction to Actual Budget.
    Returns True on success, False on failure.

    parsed dict must have:
        date, time, amount, currency, category, merchant,
        payment_method, card_last4, transaction_type, source, raw_text
    """
    from actual import get_accounts
    from dedup import check_and_handle

    validate_actual_config()

    # Determine account name from parsed data if not provided
    if not account_name:
        source = parsed.get("source", "UNKNOWN")
        last4  = parsed.get("card_last4")
        account_name = f"{source} *{last4}" if last4 else source

    # imported_id: unique per source+card+date+amount (keeps Actual idempotent for same source)
    imported_id = (
        f"{parsed['source']}-{parsed['date']}-"
        f"{parsed['amount']}-{parsed.get('card_last4', 'X')}"
    )

    category = CATEGORY_MAP.get((parsed.get("category") or "OTHER").upper(), "General")

    try:
        tx_date = datetime.strptime(parsed["date"], "%Y-%m-%d").date()
    except (ValueError, TypeError):
        tx_date = datetime.now().date()

    # Actual convention: negative = money out (debit), positive = money in (credit)
    actual_amount = -parsed["amount"] if parsed["transaction_type"] == "debit" else parsed["amount"]

    for attempt in range(1, retries + 1):
        try:
            with get_actual_client() as actual:
                s        = actual.session
                accounts = get_accounts(s)

                acc = get_or_create_account(s, accounts, account_name)

                # ── Smart dedup / transfer linking ────────────────────────────
                result = check_and_handle(
                    s, parsed, tx_date, actual_amount, acc, accounts
                )

                if result == "duplicate":
                    # Already in Actual — nothing to do
                    return True

                if result == "transfer":
                    # Transfer was linked inside check_and_handle; just commit
                    actual.commit()
                    return True

                # ── result == "new" → write normal transaction ────────────────
                add_transaction(
                    session=s,
                    account=acc,
                    date=tx_date,
                    payee=parsed.get("merchant"),
                    notes=f"{parsed.get('payment_method') or ''} | {parsed.get('currency', 'UZS')}",
                    category=category,
                    amount=actual_amount,
                    imported_id=imported_id,
                )
                actual.commit()
            return True

        except Exception as e:
            if attempt < retries:
                print(f"  ⚠️  Actual Budget error (attempt {attempt}/{retries}): {e} — retrying...")
                time.sleep(2 ** attempt)
            else:
                print(f"  ❌  Failed to push to Actual Budget after {retries} attempts: {e}")
                return False

    return False
