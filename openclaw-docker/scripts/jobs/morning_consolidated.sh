#!/bin/bash
# Morning Consolidated Report
# Replaces: morning_briefing + crypto_daily_report + task_briefing
# Reads from: Obsidian Tasks, Bybit, Docker, Reddit
# Saves to: Bot/DailyReports/MORNING-YYYY-MM-DD.md
# Sends: ONE Telegram message with WebApp button

set -e

NOTIFY_SCRIPT="/data/bot/openclaw-docker/skills/telegram/notify.py"
TELEGRAM_CHAT="6053956251"
VAULT_PATH="${USER_VAULT_PATH:-/data/obsidian/vault}"
OBSIDIAN_TASKS="/data/bot/openclaw-docker/skills/obsidian_tasks/obsidian_tasks.py"
REPORTS_DIR="$VAULT_PATH/Bot/DailyReports"
TODAY=$(date '+%Y-%m-%d')
TODAY_DISPLAY=$(date '+%d %b')
TIMESTAMP=$(date '+%H:%M')

mkdir -p "$REPORTS_DIR"

echo "[$(date)] Morning consolidated report starting..."

# ── 1. Collect task counts ────────────────────────────────────────────────
TASK_COUNTS=$(python3 "$OBSIDIAN_TASKS" count-by-folder 2>/dev/null || echo "error")
BOT_COUNT=$(echo "$TASK_COUNTS" | grep -oP 'bot: \K\d+' || echo "?")
WORK_COUNT=$(echo "$TASK_COUNTS" | grep -oP 'work: \K\d+' || echo "?")
PERSONAL_COUNT=$(echo "$TASK_COUNTS" | grep -oP 'personal: \K\d+' || echo "?")
TOTAL_COUNT=$(echo "$TASK_COUNTS" | grep -oP 'total: \K\d+' || echo "?")

# Overdue
OVERDUE=$(python3 "$OBSIDIAN_TASKS" list-overdue 2>/dev/null)
OVERDUE_COUNT=$(echo "$OVERDUE" | grep -c "\- \[" || echo "0")

# ── 2. Collect crypto data ───────────────────────────────────────────────
CRYPTO_DATA=""
CRYPTO_PRICE_BTC=""
CRYPTO_PRICE_ETH=""
BTC_CHG=""
ETH_CHG=""

# Bybit portfolio
BYBIT_OUT=$(python3 ~/.openclaw/skills/crypto_assistant/bybit_read.py --json 2>/dev/null | head -200 || echo "{}")
if [ -n "$BYBIT_OUT" ] && [ "$BYBIT_OUT" != "{}" ]; then
    TOTAL_BALANCE=$(echo "$BYBIT_OUT" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('total_balance_usd', d.get('total', 'N/A')))" 2>/dev/null || echo "N/A")
    BTC_BALANCE=$(echo "$BYBIT_OUT" | python3 -c "import json,sys; d=json.load(sys.stdin); pos=d.get('positions',[]); [print(p.get('size',0)) for p in pos if p.get('symbol','').startswith('BTC')]" 2>/dev/null | head -1 || echo "")
    CRYPTO_DATA="Portfolio: ~${TOTAL_BALANCE} USD"
fi

# Quick price check via CoinGecko free API
PRICE_DATA=$(curl -s --max-time 10 "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum&vs_currencies=usd&include_24hr_change=true" 2>/dev/null || echo "{}")
if [ -n "$PRICE_DATA" ] && echo "$PRICE_DATA" | python3 -c "import json,sys; json.load(sys.stdin)" 2>/dev/null; then
    BTC_PRICE=$(echo "$PRICE_DATA" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('bitcoin',{}).get('usd','?'))" 2>/dev/null)
    BTC_CHG=$(echo "$PRICE_DATA" | python3 -c "import json,sys; d=json.load(sys.stdin); chg=d.get('bitcoin',{}).get('usd_24h_change',0); print(f'{chg:+.2f}')" 2>/dev/null)
    ETH_PRICE=$(echo "$PRICE_DATA" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('ethereum',{}).get('usd','?'))" 2>/dev/null)
    ETH_CHG=$(echo "$PRICE_DATA" | python3 -c "import json,sys; d=json.load(sys.stdin); chg=d.get('ethereum',{}).get('usd_24h_change',0); print(f'{chg:+.2f}')" 2>/dev/null)
