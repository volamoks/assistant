#!/bin/bash
# Weekly Review Cron - Get Vikunja weekly report and send to Telegram
# This replaces the agentTurn-based weekly-review cron with pure bash

VIKUNJA_SCRIPT="/data/bot/openclaw-docker/skills/vikunja/vikunja.sh"
NOTIFY_SCRIPT="/data/bot/openclaw-docker/skills/telegram/notify.py"
TELEGRAM_CHAT="6053956251"

TODAY=$(date '+%d %b')

# Get weekly report
REPORT=$(bash "$VIKUNJA_SCRIPT" weekly-report 2>/dev/null)

# Check if there are any tasks
TASK_COUNT=$(echo "$REPORT" | grep -c "id" || echo "0")

if [ "$TASK_COUNT" -eq 0 ]; then
    # No tasks - send success message
    python3 "$NOTIFY_SCRIPT" "✅ Еженедельный ревью: нет накопленных задач в Vikunja, всё актуально." --chat-id "$TELEGRAM_CHAT" 2>/dev/null || true
    exit 0
fi

# Format the message with recommendations
MESSAGE="🔧 Еженедельный ревью — $TODAY
Накопилось $TASK_COUNT задач в Vikunja:

"

# Extract bugs with recommendations
BUGS=$(echo "$REPORT" | grep -A2 "\[BUG\]" | head -20)
if [ -n "$BUGS" ]; then
    MESSAGE+="📌 ФИКСЫ (баги):"
    MESSAGE+=$'\n'
    MESSAGE+=$(echo "$BUGS" | grep "title" | sed 's/.*"title": "\(.*\)".*/\1/' | head -5 | sed 's/^/  • /')
    MESSAGE+=$'\n\n'
fi

# Extract improvements
IMPROVES=$(echo "$REPORT" | grep -A2 "\[IMPROVE\]" | head -20)
if [ -n "$IMPROVES" ]; then
    MESSAGE+="🔧 УЛУЧШЕНИЯ:"
    MESSAGE+=$'\n'
    MESSAGE+=$(echo "$IMPROVES" | grep "title" | sed 's/.*"title": "\(.*\)".*/\1/' | head -5 | sed 's/^/  • /')
    MESSAGE+=$'\n\n'
fi

# Extract ideas
IDEAS=$(echo "$REPORT" | grep -A2 "\[IDEA\]" | head -20)
if [ -n "$IDEAS" ]; then
    MESSAGE+="🔍 НОВЫЕ ИДЕИ:"
    MESSAGE+=$'\n'
    MESSAGE+=$(echo "$IDEAS" | grep "title" | sed 's/.*"title": "\(.*\)".*/\1/' | head -5 | sed 's/^/  • /')
    MESSAGE+=$'\n\n'
fi

MESSAGE+="---
Ответь:
• \"применяй 1,3\" — реализую выбранные
• \"покажи 2\" — расскажу подробнее
• \"пропускай всё\" — закрою задачи"

# Send to Telegram
python3 "$NOTIFY_SCRIPT" "$MESSAGE" --chat-id "$TELEGRAM_CHAT" 2>/dev/null || true

exit 0
