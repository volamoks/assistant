#!/bin/bash
set -e
echo "=== Docker Containers ==="
docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.RunningFor}}' || echo "Docker socket access failed"

echo ""
echo "=== Disk Usage ==="
df -h /

echo ""
echo "=== Recent Lessons Learned ==="
PROJ_PATH="${BOT_PROJECT_PATH:-/data/bot}"
VAULT_PATH="${USER_VAULT_PATH:-${PROJ_PATH}/abror_vault}"
tail -n 15 "$VAULT_PATH/Bot/lessons-learned.md"

echo ""
echo "=== 📅 Today's Calendar ==="
if [ -f "/home/node/.openclaw/shared/google_token.json" ]; then
  bash /data/bot/openclaw-docker/scripts/gcal.sh today || echo "  (calendar unavailable)"
else
  echo "  (Google not authorized — run google_auth.py to enable)"
fi

echo ""
echo "=== 📬 Unread Inbox (top 3) ==="
if [ -f "/home/node/.openclaw/shared/google_token.json" ]; then
  bash /data/bot/openclaw-docker/scripts/gmail.sh inbox 3 || echo "  (gmail unavailable)"
else
  echo "  (Google not authorized — run google_auth.py to enable)"
fi

