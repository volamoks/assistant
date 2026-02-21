#!/bin/bash
set -e

# Usage: ./create_profile.sh [username] [port]
# Example: ./create_profile.sh wife 18790

NAME=${1:-"guest"}
PORT=${2:-"18790"}
BASE_DIR="$HOME/.openclaw"
PROFILE_DIR="$BASE_DIR/profiles/$NAME"

echo "👤 Creating Profile: $NAME (Port: $PORT)..."

mkdir -p "$PROFILE_DIR"
mkdir -p "$PROFILE_DIR/agents"
mkdir -p "$PROFILE_DIR/memory"

# 1. Copy Core Config
cp "$BASE_DIR/openclaw.json" "$PROFILE_DIR/config.json"

# 2. Update Port in Config
if [ "$(uname)" = "Darwin" ]; then
    sed -i '' "s/\"port\": [0-9]*/\"port\": $PORT/" "$PROFILE_DIR/config.json"
else
    sed -i "s/\"port\": [0-9]*/\"port\": $PORT/" "$PROFILE_DIR/config.json"
fi

# 3. Copy Agents (So you can tweak models just for this person)
cp "$BASE_DIR/agents/"*.json "$PROFILE_DIR/agents/"

# 3. Create Empty Memory (Fresh Start)
echo "# Memory for $NAME" > "$PROFILE_DIR/memory/MEMORY.md"

echo "✅ Profile '$NAME' created at $PROFILE_DIR"
echo ""
echo "👉 TO RUN:"
echo "openclaw --config $PROFILE_DIR/config.json --agents $PROFILE_DIR/agents"
