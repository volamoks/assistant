#!/usr/bin/env python3
"""
Daily Report — collects context from memory files + Vikunja tasks,
makes ONE LLM call to generate summary, sends to Telegram.
Target: ~20-30s vs 939s (agent reading files one by one).
"""

import os
import sys
import subprocess
import requests
from pathlib import Path
from datetime import datetime

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
LITELLM_URL = os.getenv("LITELLM_URL", "http://localhost:18788/v1/chat/completions")
USE_LOCAL_LLM = os.getenv("USE_LOCAL_LLM", "true").lower() == "true"
CLAW_MODEL = os.getenv("CLAW_MODEL", "litellm/claw-cron-smart")  # 9b model

VAULT_PATH = Path(os.getenv("USER_VAULT_PATH", "/data/obsidian"))
MEMORY_FILE = Path("/home/node/.openclaw/prompts/MEMORY.md")
VIKUNJA_SH = Path("/data/bot/openclaw-docker/skills/vikunja/vikunja.sh")
NOTIFY_PY = Path("/data/bot/openclaw-docker/skills/telegram/notify.py")
TELEGRAM_USER = "6053956251"

MAX_SECTION_CHARS = 3000


def read_file_safe(path: Path, max_chars: int = MAX_SECTION_CHARS) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")[:max_chars]
    except Exception:
        return ""


def run_cmd(cmd: list, timeout: int = 20) -> str:
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return (result.stdout or "").strip()
    except Exception as e:
        return f"(error: {e})"


def collect_context() -> str:
    today = datetime.now().strftime("%Y-%m-%d")
    sections = []

    # 1. MEMORY.md
    mem = read_file_safe(MEMORY_FILE)
    if mem:
        sections.append(f"## Bot Memory\n{mem}")

    # 2. Today's diary (if created by context-logger)
    for pattern in [f"Дневник_{today}.md", f"Diary_{today}.md"]:
        diary_file = VAULT_PATH / "Inbox" / pattern
        if diary_file.exists():
            sections.append(f"## Today's Diary\n{read_file_safe(diary_file)}")
            break

    # 3. Recent Vikunja tasks (undone)
    if VIKUNJA_SH.exists():
        vikunja_out = run_cmd(["bash", str(VIKUNJA_SH), "list-by-status", "undone"], timeout=15)
        if vikunja_out and "error" not in vikunja_out.lower()[:50]:
            sections.append(f"## Open Vikunja Tasks\n{vikunja_out[:MAX_SECTION_CHARS]}")

    # 4. HEARTBEAT.md (cron job statuses)
    heartbeat = VAULT_PATH.parent / "openclaw-docker/workspace/HEARTBEAT.md"
    hb_text = read_file_safe(heartbeat, 2000)
    if hb_text:
        sections.append(f"## System Heartbeat\n{hb_text}")

    # Fallback: workspace HEARTBEAT
    if not hb_text:
        hb2 = Path("/home/node/.openclaw/workspace/HEARTBEAT.md")
        hb2_text = read_file_safe(hb2, 2000)
        if hb2_text:
            sections.append(f"## System Heartbeat\n{hb2_text}")

    return "\n\n".join(sections) if sections else "(no context available)"


def generate_summary(context: str) -> str:
    if not GROQ_API_KEY and not USE_LOCAL_LLM:
        return "Error: GROQ_API_KEY not set and local LLM not enabled"

    today = datetime.now().strftime("%d %b %Y")
    model = CLAW_MODEL if USE_LOCAL_LLM else "llama-3.3-70b-versatile"
    url = LITELLM_URL if USE_LOCAL_LLM else "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Content-Type": "application/json"}
    if not USE_LOCAL_LLM:
        headers["Authorization"] = f"Bearer {GROQ_API_KEY}"

    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a concise daily reporter for a personal AI assistant system. "
                    "Respond in Russian. Be brief and clear. "
                    "Format: plain text with emoji, max 400 words. No markdown headers."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Сделай краткий ежедневный отчёт за {today}.\n\n"
                    "Контекст:\n"
                    f"{context}\n\n"
                    "Структура отчёта:\n"
                    "📋 Открытых задач: N (из Vikunja)\n"
                    "🔴 Критичных: (если есть [CRITICAL] задачи)\n"
                    "✅ Система работает: (статус крон-джобов из heartbeat)\n"
                    "⚠️ Проблемы: (если есть ошибки)\n"
                    "💡 На завтра: (топ-2 задачи из Vikunja)\n\n"
                    "Не повторяй контекст дословно — только суть."
                ),
            },
        ],
        "temperature": 0.3,
        "max_tokens": 500,
    }

    resp = requests.post(
        url,
        headers=headers,
        json=payload,
        timeout=60,  # Local model might be slower than Groq
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"].strip()


def send_telegram(text: str):
    if not NOTIFY_PY.exists():
        print(f"notify.py not found at {NOTIFY_PY}")
        print(text)
        return

    header = f"📊 Ежедневный отчёт — {datetime.now().strftime('%d %b %Y')}\n\n"
    full_msg = header + text

    result = subprocess.run(
        ["python3", str(NOTIFY_PY), full_msg],
        capture_output=True,
        text=True,
        timeout=15,
    )
    if result.returncode != 0:
        print(f"Telegram send failed: {result.stderr}")
    else:
        print("Telegram message sent.")


def main():
    print(f"[{datetime.now()}] Collecting context...")
    context = collect_context()
    print(f"  Context: {len(context)} chars")

    print(f"[{datetime.now()}] Generating summary (1 LLM call)...")
    summary = generate_summary(context)
    print(f"  Summary: {len(summary)} chars")

    send_telegram(summary)


if __name__ == "__main__":
    main()
