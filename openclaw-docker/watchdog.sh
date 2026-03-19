#!/bin/bash

# OpenClaw Watchdog Script
# This script monitors the openclaw-latest Docker container.
# If the container crashes or gets stuck in a restart loop due to bad config,
# it automatically restores the git repository state and restarts the container.

# Fix for cron: set full path and docker socket
export PATH="/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin:$PATH"
export DOCKER_HOST="unix:///Users/abror_mac_mini/.orbstack/run/docker.sock"

CONTAINER_NAME="openclaw-latest"
PROJECT_DIR="/Users/abror_mac_mini/Projects/bot"
OBSIDIAN_DIR="/Users/abror_mac_mini/Library/Mobile Documents/iCloud~md~obsidian/Documents/My Docs/vault/Bot/crash-configs"
LOG_FILE="/tmp/openclaw-watchdog.log"
DOCKER_BIN="/usr/local/bin/docker"
MAINTENANCE_FLAG="/tmp/openclaw-maintenance.lock"

# Skip watchdog during planned maintenance
if [ -f "$MAINTENANCE_FLAG" ]; then
    echo "$(date): Maintenance mode active, skipping watchdog." >> "$LOG_FILE"
    exit 0
fi

# Check if docker exists at expected path, fallback to system docker
if [ ! -x "$DOCKER_BIN" ]; then
    DOCKER_BIN="docker"
fi

TELEGRAM_BOT_TOKEN=$(grep TELEGRAM_BOT_TOKEN "$PROJECT_DIR/openclaw-docker/.env" | cut -d '=' -f2)
TELEGRAM_CHAT_ID="${TELEGRAM_CHAT_ID:-6053956251}" # Default from .env if set

# Check container status
STATUS=$($DOCKER_BIN container inspect -f '{{.State.Status}}' "$CONTAINER_NAME" 2>/dev/null)
RESTARTING=$($DOCKER_BIN container inspect -f '{{.State.Restarting}}' "$CONTAINER_NAME" 2>/dev/null)

if [ "$STATUS" == "" ]; then
    echo "$(date): Container $CONTAINER_NAME not found." >> "$LOG_FILE"
    exit 0
fi

# If container is dead or crash-looping
if [ "$STATUS" != "running" ] || [ "$RESTARTING" == "true" ]; then
    echo "$(date): CRASH DETECTED. Status: $STATUS, Restarting: $RESTARTING" >> "$LOG_FILE"

    # --- Save broken config to Obsidian before restoring ---
    TIMESTAMP=$(date +"%Y-%m-%d_%H-%M-%S")
    CRASH_FILE="$OBSIDIAN_DIR/$TIMESTAMP-crash.md"
    mkdir -p "$OBSIDIAN_DIR"

    cd "$PROJECT_DIR"
    DIFF=$(git diff openclaw-docker/ 2>/dev/null)
    MODIFIED=$(git status --short openclaw-docker/ | grep -v "^?" | awk '{print $2}' | tr '\n' ', ')

    cat > "$CRASH_FILE" <<EOF
# Crash Config — $TIMESTAMP

**Trigger:** watchdog (auto)
**Container status:** $STATUS / Restarting: $RESTARTING
**Modified files:** ${MODIFIED:-none}

## Git Diff (что изменил бот)

\`\`\`diff
${DIFF:-No changes detected}
\`\`\`
EOF
    echo "$(date): Crash config saved to $CRASH_FILE" >> "$LOG_FILE"
    # -------------------------------------------------------

    # Send Telegram alert BEFORE restoring (if curl and token exist)
    if [ ! -z "$TELEGRAM_BOT_TOKEN" ]; then
        curl -s -X POST "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/sendMessage" \
            -d "chat_id=$TELEGRAM_CHAT_ID" \
            -d "text=🚨 *OpenClaw Crash Detected!* 🚨%0AStatus: $STATUS%0AModified: ${MODIFIED:-none}%0ACrash config saved to Obsidian.%0AInitiating Git restore..." \
            -d "parse_mode=Markdown" > /dev/null
    fi

    echo "$(date): Restoring Last Known Good (LKG) config..." >> "$LOG_FILE"

    LKG_FILE="$PROJECT_DIR/openclaw-docker/core/openclaw.json.lkg"
    TARGET_FILE="$PROJECT_DIR/openclaw-docker/core/openclaw.json"
    
    if [ -f "$LKG_FILE" ]; then
        cp "$LKG_FILE" "$TARGET_FILE" >> "$LOG_FILE" 2>&1
        echo "$(date): LKG config restored successfully." >> "$LOG_FILE"
    else
        echo "$(date): WARNING: LKG file not found! Falling back to Git restore." >> "$LOG_FILE"
        git checkout -- "$TARGET_FILE" >> "$LOG_FILE" 2>&1
    fi

    echo "$(date): Restarting Docker container..." >> "$LOG_FILE"
    $DOCKER_BIN restart "$CONTAINER_NAME" >> "$LOG_FILE" 2>&1

    # Send Telegram alert AFTER restoring
    if [ ! -z "$TELEGRAM_BOT_TOKEN" ]; then
        curl -s -X POST "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/sendMessage" \
            -d "chat_id=$TELEGRAM_CHAT_ID" \
            -d "text=✅ *OpenClaw Restored!*%0AConfig reverted to last git commit. Container restarted.%0A📝 Crash config saved in Obsidian: Bot/crash-configs/$TIMESTAMP-crash.md" \
            -d "parse_mode=Markdown" > /dev/null
    fi

    echo "$(date): Recovery complete." >> "$LOG_FILE"
else
    # Everything is fine, check uptime to create LKG
    STARTED_AT=$(docker container inspect -f '{{.State.StartedAt}}' "$CONTAINER_NAME" | cut -d. -f1)
    if [ ! -z "$STARTED_AT" ]; then
        STARTED_SEC=$(date -j -u -f "%Y-%m-%dT%H:%M:%S" "$STARTED_AT" "+%s" 2>/dev/null || echo 0)
        NOW_SEC=$(date -u "+%s")
        UPTIME_SEC=$((NOW_SEC - STARTED_SEC))
        
        # If running for more than 3 minutes (180s) without restarting, save LKG
        if [ "$UPTIME_SEC" -gt 180 ]; then
            TARGET_FILE="$PROJECT_DIR/openclaw-docker/core/openclaw.json"
            LKG_FILE="$PROJECT_DIR/openclaw-docker/core/openclaw.json.lkg"
            # Only copy if the LKG doesn't exist or is different
            if ! cmp -s "$TARGET_FILE" "$LKG_FILE" 2>/dev/null; then
                cp "$TARGET_FILE" "$LKG_FILE"
                echo "$(date): New LKG config saved (uptime: ${UPTIME_SEC}s)" >> "$LOG_FILE"
            fi
        fi
    fi
    exit 0
fi
