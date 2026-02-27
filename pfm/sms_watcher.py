"""
sms_watcher.py — Watches macOS chat.db for Kapitalbank & Uzum SMS → Actual Budget

Requires Full Disk Access for Terminal (System Settings → Privacy → Full Disk Access).

Usage:
    python3 sms_watcher.py               # live mode (polls every 10s)
    python3 sms_watcher.py --once        # run once and exit
    python3 sms_watcher.py --dry-run     # preview only, no writes
    python3 sms_watcher.py --history     # process all historical SMS
"""
import argparse
import json
import shutil
import sqlite3
import time
from datetime import datetime
from pathlib import Path

CHAT_DB  = Path.home() / "Library/Messages/chat.db"
CHAT_TMP = Path("/tmp/chat_sms_copy.db")

# copy_chat_db.sh (run via cron or from Terminal) keeps CHAT_TMP fresh.
# If the copy is missing or stale (>2 min old), we try to copy ourselves
# (requires Full Disk Access for whichever process runs us).
COPY_MAX_AGE_SECS = 120

# State file to track processed SMS rowids (avoids reprocessing on restart)
STATE_FILE = Path(__file__).parent / ".sms_state.json"

POLL_INTERVAL = 300  # seconds (5 minutes — no need for realtime)

SENDERS = {
    "kapital": ["Kapitalbank", "KAPITALBANK", "KAPITAL"],
    "uzum":    ["UzumBank", "UZUMBANK", "Uzum"],
}
ALL_SENDERS = [s for group in SENDERS.values() for s in group]

import sys
sys.path.insert(0, str(Path(__file__).parent))
from parsers.kapital import parse_kapital
from parsers.uzum    import parse_uzum
from sink            import push_to_actual
# ── State (processed rowids) ─────────────────────────────────────────────

def load_state() -> set:
    if STATE_FILE.exists():
        try:
            return set(json.loads(STATE_FILE.read_text()))
        except Exception:
            pass
    return set()


def save_state(processed: set):
    STATE_FILE.write_text(json.dumps(sorted(processed)))


# ── chat.db reader ────────────────────────────────────────────────────────

def _copy_db() -> bool:
    import time as _time
    # If cron already made a fresh copy, use it directly
    if CHAT_TMP.exists():
        age = _time.time() - CHAT_TMP.stat().st_mtime
        if age < COPY_MAX_AGE_SECS:
            return True  # fresh copy from cron — no FDA needed

    # Fallback: try to copy ourselves (needs FDA if cron not running)
    try:
        shutil.copy2(CHAT_DB, CHAT_TMP)
        return True
    except PermissionError:
        print("❌ Cannot read chat.db — start copy_chat_db.sh from Terminal or grant FDA")
        return False


def read_new_sms(last_rowid: int) -> list[tuple]:
    if not _copy_db():
        return []

    conn = sqlite3.connect(CHAT_TMP)
    cur  = conn.cursor()

    conditions = " OR ".join(["h.id LIKE ?" for _ in ALL_SENDERS])
    params     = [f"%{s}%" for s in ALL_SENDERS] + [last_rowid]

    cur.execute(f"""
        SELECT m.ROWID, h.id, m.text,
               datetime(m.date/1000000000 + 978307200, 'unixepoch', 'localtime')
        FROM message m
        JOIN handle h ON m.handle_id = h.ROWID
        WHERE ({conditions})
          AND m.ROWID > ?
          AND m.is_from_me = 0
          AND m.text IS NOT NULL AND m.text != ''
        ORDER BY m.ROWID ASC
    """, params)

    rows = cur.fetchall()
    conn.close()
    return rows


def get_max_rowid() -> int:
    if not _copy_db():
        return 0
    conn = sqlite3.connect(CHAT_TMP)
    cur  = conn.cursor()
    conditions = " OR ".join(["h.id LIKE ?" for _ in ALL_SENDERS])
    params     = [f"%{s}%" for s in ALL_SENDERS]
    cur.execute(f"""
        SELECT COALESCE(MAX(m.ROWID), 0)
        FROM message m
        JOIN handle h ON m.handle_id = h.ROWID
        WHERE {conditions} AND m.is_from_me = 0
    """, params)
    result = cur.fetchone()[0]
    conn.close()
    return result


# ── Process ───────────────────────────────────────────────────────────────

def _pick_parser(sender_id: str):
    s = sender_id.lower()
    for name in SENDERS["uzum"]:
        if name.lower() in s:
            return parse_uzum
    return parse_kapital


def process_rows(rows, dry_run: bool, processed: set) -> int:
    saved = 0
    for rowid, sender, text, msg_date in rows:
        if rowid in processed:
            continue

        parser = _pick_parser(sender)
        parsed = parser(text)

        processed.add(rowid)  # mark regardless (even if no match)

        if parsed is None:
            continue

        account_name = f"{parsed['source']} *{parsed['card_last4']}" if parsed.get('card_last4') else parsed['source']
        print(f"  {'[DRY] ' if dry_run else ''}✓ {parsed['date']} {parsed['time']} | "
              f"*{parsed.get('card_last4') or '????'} | {parsed['category']} | "
              f"{parsed['amount']:,.0f} {parsed['currency']} | {parsed['merchant']}")

        if not dry_run:
            if push_to_actual(parsed, account_name=account_name):
                saved += 1

    return saved


# ── Main ──────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="SMS watcher → Actual Budget")
    parser.add_argument("--once",    action="store_true", help="Run once and exit")
    parser.add_argument("--dry-run", action="store_true", help="Preview only, no writes")
    parser.add_argument("--history", action="store_true", help="Process all historical SMS")
    args = parser.parse_args()

    processed = load_state()
    print(f"📊 Known processed SMS: {len(processed)}")

    if args.history:
        last_rowid = 0
        print("📜 History mode: processing ALL bank SMS")
    else:
        last_rowid = get_max_rowid()
        print(f"👁  Watching from ROWID > {last_rowid} (new SMS only)")

    print(f"🔍 Senders: {ALL_SENDERS}")
    print(f"⏱  Poll interval: {POLL_INTERVAL}s\n")

    try:
        while True:
            rows = read_new_sms(last_rowid)

            if rows:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Found {len(rows)} new SMS:")
                saved = process_rows(rows, args.dry_run, processed)
                if saved:
                    print(f"  💾 Pushed {saved} transactions to Actual Budget")
                if not args.dry_run:
                    save_state(processed)
                last_rowid = max(r[0] for r in rows)
            else:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] No new SMS", end="\r")

            if args.once:
                break

            time.sleep(POLL_INTERVAL)

    except KeyboardInterrupt:
        print("\n\n👋 Stopped.")
        if not args.dry_run:
            save_state(processed)


if __name__ == "__main__":
    main()
