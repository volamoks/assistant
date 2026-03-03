#!/bin/bash
echo "=== Docker Containers ==="
docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.RunningFor}}' 2>/dev/null || echo "Docker socket access failed"

echo ""
echo "=== Disk Usage ==="
df -h /

echo ""
echo "=== Recent Lessons Learned ==="
VAULT_PATH="${OBSIDIAN_VAULT_PATH:-/data/obsidian/vault}"
tail -n 15 "$VAULT_PATH/Bot/lessons-learned.md" 2>/dev/null

echo ""
echo "=== 📅 Today's Calendar ==="
if [ -f "/home/node/.openclaw/shared/google_token.json" ]; then
  bash /data/bot/openclaw-docker/scripts/gcal.sh today 2>/dev/null || echo "  (calendar unavailable)"
else
  echo "  (Google not authorized — run google_auth.py to enable)"
fi

echo ""
echo "=== 📬 Unread Inbox (top 3) ==="
if [ -f "/home/node/.openclaw/shared/google_token.json" ]; then
  bash /data/bot/openclaw-docker/scripts/gmail.sh inbox 3 2>/dev/null || echo "  (gmail unavailable)"
else
  echo "  (Google not authorized — run google_auth.py to enable)"
fi

