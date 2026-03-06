#!/bin/bash
# Crypto Monitor - BTC Alert Runner
# Runs btc_alert.py inside openclaw-latest container
# Logs output to ~/Library/Logs/crypto_monitor.log

LOG_FILE="$HOME/Library/Logs/crypto_monitor.log"
CONTAINER_NAME="openclaw-latest"
SCRIPT_PATH="/home/node/.openclaw/skills/crypto_monitor/btc_alert.py"

# Ensure log directory exists
mkdir -p "$(dirname "$LOG_FILE")"

# Log function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
}

# Check if container is running
if ! docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    log "ERROR: Container ${CONTAINER_NAME} is not running"
    exit 1
fi

# Run the alert script
log "Running BTC alert check..."
docker exec ${CONTAINER_NAME} python3 ${SCRIPT_PATH} >> "$LOG_FILE" 2>&1
exit_code=$?

if [ $exit_code -eq 0 ]; then
    log "BTC alert check completed successfully"
else
    log "ERROR: BTC alert check failed with exit code $exit_code"
fi

exit $exit_code
