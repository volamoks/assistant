#!/bin/bash
VAULT_PATH="${USER_VAULT_PATH:-/data/abror_vault}"
grep -r '- \[ \]' "$VAULT_PATH" --include='*.md' -l 2>/dev/null | grep -v "Archive" | grep -v "Templates" | while read -r file; do
    echo "File: $file"
    grep '- \[ \]' "$file" | head -n 5 | sed 's/^/  /'
done
