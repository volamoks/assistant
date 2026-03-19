"""
sink.py — single entry point to write parsed transactions to Sure PFM + finance.db

Usage:
    from sink import push_to_sure, save_to_finance_db
    push_to_sure(parsed_dict, account_name="HUMO *9396")
    save_to_finance_db(classification, parsed_dict, sms_text)

Sure API: POST /api/v1/transactions
    Header: X-Api-Key: <key>
    Set SURE_API_KEY in .env

Deduplication:
    Uses imported_id (source+date+amount+card_last4) stored in transaction notes.
    Transfers (from+to both set) → Sure Transfer via Rails runner (two linked entries).
    P2P without from/to → regular expense.
"""
import os
import time
import sqlite3
import json
import subprocess
import requests
from datetime import datetime
from typing import Optional, Dict, Any
from pathlib import Path

try:
    from normalizer import normalize as _normalize_tx
except ImportError:
    _normalize_tx = None

FINANCE_DB = Path(__file__).parent / "finance.db"

# ── Config ─────────────────────────────────────────────────────────────────────

def _env(key: str, default: str = "") -> str:
    val = os.environ.get(key, "")
    if val:
        return val
    for env_path in [
        Path(__file__).parent.parent / "openclaw-docker" / ".env",
        Path(__file__).parent.parent / ".env",
    ]:
        try:
            for line in env_path.read_text().splitlines():
                line = line.strip()
                if line.startswith(f"{key}="):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
        except Exception:
            pass
    return default

SURE_URL     = _env("SURE_URL", "http://localhost:3020")
SURE_API_KEY = _env("SURE_API_KEY", "")

# ── Own accounts — credits from these = transfer, not income ─────────────────
# Add card last4 digits whenever you get a new card
OWN_CARD_LAST4 = {"9396", "1066", "5175", "6079", "6807", "4521", "7936", "7834"}
OWN_ACCOUNT_KEYWORDS = {
    # HUMO ↔ Visa / HUMO ↔ HUMO
    "humo to visa", "humo kb to visa", "visa uzs kb to humo",
    "kap24 humo2humo", "kap24new sp p2p", "upay humo2humo",
    # Uzum internal
    "uzumbank perevod", "uzum perevod",
    # Kapitalbank internal deposit (savings → card)
    # NOTE: "frb kapital 24" is salary (external) — do NOT add here
    "dep uzs 2 visa", "dep uzs2visa", "dep usd 2 visa",
    "kap24 deposit",
    # Generic
    "between accounts", "mezhdu schetami", "o'z hisoblar", "o'z hisobim",
    "internal transfer", "own account",
}

def _is_own_transfer(merchant: str, raw_text: str) -> bool:
    """True if a credit SMS is actually a transfer from own account (not external income)."""
    text = ((merchant or "") + " " + (raw_text or "")).lower()
    # Check own card digits in the text
    for last4 in OWN_CARD_LAST4:
        if last4 in text:
            return True
    # Check known own-transfer keywords
    return any(kw in text for kw in OWN_ACCOUNT_KEYWORDS)

# Sure category IDs (fetched from Sure Rails runner — full UUIDs)
CATEGORY_ID_MAP: Dict[str, Optional[str]] = {
    "TRANSPORT":   "90541606-86a5-45cc-8de2-fcb5686840ac",  # Transportation
    "FOOD":        "f2cc77ee-1bda-4a9f-a7ee-a50b9a04a1f3",  # Food & Drink
    "HEALTH":      "51d1dded-9649-40ac-8b41-144b9191be0d",  # Healthcare
    "TELECOM":     "086fc7f4-bd38-4ce7-94d8-e8f81b87f9d3",  # Utilities
    "UTILITIES":   "086fc7f4-bd38-4ce7-94d8-e8f81b87f9d3",  # Utilities
    "SHOPPING":    "8b4ecd61-3b54-4b6f-92d3-b6b8de46e3b7",  # Shopping
    "ATM":         "5993de93-a327-426b-8356-3887d2b3a506",  # Fees
    "INCOME":      "f73a0d8b-8fe3-4bea-a2ed-e2a827da9504",  # Income
    "TRANSFER":    None,        # Handled as Sure Transfer, not regular tx
    "OTHER":       None,
}

