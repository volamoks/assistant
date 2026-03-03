"""
sink.py — single entry point to write to Actual Budget + finance.db

Usage:
    from sink import push_to_actual, save_to_finance_db
    push_to_actual(parsed_dict, account_name="HUMO *9396")
    save_to_finance_db(classification, parsed_dict, sms_text)

Deduplication & transfer-linking:
    Before writing, dedup.check_and_handle() is called:
    - 'duplicate' → same amount+direction on same account within ±1 day → skipped
    - 'transfer'  → same amount, opposite direction, different account  → create_transfer()
    - 'new'       → normal create_transaction()
"""
import os
import time
import sqlite3
import json
from datetime import datetime
from typing import Optional, Dict, Any
from pathlib import Path

from config import CATEGORY_MAP, validate_actual_config
from actual_client import get_actual_client, get_or_create_account, add_transaction

FINANCE_DB = Path(__file__).parent / "finance.db"

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


def save_to_finance_db(
    classification: Dict[str, Any],
    parsed: Optional[Dict] = None,
    sms_text: str = "",
    from_account: Optional[str] = None,
    to_account: Optional[str] = None
) -> bool:
    """
    Сохраняет транзакцию в finance.db (SQLite).
    
    Args:
        classification: результат classify_sms() {class, confidence, amount, currency}
        parsed: результат парсера (если есть) {date, time, amount, category, merchant, source, card_last4}
        sms_text: исходный текст SMS
        from_account: счёт с которого (для transfer)
        to_account: счёт на который (для transfer)
    
    Returns:
        True если сохранено, False если ошибка
    """
    try:
        conn = sqlite3.connect(FINANCE_DB)
        cur = conn.cursor()
        
        # Определяем тип
        sms_class = classification.get('class', 'unknown')
        if sms_class == 'transfer':
            tx_type = 'transfer'
            is_transfer = 1
        elif sms_class == 'transaction':
            tx_type = 'income' if (parsed or {}).get('transaction_type') == 'credit' else 'expense'
            is_transfer = 0
        else:
            tx_type = 'expense'
            is_transfer = 0
        
        # Данные из parsed или classification
        amount = (parsed or {}).get('amount') or classification.get('amount') or 0
        currency = (parsed or {}).get('currency') or classification.get('currency') or 'UZS'
        date = (parsed or {}).get('date') or datetime.now().strftime('%Y-%m-%d')
        time_val = (parsed or {}).get('time') or datetime.now().strftime('%H:%M:%S')
        category = (parsed or {}).get('category') or classification.get('reason', 'Unknown')
        merchant = (parsed or {}).get('merchant') or 'Unknown'
        source = (parsed or {}).get('source') or 'SMS'
        card_last4 = (parsed or {}).get('card_last4')
        
        # Для трансферов определяем счета
        if is_transfer and not from_account:
            # Пытаемся определить из текста
            if 'humo' in sms_text.lower():
                from_account = 'HUMO'
            if 'visa' in sms_text.lower():
                to_account = 'Visa'
        
        cur.execute("""
            INSERT INTO transactions (
                date, time, amount, currency, category, merchant,
                source, card_last4, sms_text,
                type, sms_class, confidence, is_transfer,
                from_account, to_account
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            date, time_val, amount, currency, category, merchant,
            source, card_last4, sms_text,
            tx_type, sms_class, classification.get('confidence'), is_transfer,
            from_account, to_account
        ))
        
        conn.commit()
        conn.close()
        
        print(f"  💾 finance.db: {tx_type} {amount:,.0f} {currency} ({sms_class})")
        return True
        
    except Exception as e:
        print(f"  ❌ Ошибка сохранения в finance.db: {e}")
        return False


def save_to_finance_db(
    classification: Dict[str, Any],
    parsed: Optional[Dict[str, Any]] = None,
    sms_text: str = "",
    from_account: Optional[str] = None,
    to_account: Optional[str] = None
) -> int:
    """
    Сохраняет транзакцию/трансфер в finance.db.
    
    Args:
        classification: результат classify_sms() {class, confidence, amount, currency}
        parsed: результат парсера (если есть)
        sms_text: оригинальный текст SMS
        from_account: счёт источника (для transfer)
        to_account: счёт назначения (для transfer)
    
    Returns:
        ID сохранённой записи
    """
    conn = sqlite3.connect(FINANCE_DB)
    cur = conn.cursor()
    
    sms_class = classification.get('class', 'unknown')
    confidence = classification.get('confidence', 0)
    amount = classification.get('amount') or (parsed.get('amount') if parsed else 0)
    currency = classification.get('currency') or (parsed.get('currency') if parsed else 'UZS')
    
    # Определяем тип
    if sms_class == 'transfer':
        tx_type = 'transfer'
        is_transfer = 1
    elif sms_class == 'transaction':
        tx_type = 'income' if (parsed and parsed.get('transaction_type') == 'credit') else 'expense'
        is_transfer = 0
    else:
        tx_type = 'expense'
        is_transfer = 0
    
    # Дата
    if parsed and 'date' in parsed:
        tx_date = parsed['date']
        tx_time = parsed.get('time', '')
    else:
        tx_date = datetime.now().strftime('%Y-%m-%d')
        tx_time = datetime.now().strftime('%H:%M')
    
    # Категория и мерчант
    category = parsed.get('category', 'Unknown') if parsed else sms_class
    merchant = parsed.get('merchant', '') if parsed else ''
    source = parsed.get('source', 'SMS') if parsed else 'SMS'
    card_last4 = parsed.get('card_last4') if parsed else None
    
    # Сохраняем
    cur.execute("""
        INSERT INTO transactions (
            date, time, amount, currency, category, merchant,
            source, card_last4, sms_text,
            type, sms_class, confidence, is_transfer,
            from_account, to_account
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        tx_date, tx_time, amount, currency, category, merchant,
        source, card_last4, sms_text,
        tx_type, sms_class, confidence, is_transfer,
        from_account, to_account
    ))
    
    tx_id = cur.lastrowid
    conn.commit()
    conn.close()
    
    print(f"  💾 finance.db: ID={tx_id}, type={tx_type}, amount={amount} {currency}")
    return tx_id
