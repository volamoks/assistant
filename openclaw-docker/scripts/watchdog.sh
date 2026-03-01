#!/bin/bash
# OpenClaw Watchdog - Auto-healing
# Checks if Gateway is healthy and restarts if not

LOG="/tmp/openclaw_watchdog.log"
PORT=18789

log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a $LOG
}

check_gateway() {
    bash -c ">/dev/tcp/localhost/$PORT" 2>/dev/null
    return $?
}

restart_gateway() {
    log "⚠️ Gateway unhealthy, restarting..."
    docker restart openclaw-latest 2>&1 | tee -a $LOG
    sleep 15
    if check_gateway; then
        log "✅ Gateway restarted successfully"
    else
        log "❌ Gateway restart failed"
    fi
}

# Main
log "=== Watchdog check ==="

if check_gateway; then
    log "✅ Gateway healthy"
else
    log "❌ Gateway unhealthy, attempt 1"
    sleep 5
    if check_gateway; then
        log "✅ Recovered on its own"
    else
        log "❌ Still unhealthy, attempt 2"
        sleep 5
        if check_gateway; then
            log "✅ Recovered on attempt 2"
        else
            restart_gateway
        fi
    fi
fi
