#!/bin/bash
# Manual recovery: restore config from last git commit and restart openclaw

set -e

PROJECT_DIR="/Users/abror_mac_mini/Projects/bot"
OBSIDIAN_DIR="/Users/abror_mac_mini/Library/Mobile Documents/com~apple~CloudDocs/abror/Bot/crash-configs"
CONTAINER_NAME="openclaw-latest"

echo "=== OpenClaw Manual Recovery ==="
echo ""

cd "$PROJECT_DIR"

# --- Save broken config to Obsidian before restoring ---
TIMESTAMP=$(date +"%Y-%m-%d_%H-%M-%S")
CRASH_FILE="$OBSIDIAN_DIR/$TIMESTAMP-crash.md"
mkdir -p "$OBSIDIAN_DIR"

DIFF=$(git diff openclaw-docker/ 2>/dev/null)
MODIFIED=$(git status --short openclaw-docker/ | grep -v "^?" | awk '{print $2}' | tr '\n' ', ')

cat > "$CRASH_FILE" <<EOF
# Crash Config — $TIMESTAMP

**Trigger:** manual /recover
**Modified files:** ${MODIFIED:-none}

## Git Diff (что изменил бот)

\`\`\`diff
${DIFF:-No changes detected}
\`\`\`
EOF

echo "Crash config saved: Bot/crash-configs/$TIMESTAMP-crash.md"
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
