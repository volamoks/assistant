#!/bin/bash
# OpenClaw Watchdog - Auto-healing
# Checks if Gateway is healthy and restarts if not

LOG="/tmp/openclaw_watchdog.log"
GATEWAY_URL="http://localhost:3000/health"
MAX_RETRIES=3

log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a $LOG
}

check_gateway() {
    curl -sf --max-time 5 "$GATEWAY_URL" > /dev/null 2>&1
    return $?
}

restart_gateway() {
    log "⚠️ Gateway unhealthy, restarting..."
    docker restart openclaw-latest 2>&1 | tee -a $LOG
    sleep 10
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
