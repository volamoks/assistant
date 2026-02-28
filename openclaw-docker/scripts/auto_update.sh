#!/bin/bash
# OpenClaw Auto-Updater
LOG="/tmp/openclaw_update.log"
PROJECT_DIR="/Users/abror_mac_mini/Projects/bot/openclaw-docker"
CONTAINER_NAME="openclaw-latest"

echo "=== $(date '+%Y-%m-%d %H:%M:%S') - Starting OpenClaw Update ===" >> "$LOG"

cd "$PROJECT_DIR" || exit 1

# 1. Pull the latest image
docker compose pull openclaw >> "$LOG" 2>&1

# 2. Rebuild the custom image with --pull to ensure base is updated
docker compose build openclaw >> "$LOG" 2>&1

# 3. Restart the container
docker compose up -d openclaw >> "$LOG" 2>&1

# Note: watchdog.sh will automatically handle rollback to LKG if the new version crashes
echo "=== $(date '+%Y-%m-%d %H:%M:%S') - Update Script Completed ===" >> "$LOG"
