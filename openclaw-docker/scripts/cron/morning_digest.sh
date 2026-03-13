#!/bin/bash
# Morning Digest Cron - Creates full report in Obsidian + short Telegram summary
# Telegram: MAX 5 lines with "Подробнее" button to Obsidian note

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DIGEST_SCRIPT="/data/bot/openclaw-docker/scripts/jobs/morning_digest.sh"

# Run the morning digest script (now creates Obsidian report + short Telegram msg)
OUTPUT=$(bash "$DIGEST_SCRIPT" 2>&1)
EXIT_CODE=$?

if [ $EXIT_CODE -ne 0 ]; then
    # Send error notification
    NOTIFY_SCRIPT="/data/bot/openclaw-docker/skills/telegram/notify.py"
    python3 "$NOTIFY_SCRIPT" "❌ Morning Digest Failed

$OUTPUT" --chat-id "6053956251" 2>/dev/null || true
fi

exit 0
