#!/bin/bash
# Morning Digest Cron - Run morning_digest.sh and send to Telegram
# This replaces the agentTurn-based morning-digest cron with pure bash

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DIGEST_SCRIPT="/data/bot/openclaw-docker/scripts/jobs/morning_digest.sh"
NOTIFY_SCRIPT="/data/bot/openclaw-docker/skills/telegram/notify.py"

TODAY=$(date '+%d %b')

# Run the morning digest script
OUTPUT=$(bash "$DIGEST_SCRIPT" 2>&1)
EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ] && [ -n "$OUTPUT" ]; then
    # Send to Telegram
    python3 "$NOTIFY_SCRIPT" "🌅 Morning Digest — $TODAY

$OUTPUT" --chat-id "6053956251" 2>/dev/null || true
else
    # Send error notification
    python3 "$NOTIFY_SCRIPT" "❌ Morning Digest Failed

$OUTPUT" --chat-id "6053956251" 2>/dev/null || true
fi

exit 0
