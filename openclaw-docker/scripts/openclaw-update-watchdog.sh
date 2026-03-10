#!/bin/bash
# OpenClaw Self-Update Watchdog
# Runs on HOST (macOS). Watches core/update-sentinel.json written by the bot.
# Performs: rebuild / restart / pull+rebuild depending on action field.

set -euo pipefail

# LaunchAgents have minimal PATH — add docker and compose explicitly
export PATH="/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin:$PATH"

COMPOSE_DIR="/Users/abror_mac_mini/Projects/bot/openclaw-docker"
SENTINEL="$COMPOSE_DIR/core/update-sentinel.json"
LOG="$COMPOSE_DIR/scripts/update-watchdog.log"
ENV_FILE="$COMPOSE_DIR/.env"

LOCKFILE="/tmp/openclaw-update-watchdog.lock"

log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') $1" | tee -a "$LOG"
}

# Prevent concurrent runs
exec 9>"$LOCKFILE"
flock -n 9 || exit 0

# Load .env for TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID
# Use grep-based parsing to avoid executing complex values (SSH keys, etc.)
if [ -f "$ENV_FILE" ]; then
    while IFS='=' read -r key val; do
        # Skip comments and blank lines
        [[ "$key" =~ ^[[:space:]]*# ]] && continue
        [[ -z "$key" ]] && continue
        # Only export simple VAR_NAME lines
        [[ "$key" =~ ^[A-Za-z_][A-Za-z0-9_]*$ ]] || continue
        # Strip surrounding quotes from value
        val="${val%\"}"
        val="${val#\"}"
        val="${val%\'}"
        val="${val#\'}"
        export "$key=$val"
    done < "$ENV_FILE"
fi

send_telegram() {
    local msg="$1"
    if [ -n "${TELEGRAM_BOT_TOKEN:-}" ] && [ -n "${TELEGRAM_CHAT_ID:-}" ]; then
        curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
            -d "chat_id=${TELEGRAM_CHAT_ID}" \
            -d "text=${msg}" \
            -d "parse_mode=HTML" > /dev/null 2>&1 || true
    fi
}

# Exit if no sentinel
[ -f "$SENTINEL" ] || exit 0

log "=== Sentinel detected ==="

# Parse sentinel
ACTION=$(python3 -c "import json,sys; d=json.load(open('$SENTINEL')); print(d.get('action','restart'))" 2>/dev/null || echo "restart")
REASON=$(python3 -c "import json,sys; d=json.load(open('$SENTINEL')); print(d.get('reason',''))" 2>/dev/null || echo "")
REQUESTED_BY=$(python3 -c "import json,sys; d=json.load(open('$SENTINEL')); print(d.get('requested_by','bot'))" 2>/dev/null || echo "bot")

log "Action: $ACTION | Reason: $REASON | By: $REQUESTED_BY"

# Remove sentinel immediately to avoid double-trigger
rm -f "$SENTINEL"

cd "$COMPOSE_DIR"

case "$ACTION" in
    pull)
        log "Pulling latest openclaw image..."
        send_telegram "🔄 <b>OpenClaw Update</b>: Pulling latest image..."
        docker pull ghcr.io/openclaw/openclaw:2026.3.8 >> "$LOG" 2>&1 || true
        log "Rebuilding image..."
        docker compose build openclaw >> "$LOG" 2>&1
        log "Restarting container..."
        docker compose up -d openclaw >> "$LOG" 2>&1
        log "Done: pull + rebuild + restart"
        send_telegram "✅ <b>OpenClaw</b>: Обновлён и перезапущен (pull+rebuild)\nПричина: ${REASON}"
        ;;
    rebuild)
        log "Rebuilding openclaw image..."
        send_telegram "🔨 <b>OpenClaw Update</b>: Пересборка образа..."
        docker compose build openclaw >> "$LOG" 2>&1
        log "Restarting container..."
        docker compose up -d openclaw >> "$LOG" 2>&1
        log "Done: rebuild + restart"
        send_telegram "✅ <b>OpenClaw</b>: Пересобран и перезапущен\nПричина: ${REASON}"
        ;;
    restart)
        log "Restarting openclaw container..."
        send_telegram "🔁 <b>OpenClaw</b>: Перезапускаю контейнер..."
        docker compose up -d openclaw >> "$LOG" 2>&1
        log "Done: restart"
        send_telegram "✅ <b>OpenClaw</b>: Перезапущен\nПричина: ${REASON}"
        ;;
    *)
        log "Unknown action: $ACTION — skipping"
        send_telegram "⚠️ <b>OpenClaw Watchdog</b>: Неизвестное действие: ${ACTION}"
        ;;
esac

log "=== Done ==="
