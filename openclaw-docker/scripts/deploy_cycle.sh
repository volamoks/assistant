#!/bin/bash
# Deploy Cycle — Safe deployment helper for the bot
#
# Usage:
#   deploy_cycle.sh checkpoint          — commit current state as recovery baseline
#   deploy_cycle.sh test                — run health test, rollback+analyze if failed
#   deploy_cycle.sh commit "message"    — commit after successful changes
#   deploy_cycle.sh status              — show current state
#
# Typical agent workflow:
#   1. bash deploy_cycle.sh checkpoint       # save known-good state
#   2. <make config changes>
#   3. bash deploy_cycle.sh test             # verify bot is healthy
#   4. bash deploy_cycle.sh commit "what changed"  # lock in new baseline

set -e

GIT_ROOT="/data/bot"
PROJECT_DIR="$GIT_ROOT/openclaw-docker"
CONTAINER_NAME="openclaw-latest"
GATEWAY_PORT=18789
NOTIFY_SCRIPT="$PROJECT_DIR/skills/telegram/notify.py"
CHAT_ID="6053956251"
LOG="/tmp/deploy_cycle.log"

CMD="${1:-status}"
MSG="${2:-auto-deploy checkpoint}"

log() { echo "$(date '+%Y-%m-%d %H:%M:%S') $1" | tee -a $LOG; }

# ── Health test ──────────────────────────────────────────────────────────────
check_health() {
    local attempts=0
    while [ $attempts -lt 6 ]; do
        if bash -c ">/dev/tcp/localhost/$GATEWAY_PORT" 2>/dev/null; then
            return 0
        fi
        attempts=$((attempts + 1))
        sleep 5
    done
    return 1
}

# ── checkpoint ───────────────────────────────────────────────────────────────
do_checkpoint() {
    log "=== Deploy Cycle: checkpoint ==="
    cd "$GIT_ROOT"

    local dirty
    dirty=$(git status --short openclaw-docker/ | grep -v "^?" | wc -l | tr -d ' ')

    if [ "$dirty" -eq 0 ]; then
        log "Nothing to commit — already clean"
        echo "✅ Already at clean baseline (nothing to commit)"
        return 0
    fi

    log "Committing $dirty changed file(s) as recovery baseline..."
    git add openclaw-docker/
    git commit -m "checkpoint: pre-deploy baseline $(date +%Y-%m-%d_%H:%M)" \
        --author="OpenClaw <bot@openclaw.local>" 2>&1 | tee -a $LOG

    log "✅ Checkpoint saved"
    echo "✅ Checkpoint committed. You can now make changes safely."
    echo "   Run 'deploy_cycle.sh test' after changes to verify."
}

# ── test ─────────────────────────────────────────────────────────────────────
do_test() {
    log "=== Deploy Cycle: test ==="

    log "Restarting container to apply changes..."
    docker restart "$CONTAINER_NAME" 2>&1 | tee -a $LOG
    sleep 5

    log "Waiting for gateway on port $GATEWAY_PORT..."
    if check_health; then
        log "✅ Health test passed — gateway is up"
        echo "✅ Deployment successful — gateway healthy on port $GATEWAY_PORT"
        return 0
    else
        log "❌ Health test FAILED — triggering rollback"
        echo "❌ Health test failed. Rolling back..."
        do_rollback
        return 1
    fi
}

