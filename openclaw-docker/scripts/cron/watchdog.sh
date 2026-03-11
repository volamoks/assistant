#!/bin/bash
# OpenClaw Watchdog Cron - Wrapper for watchdog.sh
# Checks watchdog output and sends Telegram alert only if issues found
# This replaces the agentTurn-based watchdog cron with pure bash

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WATCHDOG_SCRIPT="/data/bot/openclaw-docker/scripts/watchdog.sh"
NOTIFY_SCRIPT="/data/bot/openclaw-docker/skills/telegram/notify.py"

# Run watchdog and capture output
OUTPUT=$(bash "$WATCHDOG_SCRIPT" 2>&1)
EXIT_CODE=$?

# Check for issues in output
if echo "$OUTPUT" | grep -qiE "restarting|failure|failed|error|unhealthy"; then
    # Send alert to Telegram
    python3 "$NOTIFY_SCRIPT" "⚠️ OpenClaw Gateway Alert

$OUTPUT" --chat-id "6053956251" 2>/dev/null || true
fi

# Exit silently (cron expects no output for healthy state)
exit 0
