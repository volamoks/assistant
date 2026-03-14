#!/usr/bin/env python3
"""
classifier.py — LLM классификация SMS для PFM

Классы:
- transaction — расход или доход (сумма, покупка, оплата)
- transfer — перевод между своими счетами
- promotional — реклама, акции, предложения
- informational — баланс, статус, без сумм

Usage:
    python3 classifier.py "Сумма: 50000 UZS. Баланс: 100000 UZS. HUMO"
    python3 classifier.py --batch < sms_list.txt
"""

import json
import os
import sys
from pathlib import Path

try:
    import requests
except ImportError:
    print("❌ pip install requests")
    sys.exit(1)

# MiniMax Portal (OAuth) — прямой вызов через Anthropic API
MINIMAX_PORTAL_URL = "https://api.minimax.io/anthropic/v1/messages"
MODEL = "MiniMax-M2.5"
API_KEY = os.environ.get("MINIMAX_API_KEY")

SYSTEM_PROMPT = """Ты классификатор финансовых SMS. Верни ТОЛЬКО JSON без markdown:
{"class": "transaction|transfer|promotional|informational", "confidence": 0.0-1.0, "reason": "почему", "amount": number|null, "currency": "UZS|USD|etc"}

Правила:
- transaction: расход или доход (есть сумма + покупка/оплата/снятие/пополнение)
- transfer: перевод между СВОИМИ счетами (ключевые слова: "между счетами", "internal transfer", "card to card" если свои)
- promotional: реклама, акции, кэшбэк предложения, скидки
- informational: баланс, статус карты, без операций

Примеры:
"Сумма: 50000 UZS. Баланс: 100000 UZS. HUMO" → transaction, amount: 50000
"Перевод между счетами: 100000 UZS" → transfer
"Акция! Кэшбэк 10% в ресторанах" → promotional
"Баланс карты: 250000 UZS" → informational
"""

def classify_sms(text: str, use_cache: bool = True) -> dict:
    """Классифицирует SMS с кэшированием через MiniMax"""
    
    # Кэш
    cache_file = Path(__file__).parent / ".classifier_cache.json"
    cache = {}
    if use_cache and cache_file.exists():
        try:
            cache = json.loads(cache_file.read_text())
            if text in cache:
                return cache[text]
        except Exception:
            pass
    
    # Запрос к MiniMax Portal (Anthropic API format)
    try:
        resp = requests.post(
            MINIMAX_PORTAL_URL,
            headers={
                "Authorization": f"Bearer {API_KEY}",
                "Content-Type": "application/json",
                "anthropic-version": "2023-06-01"
            },
            json={
                "model": MODEL,
                "max_tokens": 200,
                "messages": [
                    {"role": "user", "content": f"{SYSTEM_PROMPT}\n\nSMS: {text}"}
                ],
                "temperature": 0.1
            },
            timeout=30
        )
        result = resp.json()["content"][0]["text"].strip()
        
        # Парсим JSON из результата (убираем markdown если есть)
        result = result.replace("```json", "").replace("```", "").strip()
        start = result.find("{")
        end = result.rfind("}") + 1
        classification = json.loads(result[start:end])
        
        # Кэшируем
        if use_cache:
            cache[text] = classification
            cache_file.write_text(json.dumps(cache, ensure_ascii=False, indent=2))
        
        return classification
        
    except Exception as e:
        return {
            "class": "unknown",
            "confidence": 0,
            "reason": f"Error: {e}",
            "amount": None,
            "currency": None
        }


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 classifier.py <sms_text>")
        print("       python3 classifier.py --batch < sms_list.txt")
        sys.exit(1)
    
    if sys.argv[1] == "--batch":
        # Пакетная обработка
        for line in sys.stdin:
            sms = line.strip()
            if sms:
                result = classify_sms(sms)
                print(f"{sms[:50]}... → {result['class']} ({result['confidence']:.2f})")
    else:
        # Одиночная классификация
        sms_text = " ".join(sys.argv[1:])
        result = classify_sms(sms_text)
        print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
