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
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

# Try multiple locations for .env file
ENV_PATHS = [
    Path(__file__).parent / ".env",
    Path.home() / ".env",
    Path("/data/bot/.env"),
]
for env_path in ENV_PATHS:
    if env_path.exists():
        load_dotenv(env_path)
        break

ACTUAL_URL      = os.environ.get("ACTUAL_URL") or os.getenv("ACTUAL_URL", "http://localhost:5006")
ACTUAL_PASSWORD = os.environ.get("ACTUAL_PASSWORD")
ACTUAL_FILE     = os.environ.get("ACTUAL_FILE")

if not ACTUAL_PASSWORD:
    raise ValueError("ACTUAL_PASSWORD environment variable is required")
if not ACTUAL_FILE:
    raise ValueError("ACTUAL_FILE environment variable is required")

CATEGORY_MAP = {
    "FOOD":      "Food",
    "TRANSPORT": "Transport",
    "SHOPPING":  "Shopping",
    "HEALTH":    "Health",
    "UTILITIES": "Utilities",
    "TELECOM":   "Telecom",
    "ATM":       "ATM",
    "TRANSFER":  "Transfer",
    "OTHER":     "General",
}


def push_to_actual(parsed: dict, account_name: Optional[str] = None, retries: int = 3) -> bool:
    """
    Write one parsed transaction to Actual Budget.
    Returns True on success, False on failure.

    parsed dict must have:
        date, time, amount, currency, category, merchant,
        payment_method, card_last4, transaction_type, source, raw_text
    """
    from actual import Actual, get_accounts
    from actual.queries import create_account, create_transaction
    from dedup import check_and_handle

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
            with Actual(base_url=ACTUAL_URL, password=ACTUAL_PASSWORD, file=ACTUAL_FILE) as actual:
                actual.download_budget()
                s        = actual.session
                accounts = get_accounts(s)

                acc = next((a for a in accounts if a.name == account_name), None)
                if not acc:
                    acc = create_account(s, account_name, initial_balance=0)
                    print(f"  📂 Created account: {account_name}")

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
                create_transaction(
                    s,
                    date=tx_date,
                    account=acc,
                    payee=parsed.get("merchant") or "Unknown",
                    notes=f"{parsed.get('payment_method') or ''} | {parsed.get('currency', 'UZS')}",
                    category=category,
                    amount=actual_amount,
                    imported_id=imported_id,
                    cleared=True,
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
