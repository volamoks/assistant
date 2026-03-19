#!/bin/bash
set -e
set -o pipefail

# OpenViking Obsidian Indexer with conversion
# 1. Converts docx/pdf to markdown
# 2. Adds to OpenViking

SOURCE_DIR="/data/obsidian"
OUTPUT_DIR="/home/node/.openclaw/obsidian_converted"
VIKING_API="http://viking-bridge:8100/v1"

echo "🔄 OpenViking Obsidian Indexer"
echo "================================"

# Step 1: Convert docx/pdf to markdown
echo "📄 Converting docx/pdf files..."
python3 /data/bot/openclaw-docker/scripts/obsidian_convert.py \
    --source "$SOURCE_DIR" \
    --output "$OUTPUT_DIR" \
    --json | python3 -c "
import json, sys
data = json.load(sys.stdin)
print(f'Converted: {len(data[\"converted\"])}')
print(f'Skipped (existing): {len(data[\"skipped\"])}')
print(f'Errors: {len(data[\"errors\"])}')
"

# Step 2: Add converted files to Viking
echo "📚 Adding to OpenViking..."
curl -s -X POST "$VIKING_API/resources" \
    -H "Content-Type: application/json" \
    -d "{
        \"path\": \"$OUTPUT_DIR\",
        \"reason\": \"Converted Obsidian documents (docx/pdf)\",
        \"wait\": false
    }" | python3 -c "
import json, sys
data = json.load(sys.stdin)
if data.get('status') == 'ok':
    print('✅ Indexed in OpenViking')
else:
    print(f'❌ Error: {data.get(\"error\")}')
"

echo "✅ Done!"
