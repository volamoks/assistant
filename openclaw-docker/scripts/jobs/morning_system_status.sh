#!/bin/bash
echo "=== Docker Containers ==="
docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.RunningFor}}' 2>/dev/null || echo "Docker socket access failed"

echo ""
echo "=== Disk Usage ==="
df -h /

echo ""
echo "=== Recent Lessons Learned ==="
VAULT_PATH="${OBSIDIAN_VAULT_PATH:-/data/obsidian/To claw}"
tail -n 15 "$VAULT_PATH/Bot/lessons-learned.md" 2>/dev/null
