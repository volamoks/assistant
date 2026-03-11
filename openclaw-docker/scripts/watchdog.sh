#!/bin/bash
# OpenClaw Watchdog - Auto-healing with rollback
# Checks if Gateway is healthy, restarts if not, rolls back after repeated failures
#
# DESIGN NOTES:
# - Failure count stored in PERSISTENT location (not /tmp) to survive container restarts
# - docker restart kills this script — so git checkout + Telegram happen BEFORE restart
# - On rollback: fix config first, notify, THEN restart (script dies but fix already applied)

LOG="/tmp/openclaw_watchdog.log"
PORT=18789
RECOVER_SCRIPT="/data/bot/openclaw-docker/recover.sh"
NOTIFY_SCRIPT="/data/bot/openclaw-docker/skills/telegram/notify.py"
FAILURE_COUNT_FILE="/data/bot/openclaw-docker/scripts/watchdog_failures"
CHAT_ID="6053956251"

log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a $LOG
}

check_gateway() {
    bash -c ">/dev/tcp/localhost/$PORT" 2>/dev/null
    return $?
}

get_failure_count() {
    if [ -f "$FAILURE_COUNT_FILE" ]; then
        cat "$FAILURE_COUNT_FILE"
    else
        echo "0"
    fi
}

increment_failure_count() {
    local count=$(get_failure_count)
    echo $((count + 1)) > "$FAILURE_COUNT_FILE"
}

reset_failure_count() {
    echo "0" > "$FAILURE_COUNT_FILE"
}

restart_gateway() {
    log "⚠️ Gateway unhealthy, restarting..."
    # NOTE: docker restart kills this container (and this script) after SIGTERM
    # That's OK — the restart is the goal, script death is expected
    docker restart openclaw-latest 2>&1 | tee -a $LOG
    # If we're still alive after restart (unlikely from inside container),
    # check if healthy
    sleep 15
    if check_gateway; then
        log "✅ Gateway restarted successfully"
        return 0
    else
        log "❌ Gateway restart failed"
        return 1
    fi
}

rollback_gateway() {
    log "🔙 Multiple failures detected, rolling back to last git commit..."

    local failures=$(get_failure_count)
    local timestamp=$(date '+%Y-%m-%d %H:%M')

    # Step 1: Log to Obsidian error-log.md (before restart)
    ERROR_LOG="/data/obsidian/vault/Bot/error-log.md"
    cat >> "$ERROR_LOG" <<EOF

### 🔴 Watchdog Rollback — $timestamp

**Reason:** Gateway unhealthy after multiple restart attempts
**Action:** recover.sh executed (git checkout + restart)
**Failure count:** $failures

EOF

    # Step 2: Run git checkout to restore config (before restart)
    log "🔧 Restoring config via git checkout..."
    GIT_ROOT="/data/bot"
    if cd "$GIT_ROOT" && git checkout -- openclaw-docker/ 2>&1 | tee -a $LOG; then
        log "✅ Config restored from last git commit"
    else
        log "❌ Git checkout failed — attempting restart anyway"
    fi

    # Step 3: Save crash config to Obsidian (before restart)
    CRASH_DIR="/data/obsidian/vault/Bot/crash-configs"
    mkdir -p "$CRASH_DIR"
    CRASH_FILE="$CRASH_DIR/$(date +%Y-%m-%d_%H-%M-%S)-watchdog-rollback.md"
    cat > "$CRASH_FILE" <<EOF
# Watchdog Rollback — $(date +%Y-%m-%d_%H-%M-%S)

**Trigger:** automatic watchdog (failure count: $failures)
**Action:** git checkout -- openclaw-docker/ + docker restart

## Recovery Timeline
$(cat "$LOG" 2>/dev/null | tail -30)
EOF
    log "📝 Crash config saved: Bot/crash-configs/"

    # Step 4: Send Telegram notification (before restart)
    python3 "$NOTIFY_SCRIPT" "🔙 Watchdog Rollback

Failure count: $failures
Action: git checkout + restart
Time: $timestamp
Config restored to last commit." --chat-id "$CHAT_ID" 2>/dev/null || true

    # Step 5: Reset failure count (before restart — /tmp is lost anyway)
    reset_failure_count

    # Step 6: Restart container (this kills our script — that's OK, config is already fixed)
    log "🔄 Restarting container (script will be killed — that's expected)..."
    docker restart openclaw-latest 2>&1 | tee -a $LOG
}

# Main
log "=== Watchdog check ==="

if check_gateway; then
    log "✅ Gateway healthy"
    reset_failure_count
else
    log "❌ Gateway unhealthy, attempt 1"
    sleep 5
    if check_gateway; then
        log "✅ Recovered on its own"
        reset_failure_count
    else
        log "❌ Still unhealthy, attempt 2"
        sleep 5
        if check_gateway; then
            log "✅ Recovered on attempt 2"
            reset_failure_count
        else
            increment_failure_count
            failures=$(get_failure_count)
            log "⚠️ Failure count: $failures"

            if [ "$failures" -ge 2 ]; then
                # Multiple failures across restarts → rollback
                log "🔙 Too many failures ($failures), triggering rollback..."
                rollback_gateway
            else
                # First failure → just restart
                restart_gateway
            fi
        fi
    fi
fi
