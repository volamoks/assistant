#!/usr/bin/env python3
"""
Context Logger — reads today's sessions from lcm.db (lossless-claw SQLite),
makes ONE LLM call to create diary entry, sends one line to Telegram.

No agent. No tool calls. ~5s vs 180s+ agent approach.
Requires lossless-claw plugin to be active (writes to lcm.db).
"""

import os
import sys
import sqlite3
import requests
import subprocess
from pathlib import Path
from datetime import datetime, timedelta

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
LCM_DB = Path("/home/node/.openclaw/lcm.db")
VAULT_PATH = Path(os.getenv("USER_VAULT_PATH", "/data/obsidian"))
NOTIFY_PY = Path("/data/bot/openclaw-docker/skills/telegram/notify.py")

LOOK_BACK_HOURS = 24
MAX_CONVERSATIONS = 8       # max sessions to include in diary
MIN_MESSAGES = 5            # skip tiny automated sessions (< this many messages)
MAX_MSG_PER_CONV = 20       # messages per conversation to send to LLM
MAX_CONTENT_CHARS = 400     # truncate long messages


def get_today_sessions(conn) -> list:
    since = datetime.now() - timedelta(hours=LOOK_BACK_HOURS)
    since_str = since.strftime("%Y-%m-%d %H:%M:%S")

    rows = conn.execute(
        """
        SELECT c.conversation_id, c.session_id, c.created_at,
               COUNT(m.message_id) as total_msgs
        FROM conversations c
        JOIN messages m ON m.conversation_id = c.conversation_id
        WHERE c.created_at >= ?
        GROUP BY c.conversation_id
        HAVING total_msgs >= ?
        ORDER BY c.created_at DESC
        LIMIT ?
        """,
        (since_str, MIN_MESSAGES, MAX_CONVERSATIONS),
    ).fetchall()
    return rows


def get_messages(conn, conv_id: int) -> list:
    """Get user + assistant messages only (skip tool outputs for brevity)."""
    rows = conn.execute(
        """
        SELECT role, content, created_at
        FROM messages
        WHERE conversation_id = ? AND role IN ('user', 'assistant')
        ORDER BY seq
        LIMIT ?
        """,
        (conv_id, MAX_MSG_PER_CONV),
    ).fetchall()
    return rows


def build_context(sessions: list, conn) -> str:
    parts = []
    for conv_id, session_id, created_at, total_msgs in sessions:
        msgs = get_messages(conn, conv_id)
        if not msgs:
            continue
        ts = created_at[:16] if created_at else "?"
        block = [f"### Сессия {ts} ({total_msgs} msgs total, session={session_id[:8]})"]
        for role, content, _ in msgs:
            content = (content or "").strip()[:MAX_CONTENT_CHARS]
            prefix = "👤" if role == "user" else "🤖"
            block.append(f"{prefix} {content}")
        parts.append("\n".join(block))
    return "\n\n".join(parts)


def generate_diary(context: str, n_sessions: int) -> str:
    if not GROQ_API_KEY:
        return "Error: GROQ_API_KEY not set"

    today = datetime.now().strftime("%Y-%m-%d")

    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a concise session diary writer for an AI assistant bot. "
                    "Write in Russian. Be very brief — max 3 bullet points per session. "
                    "Focus on: what was done, what was decided, what errors occurred."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Напиши краткий дневник сессий за {today}.\n\n"
                    "Формат строго:\n"
                    f"# Дневник {today}\n\n"
                    f"## Сессии ({n_sessions})\n\n"
                    "### [время сессии]\n"
                    "- Задача: ...\n"
                    "- Результат: ...\n"
                    "- Ошибки: ... (только если были)\n\n"
                    "## Ключевые инсайты дня\n"
                    "- ...\n\n"
                    "---\n"
                    "Данные сессий:\n\n"
                    f"{context}"
                ),
            },
        ],
        "temperature": 0.2,
        "max_tokens": 800,
    }

    resp = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"].strip()


def count_insights(diary: str) -> int:
    return diary.count("\n- ") + diary.count("\n• ")


def send_telegram(summary_line: str):
    if not NOTIFY_PY.exists():
        print(summary_line)
        return
    result = subprocess.run(
        ["python3", str(NOTIFY_PY), summary_line],
        capture_output=True,
        text=True,
        timeout=15,
    )
    if result.returncode != 0:
        print(f"Telegram error: {result.stderr}")


def main():
    if not LCM_DB.exists():
        print("lcm.db not found — lossless-claw plugin not active. Skipping.")
        sys.exit(0)

    # Open in read-write mode (WAL needs this for consistent reads)
    conn = sqlite3.connect(str(LCM_DB))
    conn.execute("PRAGMA journal_mode=WAL")

    try:
        sessions = get_today_sessions(conn)
    finally:
        conn.close()

    today = datetime.now().strftime("%Y-%m-%d")

    if not sessions:
        # Write empty diary
        diary_path = VAULT_PATH / "Inbox" / f"Дневник_{today}.md"
        diary_path.parent.mkdir(parents=True, exist_ok=True)
        diary_path.write_text(f"# Дневник {today}\n\nНет значимых сессий за сегодня.\n")
        line = f"✅ Дневник {today}: 0 сессий"
        send_telegram(line)
        print(line)
        return

    print(f"Found {len(sessions)} sessions. Generating diary (1 LLM call)...")

    # Reopen for message reading
    conn = sqlite3.connect(str(LCM_DB))
    conn.execute("PRAGMA journal_mode=WAL")
    try:
        context = build_context(sessions, conn)
    finally:
        conn.close()

    diary = generate_diary(context, len(sessions))
    insights = count_insights(diary)

    # Write to Obsidian inbox
    diary_path = VAULT_PATH / "Inbox" / f"Дневник_{today}.md"
    diary_path.parent.mkdir(parents=True, exist_ok=True)
    diary_path.write_text(diary + "\n")
    print(f"Diary written: {diary_path}")

    summary = f"✅ Дневник {today}: {len(sessions)} сессий, {insights} инсайтов"
    send_telegram(summary)
    print(summary)


if __name__ == "__main__":
    main()
