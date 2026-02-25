#!/bin/bash
VAULT_PATH="${OBSIDIAN_VAULT_PATH:-/data/obsidian/To claw}"
FILE="$VAULT_PATH/Bot/today-session.md"

if [ ! -f "$FILE" ] || [ "$(date +%Y-%m-%d)" != "$(head -1 "$FILE" | grep -oP '\d{4}-\d{2}-\d{2}')" ]; then
    echo "# Session Log — $(date +'%Y-%m-%d')" > "$FILE"
    echo "" >> "$FILE"
    echo "_Agent will append actions here throughout the day._" >> "$FILE"
fi