# ── rollback ─────────────────────────────────────────────────────────────────
do_rollback() {
    log "=== Deploy Cycle: rollback ==="
    cd "$GIT_ROOT"

    TIMESTAMP=$(date +"%Y-%m-%d_%H-%M-%S")

    # Save crash config
    CRASH_DIR="/data/obsidian/vault/Bot/crash-configs"
    mkdir -p "$CRASH_DIR"
    CRASH_FILE="$CRASH_DIR/${TIMESTAMP}-deploy-cycle.md"
    DIFF=$(git diff openclaw-docker/ 2>/dev/null)
    MODIFIED=$(git status --short openclaw-docker/ | grep -v "^?" | awk '{print $2}' | tr '\n' ', ')
    cat > "$CRASH_FILE" <<EOF
# Deploy Cycle Rollback — $TIMESTAMP

**Trigger:** deploy_cycle.sh test (health check failed)
**Modified files:** ${MODIFIED:-none}

## Git Diff (what the bot changed)

\`\`\`diff
${DIFF:-No uncommitted changes}
\`\`\`

## Last 5 commits
$(git log --oneline -5 openclaw-docker/)
EOF
    log "📝 Crash config: Bot/crash-configs/${TIMESTAMP}-deploy-cycle.md"

    # Restore last commit
    log "🔧 Restoring config via git checkout..."
    git checkout -- openclaw-docker/ 2>&1 | tee -a $LOG

    # Notify
    python3 "$NOTIFY_SCRIPT" "⚠️ Deploy Cycle Rollback

Health test failed after applying changes.
Config restored to last git commit.
Files reverted: ${MODIFIED:-none}
Crash config: Bot/crash-configs/${TIMESTAMP}-deploy-cycle.md

Running failure analysis..." --chat-id "$CHAT_ID" 2>/dev/null || true

    # Analyze + write lesson
    log "🧠 Running failure analysis..."
    bash "$PROJECT_DIR/scripts/analyze_failure.sh" "$CRASH_FILE" "deploy_cycle" 2>&1 | tee -a $LOG || \
        log "⚠️ analyze_failure.sh failed"

    # Restart with clean config
    log "🔄 Restarting with restored config..."
    docker restart "$CONTAINER_NAME" 2>&1 | tee -a $LOG
}

# ── commit ───────────────────────────────────────────────────────────────────
do_commit() {
    log "=== Deploy Cycle: commit ==="
    cd "$GIT_ROOT"

    local dirty
    dirty=$(git status --short openclaw-docker/ | grep -v "^?" | wc -l | tr -d ' ')

    if [ "$dirty" -eq 0 ]; then
        log "Nothing to commit"
        echo "Nothing to commit — no changes since last checkpoint."
        return 0
    fi

    git add openclaw-docker/
    git commit -m "deploy: $MSG" \
        --author="OpenClaw <bot@openclaw.local>" 2>&1 | tee -a $LOG

    log "✅ Changes committed as new baseline"
    echo "✅ New baseline committed: '$MSG'"
}

# ── status ───────────────────────────────────────────────────────────────────
do_status() {
    echo "=== Deploy Cycle Status ==="
    echo ""
    cd "$GIT_ROOT"

    echo "--- Modified files (uncommitted) ---"
    git status --short openclaw-docker/ | grep -v "^?" || echo "  (none)"

    echo ""
    echo "--- Last 5 commits ---"
    git log --oneline -5 openclaw-docker/

    echo ""
    echo "--- Gateway health ---"
    if bash -c ">/dev/tcp/localhost/$GATEWAY_PORT" 2>/dev/null; then
        echo "  ✅ Port $GATEWAY_PORT is open (gateway healthy)"
    else
        echo "  ❌ Port $GATEWAY_PORT not responding"
    fi

    echo ""
    echo "--- Watchdog failure count ---"
    FAIL_FILE="$PROJECT_DIR/scripts/watchdog_failures"
    if [ -f "$FAIL_FILE" ]; then
        echo "  $(cat "$FAIL_FILE") recent failures"
    else
        echo "  0 (no failures file)"
    fi
}

# ── Dispatch ─────────────────────────────────────────────────────────────────
case "$CMD" in
    checkpoint) do_checkpoint ;;
    test)       do_test ;;
    rollback)   do_rollback ;;
    commit)     do_commit ;;
    status)     do_status ;;
    *)
        echo "Usage: $0 checkpoint|test|commit [message]|rollback|status"
        exit 1
        ;;
esac
