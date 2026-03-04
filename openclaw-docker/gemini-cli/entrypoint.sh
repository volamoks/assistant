#!/bin/bash
# Entrypoint script for Gemini CLI Docker service

set -e

echo "=== Gemini CLI Docker Service ==="

# Create config directory if not exists
mkdir -p "$GEMINI_CONFIG_DIR"

# Initialize settings.json if missing
if [ ! -f "$GEMINI_CONFIG_DIR/settings.json" ]; then
    echo '{ "theme": "Default", "mcpServers": {} }' > "$GEMINI_CONFIG_DIR/settings.json"
fi

echo "Gemini config dir: $GEMINI_CONFIG_DIR"
echo "=== Ready ==="

exec "$@"
