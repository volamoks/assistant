#!/bin/bash
# Morning Briefing Cron - Get Vikunja tasks and send to Telegram
# This replaces the agentTurn-based morning-briefing cron with pure bash
# Uses vikunja.sh to get tasks and formats them for Telegram

VIKUNJA_SCRIPT="/data/bot/openclaw-docker/skills/vikunja/vikunja.sh"
NOTIFY_SCRIPT="/data/bot/openclaw-docker/skills/telegram/notify.py"
TELEGRAM_CHAT="6053956251"

TODAY=$(date '+%d %b')

# Get overdue tasks
OVERDUE=$(bash "$VIKUNJA_SCRIPT" list-overdue 2>/dev/null)
OVERDUE_COUNT=$(echo "$OVERDUE" | grep -c "id" || echo "0")

# Get all undone tasks
UNDONE=$(bash "$VIKUNJA_SCRIPT" list-by-status undone 2>/dev/null)

# Count by type
BUG_COUNT=$(echo "$UNDONE" | grep -c "\[BUG\]" || echo "0")
IMPROVE_COUNT=$(echo "$UNDONE" | grep -c "\[IMPROVE\]" || echo "0")
IDEA_COUNT=$(echo "$UNDONE" | grep -c "\[IDEA\]" || echo "0")

# Format the message
MESSAGE="🌙 Утренний брифинг — $TODAY

"

if [ "$OVERDUE_COUNT" -gt 0 ]; then
    MESSAGE+="⚠️ Просрочено: $OVERDUE_COUNT задач"
    MESSAGE+=$'\n'
    MESSAGE+=$(echo "$OVERDUE" | grep "title" | head -3 | sed 's/.*"title": "\(.*\)".*/\1/' | sed 's/^/  • /')
    MESSAGE+=$'\n\n'
fi

if [ "$BUG_COUNT" -gt 0 ]; then
    MESSAGE+="🔴 Баги: $BUG_COUNT задач"
    MESSAGE+=$'\n'
    MESSAGE+=$(echo "$UNDONE" | grep "\[BUG\]" | head -3 | sed 's/.*"title": "\(.*\)".*/\1/' | sed 's/^/  • /')
    MESSAGE+=$'\n\n'
fi

if [ "$IMPROVE_COUNT" -gt 0 ]; then
    MESSAGE+="🔧 Улучшения: $IMPROVE_COUNT задач"
    MESSAGE+=$'\n'
    MESSAGE+=$(echo "$UNDONE" | grep "\[IMPROVE\]" | head -3 | sed 's/.*"title": "\(.*\)".*/\1/' | sed 's/^/  • /')
    MESSAGE+=$'\n\n'
fi

if [ "$IDEA_COUNT" -gt 0 ]; then
    MESSAGE+="💡 Идеи: $IDEA_COUNT задач"
    MESSAGE+=$'\n'
    MESSAGE+=$(echo "$UNDONE" | grep "\[IDEA\]" | head -3 | sed 's/.*"title": "\(.*\)".*/\1/' | sed 's/^/  • /')
    MESSAGE+=$'\n\n'
fi

MESSAGE+="📄 Полная сводка: vikunja.sh weekly-report"

# Send to Telegram
python3 "$NOTIFY_SCRIPT" "$MESSAGE" --chat-id "$TELEGRAM_CHAT" 2>/dev/null || true

exit 0
