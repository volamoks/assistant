#!/bin/bash
# Manual recovery: restore config from last git commit and restart openclaw

set -e

GIT_ROOT="/data/bot"
PROJECT_DIR="$GIT_ROOT/openclaw-docker"
OBSIDIAN_DIR="/data/obsidian/vault/Bot/crash-configs"
CONTAINER_NAME="openclaw-latest"

echo "=== OpenClaw Manual Recovery ==="
echo ""

cd "$GIT_ROOT"

# --- Save broken config to Obsidian before restoring ---
TIMESTAMP=$(date +"%Y-%m-%d_%H-%M-%S")
CRASH_FILE="$OBSIDIAN_DIR/$TIMESTAMP-crash.md"
mkdir -p "$OBSIDIAN_DIR"

DIFF=$(git diff openclaw-docker/ 2>/dev/null)
MODIFIED=$(git status --short openclaw-docker/ | grep -v "^?" | awk '{print $2}' | tr '\n' ', ')
GATEWAY_LOG=$(tail -100 /home/node/.openclaw/gateway.log 2>/dev/null | grep -iE "error|warn|fatal|crash" | tail -20)

cat > "$CRASH_FILE" <<EOF
# Crash Config — $TIMESTAMP

**Trigger:** manual /recover
**Modified files:** ${MODIFIED:-none}
**Container:** $CONTAINER_NAME

## Git Diff (что изменил бот)

\`\`\`diff
${DIFF:-No changes detected}
\`\`\`

## Gateway Errors (last 20)

\`\`\`
${GATEWAY_LOG:-No recent errors in gateway.log}
\`\`\`

## Recovery Actions Taken

1. Saved this crash config
2. Ran \`git checkout -- openclaw-docker/\`
3. Ran \`docker restart $CONTAINER_NAME\`

---
EOF

echo "✅ Crash config saved: Bot/crash-configs/$TIMESTAMP-crash.md"
echo ""
# -------------------------------------------------------

echo "Modified files:"
git status --short openclaw-docker/ | grep -v "^?" || echo "  (none)"
echo ""

echo "Restoring config to last commit..."
git checkout -- openclaw-docker/
echo "Done."
echo ""

echo "Restarting container..."
docker restart "$CONTAINER_NAME"
echo "Done."
echo ""

echo "=== Recovery complete ==="
echo "Check Obsidian → Bot/crash-configs/ for the saved broken config."
