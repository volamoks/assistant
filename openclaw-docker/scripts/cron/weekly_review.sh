#!/bin/bash
# Weekly Review Cron — uses Obsidian Tasks (replaces Vikunja)
# Collects task summary and sends to Telegram

NOTIFY_SCRIPT="/data/bot/openclaw-docker/skills/telegram/notify.py"
TELEGRAM_CHAT="6053956251"
OBSIDIAN_TASKS="/data/bot/openclaw-docker/skills/obsidian_tasks/obsidian_tasks.py"

TODAY=$(date '+%d %b')

# Get all pending tasks as raw lines
BOT_TASKS=$(python3 "$OBSIDIAN_TASKS" list --tag task/bot 2>/dev/null || echo "")
WORK_TASKS=$(python3 "$OBSIDIAN_TASKS" list --tag task/work 2>/dev/null || echo "")
PERSONAL_TASKS=$(python3 "$OBSIDIAN_TASKS" list --tag task/personal 2>/dev/null || echo "")

# Get counts
TASK_COUNTS=$(python3 "$OBSIDIAN_TASKS" count-by-folder 2>/dev/null || echo "error")
BOT_COUNT=$(echo "$TASK_COUNTS" | grep -oP 'bot: \K\d+' || echo "0")
WORK_COUNT=$(echo "$TASK_COUNTS" | grep -oP 'work: \K\d+' || echo "0")
PERSONAL_COUNT=$(echo "$TASK_COUNTS" | grep -oP 'personal: \K\d+' || echo "0")
TOTAL=$(echo "$TASK_COUNTS" | grep -oP 'total: \K\d+' || echo "0")

# Extract bug/improve/idea tasks
BUGS=$(echo "$BOT_TASKS" | grep -c "\[BUG\]" || echo "0")
IMPROVES=$(echo "$BOT_TASKS" | grep -c "\[IMPROVE\]" || echo "0")
IDEAS=$(echo "$BOT_TASKS" | grep -c "\[IDEA\]" || echo "0")

# Format the message
MESSAGE="🔧 Еженедельный ревью — $TODAY

📊 Всего задач: $TOTAL (🤖 $BOT_COUNT | 💼 $WORK_COUNT | 🏠 $PERSONAL_COUNT)
"

if [ "$BUGS" -gt 0 ]; then
    MESSAGE+="🔴 Багов: $BUGS"
    MESSAGE+=$'\n'
fi

if [ "$IMPROVES" -gt 0 ]; then
    MESSAGE+="🔧 Улучшений: $IMPROVES"
    MESSAGE+=$'\n'
fi

if [ "$IDEAS" -gt 0 ]; then
    MESSAGE+="💡 Идей: $IDEAS"
    MESSAGE+=$'\n'
fi

if [ "$TOTAL" -eq 0 ]; then
    python3 "$NOTIFY_SCRIPT" "✅ Еженедельный ревью: нет накопленных задач, всё актуально." --chat-id "$TELEGRAM_CHAT" 2>/dev/null || true
    exit 0
fi

MESSAGE+=$'\n---\n'
MESSAGE+="📂 Vault Tasks: https://vault.volamoks.store/tasks"
MESSAGE+=$'\n\n'
MESSAGE+="Ответь:"
MESSAGE+=$'\n'
MESSAGE+="• \"покажи задачи\" — подробнее"
MESSAGE+=$'\n'
MESSAGE+="• \"пропускай\" — закрой уведомление"

# Send to Telegram
python3 "$NOTIFY_SCRIPT" "$MESSAGE" --chat-id "$TELEGRAM_CHAT" 2>/dev/null || true

exit 0
