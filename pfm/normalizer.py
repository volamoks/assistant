#!/usr/bin/env python3
"""
normalizer.py — determine transaction type WITHOUT LLM, at parse time

Rules (no network call, instant):
  debit  → expense
  credit + own card digits in text/merchant → pending_match (30min timeout)
  credit + external → income

pending_match is resolved by transfer_matcher.py (runs every 15 min):
  - If debit pair found → Sure Transfer
  - If 30 min pass, no pair → promoted to income

Usage:
    from normalizer import normalize
    normalized = normalize(parsed_tx)
"""
from datetime import datetime, timedelta

OWN_CARD_LAST4 = {"9396", "1066", "5175", "6079", "6807", "4521", "7936", "7834", "8515", "9445"}

PENDING_WINDOW_MINUTES = 30


def normalize(parsed: dict) -> dict:
    """
    Determine transaction type from parsed SMS data.
    Returns a copy of parsed with 'type' and 'pending_until' added.

    Args:
        parsed: dict from any bank parser with at least:
                transaction_type ('debit'|'credit'), raw_text, merchant, card_last4

    Returns:
        dict with added fields:
          type: 'expense' | 'income' | 'pending_match'
          pending_until: ISO datetime string if pending_match, else None
    """
    tx_type = (parsed.get("transaction_type") or "debit").lower()

    if tx_type == "debit":
        return {**parsed, "type": "expense", "pending_until": None}

    # Credit: check if own card digits appear in text → potential transfer
    search_text = (
        (parsed.get("raw_text") or "") + " " +
        (parsed.get("merchant") or "") + " " +
        (parsed.get("payment_method") or "")
    ).lower()

    is_own_card_credit = any(last4 in search_text for last4 in OWN_CARD_LAST4)

    if is_own_card_credit:
        pending_until = (datetime.now() + timedelta(minutes=PENDING_WINDOW_MINUTES)).isoformat()
        return {**parsed, "type": "pending_match", "pending_until": pending_until}

    return {**parsed, "type": "income", "pending_until": None}
