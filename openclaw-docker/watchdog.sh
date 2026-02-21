#!/bin/bash

# OpenClaw Watchdog Script
# This script monitors the openclaw-latest Docker container.
# If the container crashes or gets stuck in a restart loop due to bad config,
# it automatically restores the git repository state and restarts the container.

CONTAINER_NAME="openclaw-latest"
PROJECT_DIR="/Users/abror_mac_mini/Projects/bot"
LOG_FILE="/tmp/openclaw-watchdog.log"
TELEGRAM_BOT_TOKEN=$(grep TELEGRAM_BOT_TOKEN "$PROJECT_DIR/openclaw-docker/.env" | cut -d '=' -f2)
TELEGRAM_CHAT_ID="6053956251" # Hardcoded from logs

# Check container status
STATUS=$(docker container inspect -f '{{.State.Status}}' "$CONTAINER_NAME" 2>/dev/null)
RESTARTING=$(docker container inspect -f '{{.State.Restarting}}' "$CONTAINER_NAME" 2>/dev/null)

if [ "$STATUS" == "" ]; then
    echo "$(date): Container $CONTAINER_NAME not found." >> "$LOG_FILE"
    exit 0
fi

# If container is dead or crash-looping
if [ "$STATUS" != "running" ] || [ "$RESTARTING" == "true" ]; then
    echo "$(date): CRASH DETECTED. Status: $STATUS, Restarting: $RESTARTING" >> "$LOG_FILE"
    
    # Send Telegram alert BEFORE restoring (if curl and token exist)
    if [ ! -z "$TELEGRAM_BOT_TOKEN" ]; then
        curl -s -X POST "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/sendMessage" \
            -d "chat_id=$TELEGRAM_CHAT_ID" \
            -d "text=🚨 *OpenClaw Crash Detected!* 🚨%0AThe container is in '$STATUS' state.%0AInitiating Git restore sequence..." \
            -d "parse_mode=Markdown" > /dev/null
    fi

    echo "$(date): Restoring Git repository at $PROJECT_DIR..." >> "$LOG_FILE"
    
    # Navigate to project dir and restore
    cd "$PROJECT_DIR"
    
    # Restore all modified files to HEAD
    git checkout -- . >> "$LOG_FILE" 2>&1
    
    # Remove any new untracked files (like newly created broken json schemas)
    git clean -fd >> "$LOG_FILE" 2>&1
    
    echo "$(date): Restarting Docker container..." >> "$LOG_FILE"
    docker restart "$CONTAINER_NAME" >> "$LOG_FILE" 2>&1
    
    # Send Telegram alert AFTER restoring
    if [ ! -z "$TELEGRAM_BOT_TOKEN" ]; then
        curl -s -X POST "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/sendMessage" \
            -d "chat_id=$TELEGRAM_CHAT_ID" \
            -d "text=✅ *OpenClaw Restored!*%0AGit repository has been hard-reset to the last working commit and the container was restarted." \
            -d "parse_mode=Markdown" > /dev/null
    fi
    
    echo "$(date): Recovery complete." >> "$LOG_FILE"
else
    # Everything is fine, no logging needed to avoid spam
    exit 0
fi
