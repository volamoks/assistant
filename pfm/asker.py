#!/usr/bin/env python3
"""
asker.py — Proactive Telegram questions for low-confidence transactions

Sends inline keyboard messages asking the user to categorize ambiguous transactions.
When user clicks a category button, handle_callback() updates finance.db + Sure PFM.

User confirms category → saved to merchant_patterns → next similar tx skipped LLM.

Usage:
    python3 asker.py           # send questions for all low-confidence (< 0.6)
    python3 asker.py --limit 5 # send max 5 questions
    python3 asker.py --dry-run # print without sending

Cron (daily 09:00 — morning review):
    0 9 * * * python3 /Users/abror_mac_mini/Projects/bot/pfm/asker.py >> /tmp/pfm_asker.log 2>&1

Callback handler (call from bot when receiving callback_data starting with 'pfm_cat:'):
    from asker import handle_callback
    handle_callback(callback_data, callback_query_id)
    # callback_data format: "pfm_cat:{tx_id}:{category_key}"
"""
import os
import sys
import sqlite3
import requests
import argparse
from datetime import datetime
from pathlib import Path

BASE       = Path(__file__).parent
DOCKER_DIR = BASE.parent / "openclaw-docker"
SKILLS_DIR = DOCKER_DIR / "skills"
sys.path.insert(0, str(SKILLS_DIR))
sys.path.insert(0, str(BASE))

from sink import SURE_URL, _sure_headers, CATEGORY_ID_MAP
from enricher import _save_pattern

DB = BASE / "finance.db"

def _env(key: str, default: str = "") -> str:
    val = os.environ.get(key, "")
    if val:
        return val
    for p in [DOCKER_DIR / ".env", BASE.parent / ".env"]:
        try:
            for line in p.read_text().splitlines():
                if line.strip().startswith(f"{key}="):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
        except Exception:
            pass
    return default

BOT_TOKEN = _env("TELEGRAM_BOT_TOKEN")
CHAT_ID   = _env("TELEGRAM_CHAT_ID")

# Category buttons shown to user — (emoji + label, internal key)
CATEGORIES = [
    ("🍔 Еда",       "FOOD"),
    ("🚗 Транспорт", "TRANSPORT"),
    ("🛍 Покупки",   "SHOPPING"),
    ("💊 Здоровье",  "HEALTH"),
    ("⚡ ЖКУ",       "UTILITIES"),
    ("📱 Связь",     "TELECOM"),
    ("🏧 ATM",       "ATM"),
    ("💰 Доход",     "INCOME"),
    ("↔️ Перевод",   "TRANSFER"),
    ("❓ Другое",    "OTHER"),
]


def _tg_send(text: str, buttons: list[list[dict]]) -> int | None:
    """Send Telegram message, return message_id or None."""
    if not BOT_TOKEN or not CHAT_ID:
        print("  ⚠️  TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not set")
        return None
    payload = {
        "chat_id":    CHAT_ID,
        "text":       text,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True,
        "reply_markup": {"inline_keyboard": buttons},
    }
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            json=payload, timeout=10,
        )
        if r.ok:
            return r.json().get("result", {}).get("message_id")
        print(f"  ⚠️  Telegram error: {r.text[:200]}")
    except Exception as e:
        print(f"  ⚠️  Telegram send failed: {e}")
    return None


def _build_buttons(tx_id: int) -> list[list[dict]]:
    """Build 2-column inline keyboard for category selection."""
    rows = []
    row  = []
    for label, key in CATEGORIES:
        cb = f"pfm_cat:{tx_id}:{key}"
        row.append({"text": label, "callback_data": cb[:64]})
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([{"text": "⏩ Пропустить", "callback_data": f"pfm_cat:{tx_id}:SKIP"}])
    return rows


def _format_date(date_str: str) -> str:
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        return dt.strftime("%-d %b %Y")
    except Exception:
        return date_str


def ask_transaction(tx: dict, dry_run: bool = False) -> bool:
    """Send a Telegram question for one transaction. Returns True on success."""
    source   = tx.get("source", "")
    last4    = tx.get("card_last4", "")
    account  = f"{source} *{last4}" if last4 else source
    amount   = tx.get("amount", 0)
    currency = tx.get("currency", "UZS")
    merchant = tx.get("merchant_clean") or tx.get("merchant") or "Неизвестно"
    date_fmt = _format_date(tx.get("date", ""))
    category = tx.get("enriched_category", "OTHER")
    confidence = float(tx.get("llm_confidence") or 0)

    text = (
        f"❓ *Что это за платёж?*\n\n"
        f"🏦 {account} | {amount:,.0f} {currency} | {date_fmt}\n"
        f"🏪 {merchant}\n"
        f"🤖 Предположение: `{category}` ({confidence:.0%})"
    )

    if dry_run:
        print(f"  [DRY] Would ask about tx_id={tx['id']}: {merchant} {amount:,.0f} {currency}")
        return True

    buttons  = _build_buttons(tx["id"])
    msg_id   = _tg_send(text, buttons)
    if msg_id:
        conn = sqlite3.connect(DB)
        conn.execute(
            "INSERT OR REPLACE INTO pending_questions (tx_id, sent_at, message_id) VALUES (?, ?, ?)",
            (tx["id"], datetime.now().isoformat(), msg_id)
        )
        conn.commit()
        conn.close()
        print(f"  📤 Sent question for tx_id={tx['id']}: {merchant[:30]}")
        return True
    return False


