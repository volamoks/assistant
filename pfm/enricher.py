#!/usr/bin/env python3
"""
enricher.py — ночной LLM-обогатитель транзакций

Берёт необогащённые транзакции из finance.db (is_enriched=0),
отправляет батчами в LLM, получает чистое название мерчанта + категорию,
обновляет finance.db И Sure PFM.

Usage:
    python3 enricher.py           # обогатить всё необогащённое
    python3 enricher.py --limit 50  # обогатить первые 50
    python3 enricher.py --dry-run   # показать без сохранения

Cron (ежедневно в 02:00):
    0 2 * * * python3 /Users/abror_mac_mini/Projects/bot/pfm/enricher.py >> /tmp/pfm_enricher.log 2>&1
"""
import sys, os, json, sqlite3, requests, argparse, time
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))
from sink import SURE_URL, _sure_headers, CATEGORY_ID_MAP, _transaction_exists

DB = Path(__file__).parent / "finance.db"

def _read_env(key: str) -> str:
    val = os.environ.get(key, "")
    if val:
        return val
    for p in [
        Path(__file__).parent.parent / "openclaw-docker" / ".env",
        Path(__file__).parent.parent / ".env",
    ]:
        try:
            for line in p.read_text().splitlines():
                if line.strip().startswith(f"{key}="):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
        except Exception:
            pass
    return ""

LITELLM_URL = "http://localhost:18788/v1/chat/completions"
LITELLM_KEY = _read_env("LITELLM_MASTER_KEY")
MODEL       = "claw-free-fast"   # fast + free, with fallbacks

ENRICH_PROMPT = """You are a financial transaction enricher. Given a raw bank SMS merchant string and transaction details, return ONLY a JSON object:

{
  "merchant": "Clean merchant name (e.g. 'Korzinka', 'Yandex Go', 'Payme')",
  "category": "one of: TRANSPORT|FOOD|HEALTH|TELECOM|UTILITIES|SHOPPING|ATM|INCOME|OTHER",
  "confidence": 0.0-1.0
}

Rules:
- TRANSPORT: taxi, metro, bus, uber, yandex.go, parking
- FOOD: restaurants, cafes, fast food, delivery, groceries
- HEALTH: pharmacy, doctor, clinic, hospital
- TELECOM: mobile top-up, internet, ucell, beeline, mobiuz, humans
- UTILITIES: electricity, gas, water, komunal
- SHOPPING: stores, markets, online shops, amazon, wildberries
- ATM: cash withdrawal, bankomat
- INCOME: salary, refund, cashback, incoming transfer
- OTHER: everything else

Return ONLY the JSON, no explanation."""


def call_llm_batch(items: list[dict]) -> list[dict]:
    """Send batch of {id, merchant, amount, currency, raw_text} → enriched list."""
    batch_text = "\n".join(
        f"{i+1}. merchant='{it['merchant']}' raw='{it['raw_text'][:60]}'"
        for i, it in enumerate(items)
    )
    prompt = f"{ENRICH_PROMPT}\n\nEnrich these {len(items)} transactions (return JSON array):\n{batch_text}"

    try:
        resp = requests.post(
            LITELLM_URL,
            headers={"Authorization": f"Bearer {LITELLM_KEY}"},
            json={"model": MODEL, "max_tokens": 800, "temperature": 0.1,
                  "messages": [{"role": "user", "content": prompt}]},
            timeout=30,
        )
        content = resp.json()["choices"][0]["message"]["content"].strip()
        content = content.replace("```json", "").replace("```", "").strip()
        start = content.find("[")
        end   = content.rfind("]") + 1
        return json.loads(content[start:end])
    except Exception as e:
        print(f"  ⚠️  LLM batch error: {e}")
        return []


def update_sure_category(imported_id: str, category_key: str, merchant: str) -> bool:
    """Find Sure transaction by imported_id and update its category + name."""
    category_id = CATEGORY_ID_MAP.get(category_key.upper())
    if not category_id and category_key.upper() != "OTHER":
        return False

    headers = _sure_headers()
    # Find transaction
    try:
        r = requests.get(f"{SURE_URL}/api/v1/transactions",
                         headers=headers,
                         params={"search": imported_id, "per_page": 5},
                         timeout=10)
        txs = [t for t in r.json().get("transactions", [])
               if imported_id in (t.get("notes") or "")]
        if not txs:
            return False

        tx_id   = txs[0]["id"]
        payload: dict = {"transaction": {"name": merchant}}
        if category_id:
            payload["transaction"]["category_id"] = category_id

        r2 = requests.patch(f"{SURE_URL}/api/v1/transactions/{tx_id}",
                            headers=headers, json=payload, timeout=10)
        return r2.ok
    except Exception:
        return False


def _check_patterns(cur: sqlite3.Cursor, merchant: str) -> dict | None:
    """Check merchant_patterns table before calling LLM — returns category/confidence or None."""
    if not merchant:
        return None
    merchant_lower = merchant.lower()
    try:
        cur.execute("""
            SELECT category, confidence FROM merchant_patterns
            WHERE lower(?) LIKE '%' || lower(merchant_keyword) || '%'
               OR lower(merchant_keyword) LIKE '%' || lower(?) || '%'
            ORDER BY use_count DESC LIMIT 1
        """, (merchant_lower, merchant_lower))
        row = cur.fetchone()
        if row:
            cur.execute("UPDATE merchant_patterns SET use_count = use_count + 1 WHERE lower(merchant_keyword) = lower(?)", (row[0],))
            return {"category": row["category"], "confidence": row["confidence"]}
    except Exception:
        pass
    return None


