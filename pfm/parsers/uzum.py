"""
Parser: Uzum Bank SMS notifications.

Supported formats:
  Spisanie, karta ****7936: 272900.00 UZS, UZUM TEZKOR. UZ. Dostupno: 74606.12 UZS
  Popolenie ot UZUMBANK HUMO to VISAUZUM, UZ na 300000.00 UZS, karta ****7936. Dostupno: 347506.12 UZS
  Spisanie, karta ****7936: 20000000.00 UZS, UZUMBANK VISAUZUM to UZCARD, UZ. Dostupno: 25074606.12 UZS

Returns: dict | None
"""
import re
from datetime import datetime
from typing import Optional

from ._shared import categorize


def parse_uzum(text: str) -> Optional[dict]:
    """Parse Uzum Bank SMS. Returns structured dict or None."""
    text = text.strip()

    # Must start with "Spisanie" or "Popolenie"
    text_lower = text.lower()
    if not (text_lower.startswith("spisanie") or text_lower.startswith("popolenie")):
        return None

    tx_type = "credit" if text_lower.startswith("popolenie") else "debit"

    # Card last4: "karta ****7936"
    card_match = re.search(r'karta\s+\*{3,4}(\d{4})', text, re.IGNORECASE)
    card_last4 = card_match.group(1) if card_match else None

    # Amount:
    # Debit:  "karta ****7936: 272900.00 UZS,"
    # Credit: "na 300000.00 UZS, karta"
    amount_match = re.search(
        r'(?:karta\s+\*+\d{4}:\s*|na\s+)([\d\.]+)\s*UZS',
        text, re.IGNORECASE
    )
    if not amount_match:
        return None
    try:
        amount = float(amount_match.group(1))
    except ValueError:
        return None
    if amount <= 0:
        return None

    # Merchant:
    # Debit:  "272900.00 UZS, UZUM TEZKOR. UZ."
    # Credit: "Popolenie ot UZUMBANK HUMO to VISAUZUM, UZ na ..."
    merchant = None
    if tx_type == "debit":
        m = re.search(r'[\d\.]+\s*UZS,\s*(.+?)(?:\.\s*UZ|\.\s*Dostupno|$)', text, re.IGNORECASE)
        if m:
            merchant = m.group(1).strip().rstrip('.')
    else:
        m = re.search(r'Popolenie\s+ot\s+(.+?)\s+na\s+[\d\.]+\s*UZS', text, re.IGNORECASE)
        if m:
            merchant = m.group(1).strip()

    merchant = merchant or "Uzum Bank"

    now = datetime.now()

    return {
        'date':             now.strftime("%Y-%m-%d"),
        'time':             now.strftime("%H:%M:%S"),
        'amount':           amount,
        'currency':         'UZS',
        'category':         categorize(text_lower, merchant),
        'merchant':         merchant,
        'payment_method':   'Uzum Bank',
        'card_last4':       card_last4,
        'transaction_type': tx_type,
        'source':           'UZUM',
        'raw_text':         text,
    }
