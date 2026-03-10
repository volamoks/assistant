#!/bin/bash
# Writes update-sentinel.json to trigger the host watchdog.
# Usage: trigger.sh <action> <reason>
# Actions: restart | rebuild | pull

ACTION="${1:-restart}"
REASON="${2:-Manual trigger}"
SENTINEL="/home/node/.openclaw/core/update-sentinel.json"

# Validate action
if [[ "$ACTION" != "restart" && "$ACTION" != "rebuild" && "$ACTION" != "pull" ]]; then
    echo "ERROR: Unknown action '$ACTION'. Use: restart | rebuild | pull"
    exit 1
fi

cat > "$SENTINEL" <<EOF
{
  "action": "$ACTION",
  "reason": "$REASON",
  "requested_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "requested_by": "bot"
}
EOF

echo "✅ Sentinel written: action=$ACTION"
echo "⏳ Host watchdog will pick it up within 30 seconds."
echo "⚠️  Bot will disconnect during $ACTION (~15-30s for restart, ~5min for rebuild)."
