#!/bin/bash
# Vikunja API CLI
# Usage: bash /data/bot/openclaw-docker/skills/vikunja/vikunja.sh <command> [args...]
#
# Patterns: Based on ryot.sh and gcal.sh API wrappers

set -e

# Configuration
VIKUNJA_URL="${VIKUNJA_URL:-http://vikunja:3456/api/v1}"
VIKUNJA_TOKEN="${VIKUNJA_TOKEN:-}"

if [ -z "$VIKUNJA_TOKEN" ]; then
    echo "Error: VIKUNJA_TOKEN environment variable is not set"
    exit 1
fi

# Headers
HEADERS=(-H "Authorization: Bearer $VIKUNJA_TOKEN" -H "Content-Type: application/json")

# ── Caching (pattern from gcal.sh/ryot.sh) ─────────────────────────────────────
CACHE_DIR="/tmp/vikunja_cache"
CACHE_TTL=300  # 5 minutes

mkdir -p "$CACHE_DIR" 2>/dev/null || true

get_cache() {
    local key="$1"
    local cache_file="$CACHE_DIR/$key.json"
    if [ -f "$cache_file" ]; then
        local age=$(($(date +%s) - $(stat -f %m "$cache_file" 2>/dev/null || stat -c %Y "$cache_file" 2>/dev/null || echo 0)))
        if [ "$age" -lt "$CACHE_TTL" ]; then
            cat "$cache_file"
            return 0
        fi
    fi
    return 1
}

set_cache() {
    local key="$1"
    local data="$2"
    echo "$data" > "$CACHE_DIR/$key.json"
}

