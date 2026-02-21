#!/bin/bash
set -e

# Usage: ./start_server.sh
# Requires: pm2 (npm install -g pm2)

echo "🚀 Starting Jarvis Server Fleet..."

# 1. Start Main Instance (Owner)
pm2 start openclaw --name "jarvis-main" -- --profile default

# 2. Find and Start Profiles
BASE_DIR="$HOME/.openclaw/profiles"

if [ -d "$BASE_DIR" ]; then
    for profile in "$BASE_DIR"/*; do
        if [ -d "$profile" ]; then
            NAME=$(basename "$profile")
            CONFIG="$profile/config.json"
            AGENTS="$profile/agents"
            
            echo "   🔹 Launching profile: $NAME..."
            pm2 start openclaw --name "jarvis-$NAME" -- --config "$CONFIG" --agents "$AGENTS"
        fi
    done
fi

echo "✅ All systems go!"
echo "📊 Monitor with: pm2 monit"
echo "📝 Logs: pm2 logs"
