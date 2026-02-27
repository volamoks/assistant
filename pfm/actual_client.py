from datetime import datetime
from typing import Optional, List
from actual import Actual, get_accounts
from actual.queries import create_account, create_transaction

from config import ACTUAL_URL, ACTUAL_PASSWORD, ACTUAL_FILE, validate_actual_config

def get_actual_client() -> Actual:
    """Returns an initialized Actual client. Ensure validate_actual_config() is called first."""
    validate_actual_config()
    actual = Actual(base_url=ACTUAL_URL, password=ACTUAL_PASSWORD, file=ACTUAL_FILE)
    actual.download_budget()
    return actual

def get_or_create_account(session, accounts: List, account_name: str):
    """Finds an existing account by name or creates a new one."""
    acc = next((a for a in accounts if a.name == account_name), None)
    if not acc:
        acc = create_account(session, account_name, initial_balance=0)
        accounts.append(acc) # Update the local list
        print(f"  📂 Created account: {account_name}")
    return acc

def add_transaction(session, account, date: datetime.date, payee: str, notes: str, category: str, amount: float, imported_id: str):
    """Creates a single transaction in Actual Budget."""
    return create_transaction(
        session,
        date=date,
        account=account,
        payee=payee or "Unknown",
        notes=notes or "",
        category=category,
        amount=amount,
        imported_id=imported_id,
        cleared=True,
    )
