#!/bin/bash
VAULT_PATH="${USER_VAULT_PATH:-/data/abror_vault}"

echo "=== Empty Files ==="
find "$VAULT_PATH" -name '*.md' -empty 2>/dev/null

echo ""
echo "=== Searching for Wikilinks ==="
grep -ro '\[\[[^]]*\]\]' "$VAULT_PATH" --include='*.md' 2>/dev/null | head -n 30
