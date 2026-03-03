#!/bin/bash
VAULT_PATH="${OBSIDIAN_VAULT_PATH:-/data/obsidian/vault}"

echo "=== Empty Files ==="
find "$VAULT_PATH" -name '*.md' -empty 2>/dev/null

echo ""
echo "=== Searching for Wikilinks ==="
grep -ro '\[\[[^]]*\]\]' "$VAULT_PATH" --include='*.md' 2>/dev/null | head -n 30
