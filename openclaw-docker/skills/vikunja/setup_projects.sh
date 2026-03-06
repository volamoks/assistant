#!/bin/bash
# setup_projects.sh — Create Vikunja projects for OpenClaw Bot and Personal
#
# Usage: bash /data/bot/openclaw-docker/skills/vikunja/setup_projects.sh
#
# This script creates the required project structure in Vikunja:
# - OpenClaw Bot project (for agent tasks)
# - Personal project (for personal tasks)

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VIKUNJA_SCRIPT="$SCRIPT_DIR/vikunja.sh"

echo "🔧 Vikunja Project Setup"
echo "========================"
echo ""

# Check if Vikunja is configured
if [ -z "$VIKUNJA_TOKEN" ]; then
    echo "❌ Error: VIKUNJA_TOKEN environment variable is not set"
    echo "   Please set VIKUNJA_TOKEN in your .env file"
    exit 1
fi

# Check API status first
echo "📡 Checking Vikunja API connection..."
STATUS=$(bash "$VIKUNJA_SCRIPT" status 2>&1)
if echo "$STATUS" | grep -q "error\|Error\|failed"; then
    echo "❌ Error connecting to Vikunja API"
    echo "   $STATUS"
    exit 1
fi
echo "✅ Vikunja API connected"
echo ""

# List existing projects
echo "📋 Current projects:"
bash "$VIKUNJA_SCRIPT" projects
echo ""

# Create OpenClaw Bot project
echo "📦 Creating 'OpenClaw Bot' project..."
OC_RESULT=$(bash "$VIKUNJA_SCRIPT" create-project "OpenClaw Bot" "Tasks from nightly agents: bugs, improvements, discoveries" 2>&1)
echo "$OC_RESULT" | jq '.' 2>/dev/null || echo "$OC_RESULT"
echo ""

# Create Personal project
echo "📦 Creating 'Personal' project..."
P_RESULT=$(bash "$VIKUNJA_SCRIPT" create-project "Personal" "Personal tasks: sport, finance, learning" 2>&1)
echo "$P_RESULT" | jq '.' 2>/dev/null || echo "$P_RESULT"
echo ""

# List all projects after creation
echo "✅ Setup complete! Final project list:"
bash "$VIKUNJA_SCRIPT" projects
echo ""

echo "📝 Next steps:"
echo "   1. Open Vikunja UI at http://localhost:3456"
echo "   2. Create lists inside each project (optional):"
echo "      - OpenClaw Bot: Inbox, Bugs, Improvements, Discovery, Config Changes, Done"
echo "      - Personal: Inbox, Sport, Finance, Learning, Done"
echo "   3. Update jobs.json to use correct project IDs"
echo ""
echo "🔗 Vikunja task commands now available:"
echo "   - vikunja.sh create-bug \"title\" \"description\" \"due_date\""
echo "   - vikunja.sh create-improvement \"title\" \"description\" \"due_date\""
echo "   - vikunja.sh create-discovery \"title\" \"description\" \"due_date\""
echo "   - vikunja.sh create-for-project <id> \"title\" \"description\" \"due_date\" priority"
echo "   - vikunja.sh list-overdue"
echo "   - vikunja.sh weekly-report"
