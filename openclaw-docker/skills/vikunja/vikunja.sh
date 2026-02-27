#!/bin/bash
# Vikunja API CLI
# Usage: bash /data/bot/openclaw-docker/skills/vikunja/vikunja.sh <command> [args...]

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

# Commands
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
        echo "  update <id> [title] [desc]   Update a task"
        echo "  done <task_id>               Mark task as done"
        echo "  delete <task_id>             Delete a task"
        echo "  projects                      List all projects"
        echo "  create-project \"title\" [desc] Create new project"
        echo "  status                        Check API status"
        echo ""
        echo "Priority: 1=low, 2=medium, 3=high"
        echo "Date format: YYYY-MM-DD"
        exit 1
        ;;
esac