clear_cache() {
    rm -f "$CACHE_DIR"/*.json 2>/dev/null || true
}

# ── Unified API call (pattern from gcal.sh) ─────────────────────────────────────
vikunja_api() {
    local method="${1:-GET}"
    local endpoint="$2"
    local data="$3"
    
    local curl_cmd="curl -s -X $method ${HEADERS[@]}"
    if [ -n "$data" ]; then
        curl_cmd="$curl_cmd -d '$data'"
    fi
    
    eval "$curl_cmd" "$VIKUNJA_URL/$endpoint"
}

vikunja_api_cached() {
    local key="$1"
    local method="${2:-GET}"
    local endpoint="$3"
    local data="$4"
    
    # Try cache first (only for GET)
    if [ "$method" = "GET" ]; then
        local cached
        if cached=$(get_cache "$key"); then
            echo "$cached"
            return 0
        fi
    fi
    
    # API call
    local result
    result=$(vikunja_api "$method" "$endpoint" "$data")
    
    # Cache result (only for GET)
    if [ "$method" = "GET" ]; then
        set_cache "$key" "$result"
    fi
    
    echo "$result"
}

# ── Commands ─────────────────────────────────────────────────────────────────────
case "$1" in
    list)
        # List all tasks
        curl -s "${HEADERS[@]}" "$VIKUNJA_URL/tasks" | jq '.[] | {id, title, description, done, due_date, priority, project_id}'
        ;;
    list-by-project)
        # List tasks by project ID
        PROJECT_ID="$2"
        if [ -z "$PROJECT_ID" ]; then
            echo "Usage: vikunja.sh list-by-project <project_id>"
            exit 1
        fi
        curl -s "${HEADERS[@]}" "$VIKUNJA_URL/projects/$PROJECT_ID/tasks" | jq '.[] | {id, title, description, done, due_date, priority}'
        ;;
    get)
        # Get task details
        TASK_ID="$2"
        if [ -z "$TASK_ID" ]; then
            echo "Usage: vikunja.sh get <task_id>"
            exit 1
        fi
        curl -s "${HEADERS[@]}" "$VIKUNJA_URL/tasks/$TASK_ID" | jq '.'
        ;;
    create)
        # Create a new task: create "title" ["description"] ["due_date"] [priority]
        TITLE="$2"
        if [ -z "$TITLE" ]; then
            echo "Usage: vikunja.sh create \"title\" [\"description\"] [\"due_date\"] [priority]"
            exit 1
        fi
        
        DESCRIPTION="${3:-}"
        DUE_DATE="${4:-}"
        PRIORITY="${5:-2}"
        
        # Discover first project if not specified (default to 1)
        PROJECT_ID=$(curl -s "${HEADERS[@]}" "$VIKUNJA_URL/projects" | jq '.[0].id // 1')
        
        # Build JSON payload
        JSON="{\"title\": \"$TITLE\""
        if [ -n "$DESCRIPTION" ]; then
            JSON="$JSON, \"description\": \"$DESCRIPTION\""
        fi
        if [ -n "$DUE_DATE" ]; then
            JSON="$JSON, \"due_date\": \"$DUE_DATE\""
        fi
        JSON="$JSON, \"priority\": $PRIORITY}"
        
        # Latest Vikunja uses PUT to project/id/tasks for creation
        RESULT=$(curl -s -X PUT "${HEADERS[@]}" -d "$JSON" "$VIKUNJA_URL/projects/$PROJECT_ID/tasks")
        echo "$RESULT" | jq '.'
        ;;
    update)
        # Update a task: update <task_id> ["title"] ["description"]
        TASK_ID="$2"
        if [ -z "$TASK_ID" ]; then
            echo "Usage: vikunja.sh update <task_id> [\"title\"] [\"description\"]"
            exit 1
        fi
        
        NEW_TITLE="$3"
        NEW_DESCRIPTION="$4"
        
        # Build JSON payload
        JSON="{"
        FIRST=true
        if [ -n "$NEW_TITLE" ]; then
            JSON="$JSON\"title\": \"$NEW_TITLE\""
            FIRST=false
        fi
        if [ -n "$NEW_DESCRIPTION" ]; then
            if [ "$FIRST" = false ]; then JSON="$JSON, "; fi
            JSON="$JSON\"description\": \"$NEW_DESCRIPTION\""
            FIRST=false
        fi
        JSON="$JSON}"
        
        if [ "$JSON" = "{}" ]; then
            echo "Error: Nothing to update. Provide title or description."
            exit 1
        fi
        
        RESULT=$(curl -s -X POST "${HEADERS[@]}" -d "$JSON" "$VIKUNJA_URL/tasks/$TASK_ID")
        echo "$RESULT" | jq '.'
        ;;
    done)
        # Mark task as done
        TASK_ID="$2"
        if [ -z "$TASK_ID" ]; then
            echo "Usage: vikunja.sh done <task_id>"
            exit 1
        fi
        # Vikunja update done status is usually via POST to /tasks/id with {"done": true} 
        # but there is also a specific endpoint sometimes. Let's use the most standard one.
        RESULT=$(curl -s -X POST "${HEADERS[@]}" -d '{"done": true}' "$VIKUNJA_URL/tasks/$TASK_ID")
        echo "$RESULT" | jq '.'
        ;;
    delete)
        # Delete a task
        TASK_ID="$2"
        if [ -z "$TASK_ID" ]; then
            echo "Usage: vikunja.sh delete <task_id>"
            exit 1
        fi
        curl -s -X DELETE "${HEADERS[@]}" "$VIKUNJA_URL/tasks/$TASK_ID"
        echo "Task $TASK_ID deleted"
        ;;
    projects)
        # List all projects
        curl -s "${HEADERS[@]}" "$VIKUNJA_URL/projects" | jq '.[] | {id, title, description}'
        ;;
    create-project)
        # Create a new project: create-project "title" ["description"]
        TITLE="$2"
        if [ -z "$TITLE" ]; then
            echo "Usage: vikunja.sh create-project \"title\" [\"description\"]"
            exit 1
        fi
        
        DESCRIPTION="${3:-}"
        
        if [ -n "$DESCRIPTION" ]; then
            JSON="{\"title\": \"$TITLE\", \"description\": \"$DESCRIPTION\"}"
        else
            JSON="{\"title\": \"$TITLE\"}"
        fi
        
        RESULT=$(curl -s -X PUT "${HEADERS[@]}" -d "$JSON" "$VIKUNJA_URL/projects")
        echo "$RESULT" | jq '.'
        ;;
    status)
        # Check API status and token
        echo "Vikunja URL: $VIKUNJA_URL"
        echo "Token: ${VIKUNJA_TOKEN:0:10}..."
        USER_INFO=$(curl -s "${HEADERS[@]}" "$VIKUNJA_URL/user" 2>/dev/null || echo '{"error": "Failed to connect"}')
        echo "User info:"
        echo "$USER_INFO" | jq '.' 2>/dev/null || echo "$USER_INFO"
        ;;
    
    # ── NEW: Create task for specific project ─────────────────────────────────────
    create-for-project)
        # Create task for specific project: create-for-project <project_id> "title" "description" "due_date" priority
        PROJECT_ID="$2"
        TITLE="$3"
        DESCRIPTION="${4:-}"
        DUE_DATE="${5:-}"
        PRIORITY="${6:-2}"
        
        if [ -z "$PROJECT_ID" ] || [ -z "$TITLE" ]; then
            echo "Usage: vikunja.sh create-for-project <project_id> \"title\" [\"description\"] [\"due_date\"] [priority]"
            exit 1
        fi
        
        # Build JSON payload
        JSON="{\"title\": \"$TITLE\""
        if [ -n "$DESCRIPTION" ]; then
            JSON="$JSON, \"description\": \"$DESCRIPTION\""
        fi
        if [ -n "$DUE_DATE" ]; then
            JSON="$JSON, \"due_date\": \"$DUE_DATE\""
        fi
        JSON="$JSON, \"priority\": $PRIORITY}"
        
        RESULT=$(curl -s -X PUT "${HEADERS[@]}" -d "$JSON" "$VIKUNJA_URL/projects/$PROJECT_ID/tasks")
        echo "$RESULT" | jq '.'
        # Clear projects cache
        clear_cache
        ;;
    
    # ── NEW: List tasks by status (done/undone) ─────────────────────────────────────
    list-by-status)
        # List tasks by status: list-by-status <done|undone>
        STATUS="$2"
        if [ -z "$STATUS" ]; then
            echo "Usage: vikunja.sh list-by-status <done|undone>"
            exit 1
        fi
        
        if [ "$STATUS" = "done" ]; then
            DONE_FILTER="true"
        else
            DONE_FILTER="false"
        fi
        
        # Vikunja API supports filtering via query params
        curl -s "${HEADERS[@]}" "$VIKUNJA_URL/tasks?done=$DONE_FILTER" | jq '.[] | {id, title, description, done, due_date, priority, project_id}'
        ;;
    
    # ── NEW: List overdue tasks ─────────────────────────────────────
    list-overdue)
        # List tasks that are past due date and not done
        TODAY=$(date +%Y-%m-%d)
        curl -s "${HEADERS[@]}" "$VIKUNJA_URL/tasks?done=false" | jq --arg today "$TODAY" '
            .[] | select(.due_date != null and .due_date < $today) | {id, title, description, due_date, priority, project_id}'
        ;;
    
    # ── NEW: Quick create bug task ─────────────────────────────────────
    create-bug)
        # Create bug task: create-bug "title" "description" "due_date"
        TITLE="$2"
        DESCRIPTION="${3:-}"
        DUE_DATE="${4:-}"
        
        if [ -z "$TITLE" ]; then
            echo "Usage: vikunja.sh create-bug \"title\" [\"description\"] [\"due_date\"]"
            exit 1
        fi
        
        # Default to first project, priority 3 (high)
        PROJECT_ID=$(curl -s "${HEADERS[@]}" "$VIKUNJA_URL/projects" | jq '.[0].id // 1')
        
        JSON="{\"title\": \"[BUG] $TITLE\""
        if [ -n "$DESCRIPTION" ]; then
            JSON="$JSON, \"description\": \"$DESCRIPTION\""
        fi
        if [ -n "$DUE_DATE" ]; then
            JSON="$JSON, \"due_date\": \"$DUE_DATE\""
        fi
        JSON="$JSON, \"priority\": 3}"
        
        RESULT=$(curl -s -X PUT "${HEADERS[@]}" -d "$JSON" "$VIKUNJA_URL/projects/$PROJECT_ID/tasks")
        echo "$RESULT" | jq '.'
        ;;
    
    # ── NEW: Quick create improvement task ─────────────────────────────────────
    create-improvement)
        # Create improvement task: create-improvement "title" "description" "due_date"
        TITLE="$2"
        DESCRIPTION="${3:-}"
        DUE_DATE="${4:-}"
        
        if [ -z "$TITLE" ]; then
            echo "Usage: vikunja.sh create-improvement \"title\" [\"description\"] [\"due_date\"]"
            exit 1
        fi
        
        PROJECT_ID=$(curl -s "${HEADERS[@]}" "$VIKUNJA_URL/projects" | jq '.[0].id // 1')
        
        JSON="{\"title\": \"[IMPROVE] $TITLE\""
        if [ -n "$DESCRIPTION" ]; then
            JSON="$JSON, \"description\": \"$DESCRIPTION\""
        fi
        if [ -n "$DUE_DATE" ]; then
            JSON="$JSON, \"due_date\": \"$DUE_DATE\""
        fi
        JSON="$JSON, \"priority\": 2}"
        
        RESULT=$(curl -s -X PUT "${HEADERS[@]}" -d "$JSON" "$VIKUNJA_URL/projects/$PROJECT_ID/tasks")
        echo "$RESULT" | jq '.'
        ;;
    
    # ── NEW: Quick create discovery task ─────────────────────────────────────
    create-discovery)
        # Create discovery task: create-discovery "title" "description" "due_date"
        TITLE="$2"
        DESCRIPTION="${3:-}"
        DUE_DATE="${4:-}"
        
        if [ -z "$TITLE" ]; then
            echo "Usage: vikunja.sh create-discovery \"title\" [\"description\"] [\"due_date\"]"
            exit 1
        fi
        
        PROJECT_ID=$(curl -s "${HEADERS[@]}" "$VIKUNJA_URL/projects" | jq '.[0].id // 1')
        
        JSON="{\"title\": \"[IDEA] $TITLE\""
        if [ -n "$DESCRIPTION" ]; then
            JSON="$JSON, \"description\": \"$DESCRIPTION\""
        fi
        if [ -n "$DUE_DATE" ]; then
            JSON="$JSON, \"due_date\": \"$DUE_DATE\""
        fi
        JSON="$JSON, \"priority\": 1}"
        
        RESULT=$(curl -s -X PUT "${HEADERS[@]}" -d "$JSON" "$VIKUNJA_URL/projects/$PROJECT_ID/tasks")
        echo "$RESULT" | jq '.'
        ;;
    
    # ── NEW: Weekly report helper ─────────────────────────────────────
    weekly-report)
        # Generate weekly report from all projects
        echo "=== OPENCLAW BOT PROJECT ==="
        curl -s "${HEADERS[@]}" "$VIKUNJA_URL/projects" | jq '.[] | select(.title | contains("OpenClaw")) | .id' | while read -r proj_id; do
            echo "Project ID: $proj_id"
            curl -s "${HEADERS[@]}" "$VIKUNJA_URL/projects/$proj_id/tasks" | jq '.[] | select(.done == false) | {id, title, priority, due_date}'
        done
        echo ""
        echo "=== PERSONAL PROJECT ==="
        curl -s "${HEADERS[@]}" "$VIKUNJA_URL/projects" | jq '.[] | select(.title | contains("Personal")) | .id' | while read -r proj_id; do
            echo "Project ID: $proj_id"
            curl -s "${HEADERS[@]}" "$VIKUNJA_URL/projects/$proj_id/tasks" | jq '.[] | select(.done == false) | {id, title, priority, due_date}'
        done
        ;;
    
    # ── NEW: Clear cache ─────────────────────────────────────
    clear-cache)
        clear_cache
        echo "Cache cleared"
        ;;
    
    *)
        echo "Vikunja CLI - Task Management"
        echo ""
        echo "Usage: vikunja.sh <command> [args...]"
        echo ""
        echo "Commands:"
        echo "  list                          List all tasks"
        echo "  list-by-project <id>         List tasks in a project"
        echo "  get <task_id>                 Get task details"
        echo "  create \"title\" [desc] [date] [pri]  Create new task"
        echo "  create-for-project <id> \"title\" [desc] [date] [pri]  Create for project"
        echo "  create-bug \"title\" [desc] [date]     Create bug task (priority=3)"
        echo "  create-improvement \"title\" [desc] [date]  Create improvement (priority=2)"
        echo "  create-discovery \"title\" [desc] [date]    Create idea (priority=1)"
        echo "  update <id> [title] [desc]   Update a task"
        echo "  done <task_id>               Mark task as done"
        echo "  delete <task_id>             Delete a task"
        echo "  list-by-status <done|undone> List tasks by status"
        echo "  list-overdue                 List overdue tasks"
        echo "  weekly-report                Generate weekly report"
        echo "  projects                      List all projects"
        echo "  create-project \"title\" [desc] Create new project"
        echo "  status                        Check API status"
        echo "  clear-cache                   Clear API cache"
        echo ""
        echo "Priority: 1=low, 2=medium, 3=high"
        echo "Date format: YYYY-MM-DD"
        echo ""
        echo "Cache: /tmp/vikunja_cache (TTL: 5 min)"
        exit 1
        ;;
esac
