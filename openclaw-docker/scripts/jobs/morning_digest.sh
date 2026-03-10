#!/bin/bash
# morning_digest.sh — Unified Morning Digest for OpenClaw
# Collects data from multiple sources and sends one compact digest to Telegram

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Data directory for JSON files
DATA_DIR="/data/bot/openclaw-docker/data"
mkdir -p "$DATA_DIR"

# Portfolio tracker path
PORTFOLIO_TRACKER="/home/node/.openclaw/skills/crypto_monitor/portfolio_tracker.py"

# Create default JSON files if they don't exist
if [ ! -f "$DATA_DIR/crypto_radar.json" ]; then
    echo '{"status": "no_data", "message": "Crypto radar has not run yet", "timestamp": null}' > "$DATA_DIR/crypto_radar.json"
fi

if [ ! -f "$DATA_DIR/telegram_monitor.json" ]; then
    echo '{"status": "no_data", "message": "Telegram monitor has not run yet", "channels_checked": 0, "posts_found": 0}' > "$DATA_DIR/telegram_monitor.json"
fi

echo "=== 🌅 Morning Digest — $(date '+%Y-%m-%d %H:%M') ==="
echo ""

# ============================================
# SECTION 0: Crypto Portfolio (Live from Bybit)
# ============================================
echo "## 💰 Crypto Portfolio (Bybit)"
if command -v python3 &> /dev/null; then
    # Sync and get portfolio summary from Bybit
    portfolio_summary=$(python3 "$PORTFOLIO_TRACKER" sync 2>/dev/null && python3 "$PORTFOLIO_TRACKER" show 2>/dev/null || echo "  ⚠️ Failed to sync portfolio from Bybit")
    echo "$portfolio_summary"
else
    echo "  (Python3 not available)"
fi
echo ""

# ============================================
# SECTION 1: Crypto Radar
# ============================================
echo "## 🪙 Crypto Radar"
if [ -f "$DATA_DIR/crypto_radar.json" ]; then
    # Read and display crypto radar data
    crypto_status=$(cat "$DATA_DIR/crypto_radar.json" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    if data.get('status') == 'ok':
        print(f\"✅ Портфель: \${data.get('portfolio', {}).get('total_equity', 'N/A')}\")
        print(f\"📈 Рынок: BTC \${data.get('market', {}).get('btc', {}).get('price', 'N/A')} ({data.get('market', {}).get('btc', {}).get('change_24h', 'N/A')}%)\")
        print(f\"🎯 Сигнал: {data.get('signal', 'N/A')}\")
    else:
        print(f\"  ⚠️ {data.get('message', 'No data')}\")
except:
    print('  ⚠️ Failed to parse crypto data')
" 2>/dev/null || echo "  (Failed to read crypto data)")
    echo "$crypto_status"
else
    echo "  (Crypto radar data file not found)"
fi
echo ""

# ============================================
# SECTION 2: Telegram Monitor
# ============================================
echo "## 📱 Telegram Monitor"
if [ -f "$DATA_DIR/telegram_monitor.json" ]; then
    # Read and display telegram monitor data
    telegram_status=$(cat "$DATA_DIR/telegram_monitor.json" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    if data.get('status') == 'ok':
        print(f\"✅ Проверено каналов: {data.get('channels_checked', 0)}\")
        print(f\"📄 Найдено постов: {data.get('posts_found', 0)}\")
        digest_file = data.get('digest_file', 'N/A')
        print(f\"📄 Полный дайджест: {digest_file}\")
    else:
        print(f\"  ⚠️ {data.get('message', 'No data')}\")
except:
    print('  ⚠️ Failed to parse telegram data')
" 2>/dev/null || echo "  (Failed to read telegram data)")
    echo "$telegram_status"
else
    echo "  (Telegram monitor data file not found)"
fi
echo ""

# ============================================
# SECTION 3: System Status
# ============================================
echo "## 🖥️ System Status"
echo "### Docker Containers"
docker ps --format 'table {{.Names}}\t{{.Status}}' 2>/dev/null | head -n 5 || echo "  (Docker unavailable)"
echo ""
echo "### Disk Usage"
disk_info=$(df -h / 2>/dev/null | tail -n 1 | awk '{print "  Used: " $3 " / " $2 " (" $5 " used)"}' || echo "  (Disk info unavailable)")
echo "$disk_info"
echo ""

# ============================================
# SECTION 4: Inbox Router
# ============================================
echo "## 📬 Inbox Router"
VAULT_PATH="${USER_VAULT_PATH:-/data/obsidian/vault}"
if [ -d "$VAULT_PATH" ]; then
    # Count pending tasks (unchecked items)
    PENDING_COUNT=$(grep -r '\- \[ \]' "$VAULT_PATH" --include='*.md' 2>/dev/null | wc -l | tr -d ' ')
    # Count files in Inbox folder
    INBOX_COUNT=$(find "$VAULT_PATH/Inbox" -name '*.md' 2>/dev/null | wc -l | tr -d ' ')
    echo "  Pending tasks: $PENDING_COUNT"
    echo "  Files in Inbox: $INBOX_COUNT"
else
    echo "  (Vault path not found: $VAULT_PATH)"
fi
echo ""

# ============================================
# SECTION 5: Skill Researcher (last night's run)
# ============================================
echo "## 🔬 Skill Researcher"
RESEARCHER_STATE="/data/bot/openclaw-docker/scripts/skill_researcher_state.json"
if [ -f "$RESEARCHER_STATE" ]; then
    python3 - <<'PYEOF'
import json, os, datetime
path = "/data/bot/openclaw-docker/scripts/skill_researcher_state.json"
try:
    data = json.load(open(path))
    last_run = data.get("last_run")
    processed = data.get("processed", {})
    if last_run:
        ts = datetime.datetime.fromisoformat(last_run)
        print(f"  Last run: {ts.strftime('%Y-%m-%d %H:%M')}")
    # count improved (files processed in last 24h)
    cutoff = datetime.datetime.now().timestamp() - 86400
    recent = [(k, v) for k, v in processed.items() if v > cutoff]
    if recent:
        print(f"  Processed last 24h: {len(recent)} scripts")
        for path_str, ts_val in sorted(recent, key=lambda x: x[1], reverse=True)[:5]:
            rel = path_str.split("skills/")[-1] if "skills/" in path_str else path_str
            print(f"    • {rel}")
    else:
        print("  No scripts processed in last 24h")
except Exception as e:
    print(f"  (Could not read state: {e})")
PYEOF
else
    echo "  (Skill researcher has not run yet)"
fi
echo ""

# ============================================
# SECTION 6: Calendar & Today's Plan
# ============================================
echo "## 📅 Today's Calendar"
if [ -f "/home/node/.openclaw/shared/google_token.json" ]; then
    bash /data/bot/openclaw-docker/scripts/gcal.sh today 2>/dev/null || echo "  (Calendar unavailable)"
else
    echo "  (Google not authorized)"
fi
echo ""

# ============================================
# SUMMARY
# ============================================
echo "---"
echo "*Morning Digest complete*"