# ── Sure API helpers ────────────────────────────────────────────────────────────

def _sure_headers() -> dict:
    if not SURE_API_KEY:
        raise RuntimeError("SURE_API_KEY not set in .env")
    return {
        "X-Api-Key": SURE_API_KEY,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

def _all_sure_accounts() -> list:
    """Fetch all Sure accounts (handles pagination)."""
    accounts, page = [], 1
    while True:
        r = requests.get(f"{SURE_URL}/api/v1/accounts",
                         headers=_sure_headers(),
                         params={"page": page, "per_page": 100}, timeout=10)
        r.raise_for_status()
        resp = r.json()
        batch = resp.get("accounts", [])
        accounts.extend(batch)
        if page >= resp.get("pagination", {}).get("total_pages", 1):
            break
        page += 1
    return accounts

def _get_or_create_account(account_name: str, currency: str = "UZS") -> str:
    """Return Sure account ID, creating via Rails runner if not found."""
    for acc in _all_sure_accounts():
        if acc.get("name") == account_name:
            return acc["id"]

    script = (
        f"family = Family.first; "
        f"unless Account.exists?(name: '{account_name}', family: family); "
        f"  Account.create!(name: '{account_name}', family: family, "
        f"    accountable: Depository.new, currency: '{currency}', balance: 0, status: 'active'); "
        f"end"
    )
    subprocess.run(["docker", "exec", "sure", "bin/rails", "runner", script],
                   capture_output=True, timeout=15)

    for acc in _all_sure_accounts():
        if acc.get("name") == account_name:
            return acc["id"]

    raise RuntimeError(f"Failed to create Sure account '{account_name}'")

def _transaction_exists(account_id: str, imported_id: str) -> bool:
    r = requests.get(
        f"{SURE_URL}/api/v1/transactions",
        headers=_sure_headers(),
        params={"account_id": account_id, "search": imported_id, "per_page": 5},
        timeout=10,
    )
    if not r.ok:
        return False
    return any(imported_id in (t.get("notes") or "") for t in r.json().get("transactions", []))

# ── Transfer via Rails runner ───────────────────────────────────────────────────

def _push_transfer_rails(
    from_name: str, to_name: str,
    amount: float, currency: str, date: str,
    merchant: str, imported_id: str,
) -> bool:
    """Create a proper Sure Transfer via Rails runner. Single call per transfer."""
    return push_transfers_batch([{
        "from_name":   from_name,
        "to_name":     to_name,
        "amount":      amount,
        "currency":    currency,
        "date":        date,
        "merchant":    merchant,
        "imported_id": imported_id,
    }])

def push_transfers_batch(transfers: list) -> bool:
    """
    Create multiple Sure Transfers in a single Rails runner call (avoids repeated startup overhead).
    Each transfer: {from_name, to_name, amount, currency, date, merchant, imported_id}
    """
    if not transfers:
        return True

    # Build Ruby array literal
    items = []
    for t in transfers:
        note    = str(t["imported_id"])[:80].replace("'", "").replace("\\", "")
        name    = str(t["merchant"] or "Transfer")[:60].replace("'", "").replace("\\", "")
        fr      = str(t["from_name"]).replace("'", "")
        to      = str(t["to_name"]).replace("'", "")
        amt     = abs(float(t["amount"]))
        cur     = str(t["currency"])
        dt      = str(t["date"])
        items.append(
            f"{{from: '{fr}', to: '{to}', amount: {amt}, "
            f"currency: '{cur}', date: '{dt}', name: '{name}', note: '{note}'}}"
        )

    script = """
family = Family.first
transfers = [ """ + ", ".join(items) + """ ]
transfers.each do |t|
  from_acc = family.accounts.find_by(name: t[:from])
  to_acc   = family.accounts.find_by(name: t[:to])
  unless from_acc && to_acc
    puts "SKIP:#{t[:note]}:account_not_found #{t[:from]}->#{t[:to]}"
    next
  end
  next if family.entries.where("entries.notes LIKE ?", "%#{t[:note]}%").exists?
  outflow = from_acc.entries.create!(
    name: t[:name], date: t[:date], amount: t[:amount], currency: t[:currency],
    notes: t[:note], entryable_type: 'Transaction', entryable_attributes: {}
  )
  inflow = to_acc.entries.create!(
    name: t[:name], date: t[:date], amount: -t[:amount], currency: t[:currency],
    notes: t[:note], entryable_type: 'Transaction', entryable_attributes: {}
  )
  Transfer.create!(inflow_transaction: inflow.entryable,
                   outflow_transaction: outflow.entryable, status: 'confirmed')
  puts "OK:#{t[:note]}"
end
"""
    result = subprocess.run(
        ["docker", "exec", "sure", "bin/rails", "runner", script],
        capture_output=True, text=True, timeout=60,
    )
    output = result.stdout + result.stderr
    ok_count   = output.count("OK:")
    skip_count = output.count("SKIP:")
    if ok_count or skip_count:
        print(f"  🔄 Transfers: {ok_count} created, {skip_count} skipped")
        return True
    if result.returncode != 0:
        print(f"  ❌ Transfer Rails error: {output[:200]}")
        return False
    return True

# ── Account name resolver ───────────────────────────────────────────────────────

def _resolve_account_name(generic: str, card_last4: Optional[str]) -> str:
    """Map generic account name (HUMO/Visa/Uzum) to Sure account name with card digits."""
    generic_upper = (generic or "").upper()
    if generic_upper in ("HUMO", "HUMOCARD") and card_last4:
        return f"HUMO *{card_last4}"
    if generic_upper in ("VISA", "VISA CARD"):
        return "Visa *7834"
    if generic_upper in ("UZUM", "UZUMBANK"):
        return "Uzum *4521"
    if generic_upper in ("KAPITAL", "KAPITALBANK"):
        return f"Kapitalbank *{card_last4}" if card_last4 else "Kapitalbank"
    return generic or "Unknown"

# ── Main public functions ───────────────────────────────────────────────────────

def push_to_sure(
    parsed: dict,
    account_name: Optional[str] = None,
    retries: int = 3,
    from_account: Optional[str] = None,
    to_account: Optional[str] = None,
) -> bool:
    """
    Write one parsed transaction to Sure PFM.
    - If from_account + to_account are set → Sure Transfer (two linked entries)
    - Otherwise → regular income/expense transaction
    Returns True on success (including duplicate skip), False on failure.
    """
    # pending_match: hold off pushing to Sure — transfer_matcher will decide
    if parsed.get("type") == "pending_match":
        print(f"  ⏳ Pending match — not pushed to Sure yet")
        return True

    if not account_name:
        source = parsed.get("source", "UNKNOWN")
        last4  = parsed.get("card_last4")
        account_name = f"{source} *{last4}" if last4 else source

    imported_id = (
        f"{parsed.get('source','X')}-{parsed.get('date','?')}-"
        f"{parsed.get('amount',0)}-{parsed.get('card_last4','X')}"
    )

    # ── Transfer between own accounts ──────────────────────────────────────────
    if from_account and to_account:
        card_last4 = parsed.get("card_last4")
        from_name = _resolve_account_name(from_account, card_last4)
        to_name   = _resolve_account_name(to_account, card_last4)
        return _push_transfer_rails(
            from_name=from_name,
            to_name=to_name,
            amount=parsed.get("amount", 0),
            currency=parsed.get("currency", "UZS"),
            date=parsed.get("date", datetime.now().strftime("%Y-%m-%d")),
            merchant=parsed.get("merchant", ""),
            imported_id=imported_id,
        )

    # ── Regular income / expense ───────────────────────────────────────────────
    is_credit = parsed.get("transaction_type") == "credit"
    if is_credit and _is_own_transfer(parsed.get("merchant", ""), parsed.get("raw_text", "")):
        # Credit from own card — incoming side of an own-account transfer
        nature       = "income"
        category_key = "TRANSFER"
    else:
        nature       = "income" if is_credit else "expense"
        category_key = (parsed.get("category") or "OTHER").upper()
    category_id  = CATEGORY_ID_MAP.get(category_key)  # None → don't send

    try:
        tx_date = datetime.strptime(parsed["date"], "%Y-%m-%d").strftime("%Y-%m-%d")
    except (ValueError, TypeError):
        tx_date = datetime.now().strftime("%Y-%m-%d")

    for attempt in range(1, retries + 1):
        try:
            account_id = _get_or_create_account(account_name)

            if _transaction_exists(account_id, imported_id):
                print(f"  ⏭️  Sure: duplicate skipped ({imported_id})")
                return True

            tx: Dict[str, Any] = {
                "account_id": account_id,
                "date":       tx_date,
                "amount":     abs(parsed["amount"]),
                "currency":   parsed.get("currency", "UZS"),
                "name":       parsed.get("merchant") or account_name,
                "notes":      f"{imported_id} | {parsed.get('payment_method', '')} | {parsed.get('raw_text', '')[:80]}",
                "nature":     nature,
            }
            if category_id:
                tx["category_id"] = category_id

            r = requests.post(f"{SURE_URL}/api/v1/transactions",
                              headers=_sure_headers(), json={"transaction": tx}, timeout=15)
            r.raise_for_status()
            tx_id = r.json().get("transaction", {}).get("id", "?")
            cat_label = category_key if category_id else "—"
            print(f"  ✅ Sure: {nature} {parsed['amount']:,.0f} {parsed.get('currency','UZS')} "
                  f"[{cat_label}] → {account_name} (id={tx_id})")
            return True

        except RuntimeError as e:
            print(f"  ⚠️  Sure config error: {e}")
            return False
        except Exception as e:
            if attempt < retries:
                print(f"  ⚠️  Sure error (attempt {attempt}/{retries}): {e} — retrying...")
                time.sleep(2 ** attempt)
            else:
                print(f"  ❌ Failed to push to Sure after {retries} attempts: {e}")
                return False

    return False


def save_to_finance_db(
    classification: Dict[str, Any],
    parsed: Optional[Dict[str, Any]] = None,
    sms_text: str = "",
    from_account: Optional[str] = None,
    to_account: Optional[str] = None,
) -> int:
    """Save transaction to local finance.db (SQLite backup, always runs)."""
    try:
        conn = sqlite3.connect(FINANCE_DB)
        cur  = conn.cursor()

        sms_class  = classification.get("class", "unknown")
        confidence = classification.get("confidence", 0)
        amount     = (parsed or {}).get("amount") or classification.get("amount") or 0
        currency   = (parsed or {}).get("currency") or classification.get("currency") or "UZS"

        tx_date    = (parsed or {}).get("date") or datetime.now().strftime("%Y-%m-%d")
        tx_time    = (parsed or {}).get("time") or datetime.now().strftime("%H:%M")
        category   = (parsed or {}).get("category") or sms_class
        merchant   = (parsed or {}).get("merchant") or ""
        source     = (parsed or {}).get("source") or "SMS"
        card_last4 = (parsed or {}).get("card_last4")

        # Use normalizer to determine type (no LLM, rule-based)
        pending_until = None
        if sms_class == "transfer":
            tx_type, is_transfer = "transfer", 1
        elif _normalize_tx and parsed:
            normalized = _normalize_tx({**parsed, "raw_text": sms_text or ""})
            tx_type      = normalized.get("type", "expense")
            is_transfer  = 1 if tx_type == "transfer" else 0
            pending_until = normalized.get("pending_until")
        elif sms_class == "transaction":
            tx_type = "income" if (parsed or {}).get("transaction_type") == "credit" else "expense"
            is_transfer = 0
        else:
            tx_type, is_transfer = "expense", 0

        cur.execute("""
            INSERT INTO transactions (
                date, time, amount, currency, category, merchant,
                source, card_last4, sms_text,
                type, sms_class, confidence, is_transfer,
                from_account, to_account, pending_until
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            tx_date, tx_time, amount, currency, category, merchant,
            source, card_last4, sms_text,
            tx_type, sms_class, confidence, is_transfer,
            from_account, to_account, pending_until,
        ))

        tx_id = cur.lastrowid
        conn.commit()
        conn.close()
        print(f"  💾 finance.db: ID={tx_id}, {tx_type} {amount:,.0f} {currency}")
        return tx_id

    except Exception as e:
        print(f"  ❌ finance.db error: {e}")
        return 0


# ── Legacy shim ─────────────────────────────────────────────────────────────────

def push_to_actual(parsed: dict, account_name: Optional[str] = None, retries: int = 3) -> bool:
    """Deprecated alias → push_to_sure."""
    return push_to_sure(parsed, account_name, retries)
