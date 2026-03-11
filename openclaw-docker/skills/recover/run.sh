#!/bin/bash
# recover skill — run recover.sh and report result

set -e

RECOVER_SCRIPT="/data/bot/openclaw-docker/recover.sh"
NOTIFY_SCRIPT="/data/bot/openclaw-docker/skills/telegram/notify.py"
CHAT_ID="6053956251"

echo "🔙 Starting rollback to last git commit..."

# Run recover.sh
OUTPUT=$(bash "$RECOVER_SCRIPT" 2>&1)
EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    RESULT="✅ Rollback successful — бот откатан к последнему коммиту"
else
    RESULT="❌ Rollback failed — см. логи"
fi

# Send to Telegram
python3 "$NOTIFY_SCRIPT" "$RESULT

\`\`\`
$OUTPUT
\`\`\`" --chat-id "$CHAT_ID" 2>/dev/null || true

echo "$RESULT"
