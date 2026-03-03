#!/usr/bin/env python3
"""
classifier_simple.py — Pattern-based классификация SMS для PFM (без LLM)

Классы:
- transaction — расход или доход
- transfer — между своими счетами  
- promotional — реклама
- informational — баланс/статус

Usage:
    python3 classifier_simple.py "Сумма: 50000 UZS"
"""

import json
import re
import sys

def classify_sms(text: str) -> dict:
    """Классифицирует SMS по паттернам"""
    
    text_lower = text.lower()
    
    # Promotional — реклама
    promo_patterns = [
        r'акци[яи]', r'кэшбэк', r'скидк', r'предложени', r'бонус',
        r'промокод', r'распродаж', r'выгодн', r'специальн'
    ]
    for pattern in promo_patterns:
        if re.search(pattern, text_lower):
            return {
                "class": "promotional",
                "confidence": 0.9,
                "reason": "Рекламные ключевые слова",
                "amount": None,
                "currency": None
            }
    
    # Transfer — между счетами
    transfer_patterns = [
        r'межд[уы] счет', r'internal transfer', r'card to card',
        r'перевод меж', r'пополнени.*карт', r'с.*счета.*на.*счет'
    ]
    for pattern in transfer_patterns:
        if re.search(pattern, text_lower):
            amount = extract_amount(text)
            return {
                "class": "transfer",
                "confidence": 0.85,
                "reason": "Перевод между счетами",
                "amount": amount,
                "currency": extract_currency(text)
            }
    
    # Informational — баланс, статус (без операций)
    info_patterns = [r'баланс', r'статус', r'остаток']
    has_operation = any(k in text_lower for k in ['сумма', 'оплата', 'покупк', 'сняти', 'пополнени', 'перевод'])
    if any(re.search(p, text_lower) for p in info_patterns) and not has_operation:
        return {
            "class": "informational",
            "confidence": 0.8,
            "reason": "Информационное SMS (баланс/статус)",
            "amount": None,
            "currency": None
        }
    
    # Transaction — расход/доход
    amount = extract_amount(text)
    if amount and any(k in text_lower for k in ['сумма', 'оплата', 'покупк', 'сняти', 'пополнени', 'перевод', 'uzs', 'сум']):
        return {
            "class": "transaction",
            "confidence": 0.85,
            "reason": "Финансовая операция с суммой",
            "amount": amount,
            "currency": extract_currency(text)
        }
    
    # Unknown
    return {
        "class": "unknown",
        "confidence": 0.3,
        "reason": "Не удалось классифицировать",
        "amount": None,
        "currency": None
    }


def extract_amount(text: str) -> float:
    """Извлекает сумму из SMS"""
    # Паттерны: 50000, 50 000, 50.000
    patterns = [
        r'(\d[\d\s\.]*)\s*(?:uzs|сум|usd|долл)',
        r'сумма[:\s]+(\d[\d\s\.]*)',
        r'(\d[\d\s\.]*)\s*тенге'
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            amount_str = match.group(1).replace(' ', '').replace('.', '')
            try:
                return float(amount_str)
            except:
                pass
    return None


def extract_currency(text: str) -> str:
    """Извлекает валюту"""
    text_upper = text.upper()
    if 'UZS' in text_upper or 'СУМ' in text_upper:
        return 'UZS'
    elif 'USD' in text_upper or 'ДОЛЛ' in text_upper:
        return 'USD'
    elif 'EUR' in text_upper:
        return 'EUR'
    elif 'TENGE' in text_upper or 'KZT' in text_upper:
        return 'KZT'
    return None


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 classifier_simple.py <sms_text>")
        sys.exit(1)
    
    sms_text = " ".join(sys.argv[1:])
    result = classify_sms(sms_text)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
