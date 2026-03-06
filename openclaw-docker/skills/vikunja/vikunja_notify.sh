#!/bin/bash
# Vikunja + Telegram Integration using unified notify.py module
# Sends Vikunja notifications with inline keyboard buttons

set -e

VIKUNJA_URL="${VIKUNJA_URL:-http://localhost:3456/api/v1}"
VIKUNJA_TOKEN="${VIKUNJA_TOKEN:-}"
TELEGRAM_CHAT_ID="${TELEGRAM_CHAT_ID:-$TELEGRAM_CHAT_ID_ABROR}"

if [ -z "$VIKUNJA_TOKEN" ]; then
    echo "Error: VIKUNJA_TOKEN environment variable is not set"
    exit 1
fi

if [ -z "$TELEGRAM_BOT_TOKEN" ]; then
    echo "Error: TELEGRAM_BOT_TOKEN environment variable is not set"
    exit 1
fi

HEADERS=(-H "Authorization: Bearer $VIKUNJA_TOKEN" -H "Content-Type: application/json")
NOTIFY_SCRIPT="/data/bot/openclaw-docker/skills/telegram/notify.py"

# Send task notification with buttons
send-task-notification() {
    local TASK_ID="$1"
    
    # Get task details from Vikunja
    local TASK
    TASK=$(curl -s "${HEADERS[@]}" "$VIKUNJA_URL/tasks/$TASK_ID")
    
    if [ -z "$TASK" ] || echo "$TASK" | jq -e '.id == null' > /dev/null 2>&1; then
        echo "Error: Task #$TASK_ID not found"
        exit 1
    fi
    
    local TITLE DESC PRIORITY PRIO_TEXT
    TITLE=$(echo "$TASK" | jq -r '.title')
    DESC=$(echo "$TASK" | jq -r '.description // "No description"')
    PRIORITY=$(echo "$TASK" | jq -r '.priority // 1')
    
    # Map priority to emoji
    case $PRIORITY in
        3) PRIO_TEXT="🔴 HIGH" ;;
        2) PRIO_TEXT="🟡 MEDIUM" ;;
        *) PRIO_TEXT="🟢 LOW" ;;
    esac
    
    # Build message
    local MSG
    MSG="🔧 **Task #$TASK_ID**

**Title:** $TITLE
**Priority:** $PRIO_TEXT

**Description:**
$DESC"
    
    # Buttons: Apply, Show Details, Skip, Mark Done
    local BUTTONS
    BUTTONS="✅ Apply:apply:$TASK_ID,📋 Details:show:$TASK_ID|⏭️ Skip:skip:$TASK_ID,✅ Done:vikunja:done:$TASK_ID"
    
    # Send via notify.py
    python3 "$NOTIFY_SCRIPT" "$MSG" \
        --chat-id "$TELEGRAM_CHAT_ID" \
        --buttons "$BUTTONS"
    
    echo "Notification sent for task #$TASK_ID"
}

