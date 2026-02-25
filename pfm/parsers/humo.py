"""
Parser: HUMO Card Telegram bot notifications.

Supported format:
  💸 Оплата ➖ 1.700,00 UZS 📍 TRANSPORT TOLOV>M U 💳 HUMOCARD *9396 🕓 18:34 23.02.2026
  💰 Пополнение ➕ 500.000,00 UZS 💳 HUMOCARD *9396 🕓 09:00 23.02.2026

Returns: dict | None
"""
import re
from datetime import datetime
from typing import Optional

CATEGORY_KEYWORDS = {
    'TRANSPORT': ['transport', 'tolov>m', 'metro', 'avtobeket', 'taxi', 'yandex'],
    'FOOD':      ['food', 'korzinka', 'magnit', 'cafe', 'restaurant', 'restoran', 'pizza'],
    'HEALTH':    ['clinic', 'apteka', 'pharmacy', 'hospital', 'doktor'],
    'TELECOM':   ['ucell', 'beeline', 'uzmobile', 'mobiuz', 'humans'],
    'UTILITIES': ['gas', 'electric', 'water', 'kommunal', 'internet'],
    'SHOPPING':  ['shop', 'market', 'mall', 'store', 'magazin'],
    'TRANSFER':  ['transfer', 'p2p', 'perevod'],
    'ATM':       ['atm', 'bankomat', 'nalichn'],
}


def _detect_category(merchant: str) -> str:
    text = merchant.lower()
    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(kw in text for kw in keywords):
            return category
    return 'OTHER'


def _parse_amount(raw: str) -> float:
    """Convert '1.700,00' or '500.000,00' to float."""
    return float(raw.replace('.', '').replace(',', '.'))


def parse_humo(text: str) -> Optional[dict]:
    """
    Parse HUMO Card notification text.
    Returns structured dict or None if no match.
    """
    pattern = re.compile(
        r'(?P<type_text>[^\➖➕]+?)\s*'
        r'(?P<direction>[➖➕])\s*'
        r'(?P<amount>[\d.,]+)\s+'
        r'(?P<currency>[A-Z]{3})'
        r'(?:\s+📍\s*(?P<merchant>[^💳🕓\n]+?))?'
        r'(?:\s+💳\s*(?P<card>[^🕓\n]+?))?'
        r'(?:\s+🕓\s*(?P<time>\d{2}:\d{2})\s+(?P<date>\d{2}\.\d{2}\.\d{4}))?'
        r'\s*$',
        re.UNICODE | re.DOTALL,
    )
    m = pattern.search(text.strip())
    if not m:
        return None

    direction = m.group('direction')
    merchant  = (m.group('merchant') or '').strip()
    card      = (m.group('card') or '').strip()
    raw_time  = m.group('time') or ''
    raw_date  = m.group('date') or ''

    card_last4_match = re.search(r'\*(\d{4})', card)
    card_last4 = card_last4_match.group(1) if card_last4_match else None

    if raw_date:
        try:
            date_str = datetime.strptime(raw_date, '%d.%m.%Y').strftime('%Y-%m-%d')
        except ValueError:
            date_str = datetime.now().strftime('%Y-%m-%d')
    else:
        date_str = datetime.now().strftime('%Y-%m-%d')

    return {
        'date':             date_str,
        'time':             raw_time or datetime.now().strftime('%H:%M'),
        'amount':           _parse_amount(m.group('amount')),
        'currency':         m.group('currency'),
        'category':         _detect_category(merchant),
        'merchant':         merchant,
        'payment_method':   card,
        'card_last4':       card_last4,
        'transaction_type': 'debit' if direction == '➖' else 'credit',
        'source':           'HUMO',
        'raw_text':         text.strip(),
    }
