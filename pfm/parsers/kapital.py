"""
Parser: Kapitalbank SMS notifications.

Supported formats:
  1. Snyatiye/Popolneniye (new format):
     "Snyatiye, 24.02.26 v 15:27. Karta (*6079). Summa: 1000.00 UZS. ... Dostupno: ..."
     "Popolneniye, 24.02.26 v 15:36. Karta (*6079). Summa: 1000.00 UZS. ..."

  2. Karta action with sign+amount (classic format):
     "Karta *6079. Xarid/Pokupka "YANDEX.GO>YUNUSOBOD", -39000.00, UZS, "24-02-2026 09:46". Dostupno: ..."
     "Karta *6079. vznos "HUMO KB 2 VISA MC UZ", +2026.00, UZS, "23-02-2026 21:46". Dostupno: ..."

  3. Schet popolnen (simple top-up):
     "Schet po karte *6079 popolnen na summu 55756.85 UZS. 23-FEB-2026 00:00"

Returns: dict | None
"""
import re
from datetime import datetime
from typing import Optional

from ._shared import categorize

MONTHS_RU = {
    "JAN": "01", "FEB": "02", "MAR": "03", "APR": "04",
    "MAY": "05", "JUN": "06", "JUL": "07", "AUG": "08",
    "SEP": "09", "OCT": "10", "NOV": "11", "DEC": "12",
}

DEBIT_ACTIONS  = ["xarid", "pokupka", "snyatiye", "chiqim", "payment", "spisanie"]
CREDIT_ACTIONS = ["vznos", "popolneniye", "popolenie", "popolnen", "kirim", "credit", "zachislenie"]


def _parse_date_ddmmyyyy(s: str) -> Optional[str]:
    """Parse 'DD-MM-YYYY' or 'DD.MM.YYYY' → 'YYYY-MM-DD'"""
    m = re.match(r'(\d{2})[-.](\d{2})[-.](\d{4})', s.strip())
    if m:
        return f"{m.group(3)}-{m.group(2)}-{m.group(1)}"
    return None


def _parse_date_ddmonyyyy(s: str) -> Optional[str]:
    """Parse '23-FEB-2026' → '2026-02-23'"""
    m = re.match(r'(\d{2})-([A-Z]{3})-(\d{4})', s.strip(), re.IGNORECASE)
    if m:
        mon = MONTHS_RU.get(m.group(2).upper())
        if mon:
            return f"{m.group(3)}-{mon}-{m.group(1)}"
    return None


def _tx_type_from_action(action: str) -> str:
    a = action.lower()
    if any(k in a for k in CREDIT_ACTIONS):
        return "credit"
    return "debit"


def parse_kapital(text: str) -> Optional[dict]:
    """Parse any Kapitalbank SMS format. Returns dict or None."""
    text = text.strip()
    now = datetime.now()

    # ── Format 1: "Snyatiye/Popolneniye, YY.MM.DD v HH:MM. Karta (*XXXX). Summa: X UZS." ──
    if re.match(r'(Snyatiye|Popolneniye)', text, re.IGNORECASE):
        tx_type = "credit" if text.lower().startswith("popolneniye") else "debit"

        dt_m = re.search(r'(\d{2})\.(\d{2})\.(\d{2})\s+v\s+(\d{2}:\d{2})', text)
        if dt_m:
            yy, mm, dd, hhmm = dt_m.groups()
            date_str, time_str = f"20{yy}-{mm}-{dd}", f"{hhmm}:00"
        else:
            date_str = now.strftime("%Y-%m-%d")
            time_str = now.strftime("%H:%M:%S")

        card_m  = re.search(r'Karta\s*\(\*(\d{4})\)', text, re.IGNORECASE)
        card_l4 = card_m.group(1) if card_m else None

        amt_m = re.search(r'Summa:\s*([\d\.]+)\s*UZS', text, re.IGNORECASE)
        if not amt_m:
            return None
        amount = float(amt_m.group(1))

        merch_m = re.search(r'Summa:\s*[\d\.]+\s*UZS\.\s*(.+?)(?:\.|Dostupno)', text, re.IGNORECASE)
        merchant = (merch_m.group(1).strip() if merch_m else None) or "Kapitalbank"

        return _build(date_str, time_str, amount, card_l4, tx_type, merchant, text)

    # ── Format 2: "Karta *XXXX. ACTION "MERCHANT", ±AMOUNT, UZS, "DD-MM-YYYY HH:MM"" ──
    f2 = re.match(
        r'Karta\s+\*(\d{4})\.\s*'                          # Karta *6079.
        r'([^"]+?)\s*'                                      # action (Xarid/Pokupka, vznos...)
        r'"([^"]+)",\s*'                                    # "MERCHANT"
        r'([+-][\d\.]+),\s*UZS,\s*'                        # ±AMOUNT, UZS,
        r'"(\d{2}-\d{2}-\d{4})\s+(\d{2}:\d{2})"',         # "DD-MM-YYYY HH:MM"
        text, re.IGNORECASE
    )
    if f2:
        card_l4, action, merchant, raw_amt, raw_date, raw_time = f2.groups()
        amount   = abs(float(raw_amt))
        tx_type  = "credit" if raw_amt.startswith("+") else "debit"
        date_str = _parse_date_ddmmyyyy(raw_date) or now.strftime("%Y-%m-%d")
        return _build(date_str, f"{raw_time}:00", amount, card_l4, tx_type, merchant, text)

    # ── Format 3: "Schet po karte *XXXX popolnen na summu AMOUNT UZS. DD-MON-YYYY HH:MM" ──
    f3 = re.match(
        r'Schet\s+po\s+karte\s+\*(\d{4})\s+popolnen\s+na\s+summu\s+'
        r'([\d\.]+)\s+UZS\.\s*'
        r'(\d{2}-[A-Z]{3}-\d{4})\s+(\d{2}:\d{2})',
        text, re.IGNORECASE
    )
    if f3:
        card_l4, raw_amt, raw_date, raw_time = f3.groups()
        amount   = float(raw_amt)
        date_str = _parse_date_ddmonyyyy(raw_date) or now.strftime("%Y-%m-%d")
        return _build(date_str, f"{raw_time}:00", amount, card_l4, "credit", "Kapitalbank", text)

    return None


def _build(date_str, time_str, amount, card_last4, tx_type, merchant, raw_text) -> dict:
    return {
        'date':             date_str,
        'time':             time_str,
        'amount':           amount,
        'currency':         'UZS',
        'category':         categorize(raw_text.lower(), merchant),
        'merchant':         merchant,
        'payment_method':   'Kapitalbank VISA/MC',
        'card_last4':       card_last4,
        'transaction_type': tx_type,
        'source':           'KAPITAL',
        'raw_text':         raw_text,
    }
