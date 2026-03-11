#!/bin/bash
# OpenClaw Watchdog - Auto-healing with rollback
# Checks if Gateway is healthy, restarts if not, rolls back after repeated failures

LOG="/tmp/openclaw_watchdog.log"
PORT=18789
RECOVER_SCRIPT="/data/bot/openclaw-docker/recover.sh"
FAILURE_COUNT_FILE="/tmp/openclaw_watchdog_failures"

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
    docker restart openclaw-latest 2>&1 | tee -a $LOG
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
    
    # Log to Obsidian error-log.md
    ERROR_LOG="/data/obsidian/vault/Bot/error-log.md"
    TIMESTAMP=$(date '+%Y-%m-%d %H:%M')
    cat >> "$ERROR_LOG" <<EOF

### 🔴 Watchdog Rollback — $TIMESTAMP

**Reason:** Gateway unhealthy after 2 restart attempts
**Action:** recover.sh executed (git checkout + restart)
**Failure count:** $(get_failure_count)

EOF
    
    bash "$RECOVER_SCRIPT" 2>&1 | tee -a $LOG
    reset_failure_count
    log "✅ Rollback complete — check Obsidian Bot/error-log.md"
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
            # First restart attempt
            increment_failure_count
            failures=$(get_failure_count)
            log "⚠️ Failure count: $failures"
            
            if restart_gateway; then
                reset_failure_count
            else
                # Second restart attempt
                increment_failure_count
                failures=$(get_failure_count)
                log "⚠️ Failure count: $failures"
                
                if [ "$failures" -ge 2 ]; then
                    log "🔙 Too many failures, triggering rollback..."
                    rollback_gateway
                fi
            fi
        fi
    fi
fi
