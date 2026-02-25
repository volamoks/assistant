"""Shared utilities for all parsers."""
from typing import Optional


def categorize(text_lower: str, merchant: Optional[str]) -> str:
    """Keyword-based category detection from text + merchant name."""
    combined = text_lower + " " + (merchant or "").lower()
    rules = [
        (["korzinka", "makro", "havas", "supermarket", "bozor", "grocery",
          "restoran", "cafe", "restaurant", "pizza", "burger", "tezkor", "food"], "FOOD"),
        (["taxi", "yandex", "uber", "metro", "avtobus", "transport", "tolov>m"], "TRANSPORT"),
        (["uzum", "ozon", "wildberries", "shop", "do'kon", "mall", "store", "magazin"], "SHOPPING"),
        (["apteka", "clinic", "hospital", "doktor", "pharmacy", "health"], "HEALTH"),
        (["komunal", "gas", "electric", "suv", "internet", "utility", "kommunal"], "UTILITIES"),
        (["ucell", "beeline", "uzmobile", "mobiuz", "humans", "aloqa", "telecom"], "TELECOM"),
        (["atm", "bankomat", "nalichn"], "ATM"),
        (["transfer", "p2p", "perevod", "o'tkazma", "visauzum to uzcard",
          "humo to visa", "uzcard"], "TRANSFER"),
    ]
    for keywords, cat in rules:
        if any(k in combined for k in keywords):
            return cat
    return "OTHER"
