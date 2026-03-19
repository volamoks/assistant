#!/bin/bash
# Morning Briefing Cron — uses Obsidian Tasks (replaces Vikunja)
# Collects tasks + system status and sends to Telegram

NOTIFY_SCRIPT="/data/bot/openclaw-docker/skills/telegram/notify.py"
TELEGRAM_CHAT="6053956251"
OBSIDIAN_TASKS="/data/bot/openclaw-docker/skills/obsidian_tasks/obsidian_tasks.py"

TODAY=$(date '+%d %b')

# Get task counts
TASK_COUNTS=$(python3 "$OBSIDIAN_TASKS" count-by-folder 2>/dev/null || echo "error")

# Parse counts
BOT_COUNT=$(echo "$TASK_COUNTS" | grep -oP 'bot: \K\d+' || echo "0")
WORK_COUNT=$(echo "$TASK_COUNTS" | grep -oP 'work: \K\d+' || echo "0")
PERSONAL_COUNT=$(echo "$TASK_COUNTS" | grep -oP 'personal: \K\d+' || echo "0")
TOTAL_COUNT=$(echo "$TASK_COUNTS" | grep -oP 'total: \K\d+' || echo "0")

# Get overdue
OVERDUE=$(python3 "$OBSIDIAN_TASKS" list-overdue 2>/dev/null)
OVERDUE_COUNT=$(echo "$OVERDUE" | grep -c "\- \[" || echo "0")

# Docker container count
CONTAINER_COUNT=$(docker ps --format '{{.Names}}' 2>/dev/null | wc -l || echo "?")

# System alerts (containers not running)
UNHEALTHY=$(docker ps --format '{{.Names}} ({{.Status}})' 2>/dev/null | grep -v "Up" | grep -v "healthy" | grep -v "starting" | wc -l || echo "0")

# Format the message
MESSAGE="🌙 Утренний брифинг — $TODAY

📋 Задач: $TOTAL_COUNT (🤖 $BOT_COUNT | 💼 $WORK_COUNT | 🏠 $PERSONAL_COUNT)
"

if [ "$OVERDUE_COUNT" -gt 0 ]; then
    MESSAGE+="⚠️ Просрочено: $OVERDUE_COUNT задач"
    MESSAGE+=$'\n'
fi

MESSAGE+="🐳 Контейнеров: $CONTAINER_COUNT"

if [ "$UNHEALTHY" -gt 0 ]; then
    MESSAGE+=" | ⚠️ $UNHEALTHY проблемы"
fi

MESSAGE+=$'\n\n'
MESSAGE+="📂 Vault: /data/obsidian/vault/Bot/Tasks/"
MESSAGE+=$'\n'
MESSAGE+="📄 Полная сводка: vault-viewer /tasks"

# Send to Telegram
python3 "$NOTIFY_SCRIPT" "$MESSAGE" --chat-id "$TELEGRAM_CHAT" 2>/dev/null || true

exit 0
