#!/usr/bin/env python3
"""
parsers/nbu.py — NBU (National Bank of Uzbekistan) SMS parser

SMS formats:
  Pokupka, My taxi L 27.12.25 10:10, karta 514379******9445. summa: 17 800.00 UZS, balans: 36.71 USD
  Reversal, My taxi L 27.12.25 09:42, karta 514379******9445. summa: 1 000.00 UZS, balans: 38.22 USD
  Nedostatochno sredstv, My taxi L 16.01.26 19:00, karta 514379******9445. summa: 31 500.00 UZS, balans: 0.00 USD

Types:
  Pokupka           → debit (expense)
  Reversal          → credit (refund)
  Popolnenie        → credit (top-up/income)
  Nedostatochno... → SKIP (failed transaction, no money moved)
"""
import re
from datetime import datetime

# SMS type → transaction_type mapping
_TYPE_MAP = {
    "pokupka":          "debit",
    "reversal":         "credit",
    "popolnenie":       "credit",
    "zachislenie":      "credit",
    "vozvrat":          "credit",
}

_SKIP_TYPES = {"nedostatochno sredstv", "nedostatochno", "oshibka", "otkaz"}


def parse(text: str) -> dict | None:
    """
    Parse an NBU bank SMS into a unified ParsedTx dict.
    Returns None if not an NBU financial SMS or if transaction failed/skipped.
    """
    if not text:
        return None

    text_stripped = text.strip()

    # Identify transaction type (first word before comma)
    first_part = text_stripped.split(",")[0].strip().lower()

    # Skip failed transactions
    for skip in _SKIP_TYPES:
        if first_part.startswith(skip):
            return None

    transaction_type = _TYPE_MAP.get(first_part)
    if not transaction_type:
        return None

    # Extract merchant name (between first comma and date pattern)
    # Pattern: "Pokupka, {merchant} {DD.MM.YY HH:MM}, karta ..."
    merchant_match = re.search(
        r',\s*(.+?)\s+(\d{2}\.\d{2}\.\d{2})\s+(\d{2}:\d{2})\s*,\s*karta',
        text_stripped, re.IGNORECASE
    )
    merchant = merchant_match.group(1).strip() if merchant_match else ""

    # Extract date and time
    date_str, time_str = None, None
    if merchant_match:
        raw_date = merchant_match.group(2)  # DD.MM.YY
        time_str = merchant_match.group(3)  # HH:MM
        try:
            dt = datetime.strptime(raw_date, "%d.%m.%y")
            date_str = dt.strftime("%Y-%m-%d")
        except ValueError:
            pass

    if not date_str:
        return None

    # Extract card last 4 digits: "karta 514379******9445"
    card_match = re.search(r'karta\s+\d+\*+(\d{4})', text_stripped, re.IGNORECASE)
    card_last4 = card_match.group(1) if card_match else None

    # Extract amount and currency from "summa: 17 800.00 UZS"
    summa_match = re.search(
        r'summa:\s*([\d\s]+\.?\d*)\s*([A-Z]{3})',
        text_stripped, re.IGNORECASE
    )
    if not summa_match:
        return None

    amount_raw = summa_match.group(1).replace(" ", "")
    currency   = summa_match.group(2).upper()

    try:
        amount = float(amount_raw)
    except ValueError:
        return None

    if amount <= 0:
        return None

    return {
        "source":           "NBU",
        "card_last4":       card_last4,
        "date":             date_str,
        "time":             time_str,
        "amount":           amount,
        "currency":         currency,
        "merchant":         merchant,
        "transaction_type": transaction_type,
        "raw_text":         text_stripped,
    }


def is_nbu_sms(text: str) -> bool:
    """Quick check: does this look like an NBU SMS?"""
    if not text:
        return False
    t = text.lower().strip()
    return bool(
        re.match(r'(pokupka|reversal|popolnenie|zachislenie|vozvrat|nedostatochno)', t) and
        'karta' in t and 'summa' in t
    )


if __name__ == "__main__":
    import json, sys
    tests = [
        "Pokupka, My taxi L 27.12.25 10:10, karta 514379******9445. summa: 17 800.00 UZS, balans: 36.71 USD",
        "Reversal, My taxi L 27.12.25 09:42, karta 514379******9445. summa: 1 000.00 UZS, balans: 38.22 USD",
        "Nedostatochno sredstv, My taxi L 16.01.26 19:00, karta 514379******9445. summa: 31 500.00 UZS, balans: 0.00 USD",
    ]
    for t in tests:
        result = parse(t)
        print(f"{'✅' if result else '⏭️ (skipped)'} {t[:60]}")
        if result:
            print(f"   → {result['transaction_type']} {result['amount']:,.0f} {result['currency']} [{result['merchant']}] card={result['card_last4']}")