# Send weekly report with task list
send-weekly-report() {
    echo "📋 Weekly Vikunja Report — $(date +%d.%m.%Y)"
    echo ""
    
    # Get OpenClaw project ID
    local PROJECTS
    PROJECTS=$(curl -s "${HEADERS[@]}" "$VIKUNJA_URL/projects")
    local PROJECT_ID
    PROJECT_ID=$(echo "$PROJECTS" | jq -r '.[] | select(.title | contains("OpenClaw")) | .id' | head -1)
    
    if [ -z "$PROJECT_ID" ]; then
        echo "Error: OpenClaw project not found"
        exit 1
    fi
    
    # Get tasks
    local TASKS
    TASKS=$(curl -s "${HEADERS[@]}" "$VIKUNJA_URL/projects/$PROJECT_ID/tasks")
    
    # Count by status and type
    local TOTAL OPEN DONE
    TOTAL=$(echo "$TASKS" | jq '. | length')
    OPEN=$(echo "$TASKS" | jq '[.[] | select(.done == false)] | length')
    DONE=$(echo "$TASKS" | jq '[.[] | select(.done == true)] | length')
    
    local BUGS IMPROVE IDEAS CONFIGS
    BUGS=$(echo "$TASKS" | jq '[.[] | select(.title | contains("[BUG]"))] | length')
    IMPROVE=$(echo "$TASKS" | jq '[.[] | select(.title | contains("[IMPROVE]"))] | length')
    IDEAS=$(echo "$TASKS" | jq '[.[] | select(.title | contains("[IDEA]"))] | length')
    CONFIGS=$(echo "$TASKS" | jq '[.[] | select(.title | contains("[CONFIG]"))] | length')
    
    # Build report
    local MSG
    MSG="📊 **Weekly Vikunja Report**
📅 $(date +%d.%m.%Y)

**Summary:**
• Total: $TOTAL
• Open: $OPEN
• Done: $DONE

**By Type:**
• 🐛 Bugs: $BUGS
• 🔧 Improvements: $IMPROVE
• 💡 Ideas: $IDEAS
• ⚙️ Config: $CONFIGS"
    
    # Get overdue tasks
    local OVERDUE
    OVERDUE=$(echo "$TASKS" | jq -r '[.[] | select(.done == false and .end < now)] | length')
    
    if [ "$OVERDUE" -gt 0 ]; then
        MSG="$MSG

⚠️ **Overdue:** $OVERDUE tasks"
    fi
    
    # Build buttons for top priority tasks
    local BUTTONS=""
    local HIGH_PRIORITY_TASKS
    HIGH_PRIORITY_TASKS=$(echo "$TASKS" | jq -r '[.[] | select(.done == false and .priority == 3)] | .[:5] | .[].id' | tr '\n' ',' | sed 's/,$//')
    
    if [ -n "$HIGH_PRIORITY_TASKS" ]; then
        # Add buttons for first high priority task
        local FIRST_TASK
        FIRST_TASK=$(echo "$HIGH_PRIORITY_TASKS" | cut -d',' -f1)
        BUTTONS="🔥 Review #$FIRST_TASK:apply:$FIRST_TASK"
    fi
    
    BUTTONS="$BUTTONS|📋 Full List:vikunja:list,✅ Done Review:skip:all"
    
    # Send notification
    python3 "$NOTIFY_SCRIPT" "$MSG" \
        --chat-id "$TELEGRAM_CHAT_ID" \
        --buttons "$BUTTONS"
    
    echo "Weekly report sent"
}

# Send task creation confirmation
send-task-created() {
    local TASK_ID="$1"
    local TASK_TYPE="$2"  # BUG, IMPROVE, IDEA, CONFIG
    local TITLE="$3"
    
    # Map type to emoji
    local EMOJI
    case $TASK_TYPE in
        BUG) EMOJI="🐛" ;;
        IMPROVE) EMOJI="🔧" ;;
        IDEA) EMOJI="💡" ;;
        CONFIG) EMOJI="⚙️" ;;
        *) EMOJI="📋" ;;
    esac
    
    local MSG
    MSG="$EMOJI **Task Created #$TASK_ID**

$TITLE

Task added to Vikunja OpenClaw Bot project."
    
    local BUTTONS
    BUTTONS="📋 View:show:$TASK_ID,✅ Done:vikunja:done:$TASK_ID|🗑️ Delete:vikunja:delete:$TASK_ID"
    
    python3 "$NOTIFY_SCRIPT" "$MSG" \
        --chat-id "$TELEGRAM_CHAT_ID" \
        --buttons "$BUTTONS"
    
    echo "Task creation notification sent"
}

# Main command router
case "$1" in
    send-task-notification)
        if [ -z "$2" ]; then
            echo "Usage: vikunja_notify.sh send-task-notification <task_id>"
            exit 1
        fi
        send-task-notification "$2"
        ;;
    send-weekly-report)
        send-weekly-report
        ;;
    send-task-created)
        if [ -z "$2" ] || [ -z "$3" ] || [ -z "$4" ]; then
            echo "Usage: vikunja_notify.sh send-task-created <task_id> <type> <title>"
            exit 1
        fi
        send-task-created "$2" "$3" "$4"
        ;;
    *)
        echo "Vikunja + Telegram Notification (using unified notify.py)"
        echo ""
        echo "Usage: vikunja_notify.sh <command> [args...]"
        echo ""
        echo "Commands:"
        echo "  send-task-notification <id>     Send notification for specific task"
        echo "  send-weekly-report              Send weekly summary report"
        echo "  send-task-created <id> <type> <title>  Send task creation confirmation"
        echo ""
        echo "Environment:"
        echo "  VIKUNJA_URL         Vikunja API URL (default: http://localhost:3456/api/v1)"
        echo "  VIKUNJA_TOKEN       Vikunja API token (required)"
        echo "  TELEGRAM_BOT_TOKEN  Telegram bot token (required)"
        echo "  TELEGRAM_CHAT_ID    Target chat ID"
        echo ""
        exit 1
        ;;
esac