def _save_pattern(cur: sqlite3.Cursor, merchant: str, category: str,
                  confirmed_by: str = "llm", confidence: float = 0.85):
    """Save or update a merchant pattern."""
    if not merchant or not category or category == "OTHER":
        return
    try:
        cur.execute("""
            INSERT INTO merchant_patterns (merchant_keyword, category, confirmed_by, confidence)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(merchant_keyword) DO UPDATE SET
                use_count  = use_count + 1,
                confidence = MAX(confidence, excluded.confidence)
        """, (merchant[:60], category, confirmed_by, confidence))
    except Exception:
        pass


def run(limit: int = 500, dry_run: bool = False, batch_size: int = 10):
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    cur  = conn.cursor()

    cur.execute("""
        SELECT id, date, amount, currency, merchant, source, card_last4,
               sms_text, category, type
        FROM transactions
        WHERE is_enriched = 0
          AND type IN ('expense', 'income')
          AND (sms_text IS NOT NULL AND sms_text != '' OR merchant != '')
        ORDER BY date DESC
        LIMIT ?
    """, (limit,))
    rows = cur.fetchall()
    print(f"Found {len(rows)} unenriched transactions")

    if not rows:
        print("Nothing to enrich ✅")
        conn.close()
        return

    enriched_count = 0
    pattern_hits   = 0
    low_confidence = []  # for proactive asker

    for i in range(0, len(rows), batch_size):
        batch_rows = rows[i:i + batch_size]

        # Split: pattern hits vs LLM needed
        pattern_results = {}
        llm_items = []
        llm_indices = []

        for j, row in enumerate(batch_rows):
            hit = _check_patterns(cur, row["merchant"] or "")
            if hit and hit["confidence"] >= 0.75:
                pattern_results[j] = hit
            else:
                llm_items.append({
                    "id":       row["id"],
                    "merchant": row["merchant"] or "",
                    "raw_text": row["sms_text"] or "",
                    "amount":   row["amount"],
                    "currency": row["currency"],
                })
                llm_indices.append(j)

        # LLM batch for unknowns
        llm_results = {}
        if llm_items:
            batch_output = call_llm_batch(llm_items)
            for k, idx in enumerate(llm_indices):
                if k < len(batch_output):
                    llm_results[idx] = batch_output[k]

        # Process results
        for j, row in enumerate(batch_rows):
            imported_id = f"{row['source']}-{row['date']}-{row['amount']}-{row['card_last4'] or 'X'}"

            if j in pattern_results:
                result = pattern_results[j]
                new_merchant = row["merchant"] or ""
                new_category = result["category"]
                confidence   = result["confidence"]
                source_label = "pattern"
            elif j in llm_results and isinstance(llm_results[j], dict):
                result = llm_results[j]
                new_merchant = result.get("merchant") or row["merchant"] or ""
                new_category = (result.get("category") or "OTHER").upper()
                confidence   = float(result.get("confidence") or 0)
                source_label = "llm"
            else:
                continue

            if dry_run:
                print(f"  [DRY/{source_label}] {row['date']} {row['amount']:,.0f} {row['currency']} "
                      f"'{row['merchant']}' → '{new_merchant}' [{new_category}] ({confidence:.2f})")
                continue

            # Update finance.db
            cur.execute("""
                UPDATE transactions SET
                    is_enriched = 1,
                    enriched_at = ?,
                    enriched_category = ?,
                    merchant_clean = ?,
                    llm_confidence = ?
                WHERE id = ?
            """, (datetime.now().isoformat(), new_category, new_merchant, confidence, row["id"]))

            # Save LLM result as pattern (high confidence only)
            if source_label == "llm" and confidence >= 0.8:
                _save_pattern(cur, new_merchant, new_category, "llm", confidence)

            # Update Sure
            sure_ok = update_sure_category(imported_id, new_category, new_merchant)
            status  = "✅" if sure_ok else "💾"
            print(f"  {status} [{source_label}] {row['date']} {row['amount']:,.0f} {row['currency']} "
                  f"'{row['merchant']}' → '{new_merchant}' [{new_category}]")
            enriched_count += 1
            if source_label == "pattern":
                pattern_hits += 1

            # Track low-confidence for proactive asker
            if confidence < 0.6:
                low_confidence.append({"id": row["id"], "merchant": new_merchant,
                                       "amount": row["amount"], "currency": row["currency"],
                                       "date": row["date"], "source": row["source"],
                                       "card_last4": row["card_last4"]})

        conn.commit()
        time.sleep(0.5)  # rate limiting

    # Archive raw SMS text for enriched transactions (> 1 day old)
    if not dry_run:
        cur.execute("""
            UPDATE transactions SET sms_text = NULL
            WHERE is_enriched = 1
              AND enriched_at < datetime('now', '-1 day')
              AND sms_text IS NOT NULL
        """)
        conn.commit()

    conn.close()
    if not dry_run:
        print(f"\nDone: {enriched_count}/{len(rows)} enriched "
              f"({pattern_hits} from patterns, {enriched_count - pattern_hits} via LLM) ✅")
        if low_confidence:
            print(f"⚠️  {len(low_confidence)} low-confidence txns need user input → run asker.py")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit",   type=int, default=500)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--batch",   type=int, default=10)
    args = parser.parse_args()
    run(limit=args.limit, dry_run=args.dry_run, batch_size=args.batch)