def run(limit: int = 10, dry_run: bool = False, min_confidence: float = 0.6):
    """Send questions for all low-confidence enriched transactions not yet asked."""
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    cur  = conn.cursor()

    cur.execute("""
        SELECT t.id, t.date, t.amount, t.currency, t.source, t.card_last4,
               t.merchant, t.merchant_clean, t.enriched_category, t.llm_confidence
        FROM transactions t
        LEFT JOIN pending_questions q ON q.tx_id = t.id
        WHERE t.is_enriched = 1
          AND t.type IN ('expense', 'income')
          AND t.llm_confidence < ?
          AND t.llm_confidence > 0
          AND q.tx_id IS NULL
        ORDER BY t.date DESC
        LIMIT ?
    """, (min_confidence, limit))
    rows = cur.fetchall()
    conn.close()

    if not rows:
        print("No low-confidence transactions to ask about ✅")
        return

    print(f"Sending {len(rows)} question(s) to Telegram (confidence < {min_confidence:.0%})")
    sent = 0
    for row in rows:
        if ask_transaction(dict(row), dry_run):
            sent += 1

    print(f"\n{'[DRY] ' if dry_run else ''}Sent {sent}/{len(rows)} question(s)")


def handle_callback(callback_data: str, callback_query_id: str = "") -> bool:
    """
    Handle pfm_cat callback from Telegram inline button press.
    callback_data format: "pfm_cat:{tx_id}:{category_key}"

    Returns True on success. Call from bot's callback handler.
    """
    if not callback_data.startswith("pfm_cat:"):
        return False

    parts = callback_data.split(":", 2)
    if len(parts) != 3:
        return False

    try:
        tx_id    = int(parts[1])
        category = parts[2].upper()
    except (ValueError, IndexError):
        return False

    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    cur  = conn.cursor()

    cur.execute("SELECT * FROM transactions WHERE id = ?", (tx_id,))
    row = cur.fetchone()
    if not row:
        conn.close()
        return False

    if category == "SKIP":
        # Mark as enriched with high confidence to stop re-asking
        cur.execute("""
            UPDATE transactions SET is_enriched = 1, llm_confidence = 0.5
            WHERE id = ?
        """, (tx_id,))
        cur.execute("DELETE FROM pending_questions WHERE tx_id = ?", (tx_id,))
        conn.commit()
        conn.close()
        _answer_callback(callback_query_id, "⏩ Пропущено")
        return True

    # User confirmed category — update DB
    merchant = dict(row).get("merchant_clean") or dict(row).get("merchant") or ""
    cur.execute("""
        UPDATE transactions SET
            enriched_category = ?,
            is_enriched = 1,
            llm_confidence = 1.0
        WHERE id = ?
    """, (category, tx_id))
    cur.execute("DELETE FROM pending_questions WHERE tx_id = ?", (tx_id,))

    # Save to merchant_patterns (LEARN!)
    _save_pattern(cur, merchant, category, "user", 1.0)
    conn.commit()

    # Update Sure
    imported_id = f"{dict(row)['source']}-{dict(row)['date']}-{dict(row)['amount']}-{dict(row)['card_last4'] or 'X'}"
    _update_sure(imported_id, category, merchant)

    conn.close()

    label = next((lbl for lbl, key in CATEGORIES if key == category), category)
    _answer_callback(callback_query_id, f"✅ {label}")
    print(f"  ✅ tx_id={tx_id} category set to {category} by user → pattern saved")
    return True


def _update_sure(imported_id: str, category: str, merchant: str) -> bool:
    """Update Sure transaction category and name."""
    category_id = CATEGORY_ID_MAP.get(category)
    try:
        r = requests.get(f"{SURE_URL}/api/v1/transactions",
                         headers=_sure_headers(),
                         params={"search": imported_id, "per_page": 5},
                         timeout=10)
        txs = [t for t in r.json().get("transactions", [])
               if imported_id in (t.get("notes") or "")]
        if not txs:
            return False
        tx_id   = txs[0]["id"]
        payload = {"transaction": {"name": merchant}}
        if category_id:
            payload["transaction"]["category_id"] = category_id
        r2 = requests.patch(f"{SURE_URL}/api/v1/transactions/{tx_id}",
                            headers=_sure_headers(), json=payload, timeout=10)
        return r2.ok
    except Exception:
        return False


def _answer_callback(callback_query_id: str, text: str):
    """Answer Telegram callback query (shows toast notification)."""
    if not BOT_TOKEN or not callback_query_id:
        return
    try:
        requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery",
            json={"callback_query_id": callback_query_id, "text": text},
            timeout=5,
        )
    except Exception:
        pass


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Send category questions to Telegram")
    parser.add_argument("--limit",      type=int,   default=10,   help="Max questions to send")
    parser.add_argument("--dry-run",    action="store_true",      help="Print without sending")
    parser.add_argument("--confidence", type=float, default=0.6,  help="Max confidence threshold (default 0.6)")
    parser.add_argument("--callback",   type=str,   default=None, help="Handle callback data (for testing)")
    args = parser.parse_args()

    if args.callback:
        ok = handle_callback(args.callback)
        print("Handled:", ok)
    else:
        run(limit=args.limit, dry_run=args.dry_run, min_confidence=args.confidence)