fi

# ── 3. Docker system status ──────────────────────────────────────────────
CONTAINER_COUNT=$(docker ps --format '{{.Names}}' 2>/dev/null | wc -l || echo "?")
UNHEALTHY=$(docker ps --format '{{.Names}} ({{.Status}})' --filter "status=running" 2>/dev/null | grep -v "Up" | wc -l || echo "0")
DOCKER_STATUS="✅ $CONTAINER_COUNT"
if [ "$UNHEALTHY" -gt 0 ]; then
    DOCKER_STATUS="⚠️ $CONTAINER_COUNT ($UNHEALTHY проблемы)"
fi

# ── 4. Compose full report markdown ─────────────────────────────────────
cat > "$REPORTS_DIR/MORNING-$TODAY.md" << REPORT
# 🌅 Morning Report — $TODAY_DISPLAY $TIMESTAMP

> Automated. Source: Obsidian Tasks, Bybit, Docker.

## 💰 Crypto

| Asset | Price | 24h |
|-------|-------|-----|
| BTC | \$${BTC_PRICE:-?} | ${BTC_CHG:-?}% |
| ETH | \$${ETH_PRICE:-?} | ${ETH_CHG:-?}% |

$([ -n "$CRYPTO_DATA" ] && echo "| $CRYPTO_DATA |" || echo "")

## 📋 Tasks

| Category | Pending |
|----------|---------|
| 🤖 Bot | $BOT_COUNT |
| 💼 Work | $WORK_COUNT |
| 🏠 Personal | $PERSONAL_COUNT |
| **Total** | **$TOTAL_COUNT** |

$([ "$OVERDUE_COUNT" -gt 0 ] && echo "⚠️ **Overdue: $OVERDUE_COUNT tasks**" || echo "✅ No overdue tasks")

## 🐳 System

- Containers: $CONTAINER_COUNT running
$([ "$UNHEALTHY" -gt 0 ] && echo "- ⚠️ $UNHEALTHY containers need attention" || echo "- ✅ All containers healthy")

## 🗓️ Priorities Today

$([ "$TOTAL_COUNT" -gt 0 ] && echo "- Review Bot/Tasks/Tasks-Dashboard.md for today's tasks" || echo "- No pending tasks — enjoy your day!")
$([ "$OVERDUE_COUNT" -gt 0 ] && echo "- ⚠️ Address $OVERDUE_COUNT overdue tasks first")

---

_Generated: $(date '+%Y-%m-%d %H:%M:%S UTC')_
_Tasks: Bot/Tasks/bot-tasks.md · Dashboard: Bot/Tasks/Tasks-Dashboard.md_
REPORT

echo "[$(date)] Report saved to $REPORTS_DIR/MORNING-$TODAY.md"

# ── 5. Send ONE Telegram message ─────────────────────────────────────────
WEBAPP_URL="https://vault.volamoks.store/report/MORNING-$TODAY"
TELEGRAM_MSG="🌅 Good morning — $TODAY_DISPLAY

💰 BTC \$${BTC_PRICE:-?} (${BTC_CHG:-?}) | ETH \$${ETH_PRICE:-?} (${ETH_CHG:-?})
📊 ${CRYPTO_DATA:-Portfolio: —}
📋 Tasks: $TOTAL_COUNT (🤖 $BOT_COUNT | 💼 $WORK_COUNT | 🏠 $PERSONAL_COUNT)
🐳 Containers: $DOCKER_STATUS"

if [ "$OVERDUE_COUNT" -gt 0 ]; then
    TELEGRAM_MSG+="
⚠️ $OVERDUE_COUNT overdue"
fi

# Send via notify.py (supports WebApp button)
python3 "$NOTIFY_SCRIPT" "$TELEGRAM_MSG" \
    --chat-id "$TELEGRAM_CHAT" \
    --webapp-url "$WEBAPP_URL" \
    --webapp-text "📊 Full Report" \
    2>/dev/null || {
    # Fallback: send without WebApp
    python3 "$NOTIFY_SCRIPT" "$TELEGRAM_MSG" --chat-id "$TELEGRAM_CHAT" 2>/dev/null || true
}

echo "[$(date)] Telegram message sent"
echo "[$(date)] Morning consolidated report complete"
exit 0
