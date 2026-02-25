"""
humo_watcher.py — Watches @HUMOcardbot via Telethon → Actual Budget

Usage:
    python3 humo_watcher.py               # live mode (new messages)
    python3 humo_watcher.py --history     # import all historical messages
    python3 humo_watcher.py --history --dry-run --limit 20
"""
import argparse
import asyncio
import os
import re
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from telethon import TelegramClient, events

# Try multiple locations for .env file
ENV_PATHS = [
    Path(__file__).parent / ".env",
    Path.home() / ".env",
    Path("/data/bot/.env"),
]
for env_path in ENV_PATHS:
    if env_path.exists():
        load_dotenv(env_path)
        break

API_ID   = int(os.getenv("TELEGRAM_API_ID", "0"))
API_HASH = os.getenv("TELEGRAM_API_HASH", "")
SESSION  = str(Path(__file__).parent.parent / "openclaw-docker/workspace/telegram/session")

SOURCES = ["@HUMOcardbot"]

sys.path.insert(0, str(Path(__file__).parent))
from parsers.humo import parse_humo
from sink import push_to_actual


def _strip_markdown(text: str) -> str:
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text, flags=re.DOTALL)
    text = re.sub(r'__(.+?)__',     r'\1', text, flags=re.DOTALL)
    text = re.sub(r'`(.+?)`',       r'\1', text, flags=re.DOTALL)
    return text


def _account_name(parsed: dict) -> str:
    last4 = parsed.get("card_last4")
    return f"HUMO *{last4}" if last4 else "HUMO"


def _process(text: str, dry_run: bool) -> bool:
    parsed = parse_humo(_strip_markdown(text))
    if not parsed:
        return False

    print(f"  {'[DRY] ' if dry_run else ''}✓ {parsed['date']} {parsed['time']} | "
          f"*{parsed['card_last4'] or '????'} | {parsed['category']} | "
          f"{parsed['amount']:,.0f} {parsed['currency']} | {parsed['merchant']}")

    if not dry_run:
        push_to_actual(parsed, account_name=_account_name(parsed))
    return True


async def import_history(dry_run: bool, limit: int):
    async with TelegramClient(SESSION, API_ID, API_HASH) as client:
        for source in SOURCES:
            print(f"\n📥 Fetching history from {source}...")
            try:
                entity = await client.get_entity(source)
            except Exception as e:
                print(f"  ⚠️  Cannot access {source}: {e}")
                continue

            total = parsed_count = 0
            async for msg in client.iter_messages(entity, limit=limit or None):
                if not msg.text:
                    continue
                total += 1
                if _process(msg.text, dry_run):
                    parsed_count += 1

            print(f"\n  Scanned: {total} | Parsed: {parsed_count}")


async def watch_live(dry_run: bool):
    async with TelegramClient(SESSION, API_ID, API_HASH) as client:
        print(f"👁  Watching {SOURCES} for new messages... (Ctrl+C to stop)\n")

        @client.on(events.NewMessage(chats=SOURCES))
        async def handler(event):
            if event.text:
                _process(event.text, dry_run)

        await client.run_until_disconnected()


def main():
    parser = argparse.ArgumentParser(description="Humo TG watcher → Actual Budget")
    parser.add_argument("--history",  action="store_true", help="Import all historical messages")
    parser.add_argument("--dry-run",  action="store_true", help="Preview only, no writes")
    parser.add_argument("--limit",    type=int, default=0, help="Max messages (history mode, 0=all)")
    args = parser.parse_args()

    if args.history:
        asyncio.run(import_history(args.dry_run, args.limit))
    else:
        asyncio.run(watch_live(args.dry_run))


if __name__ == "__main__":
    main()
