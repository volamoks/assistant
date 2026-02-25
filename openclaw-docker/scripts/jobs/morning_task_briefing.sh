#!/bin/bash
VAULT_PATH="${OBSIDIAN_VAULT_PATH:-/data/obsidian/To claw}"
grep -r '- \[ \]' "$VAULT_PATH" --include='*.md' -l 2>/dev/null | grep -v "Archive" | grep -v "Templates" | while read -r file; do
    echo "File: $file"
    grep '- \[ \]' "$file" | head -n 5 | sed 's/^/  /'
done
