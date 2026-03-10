#!/bin/bash
# Terminal Execution Skill for OpenClaw Agents
#
# Usage:
#   terminal.sh "<command>"
#
# Constraints:
# - Runs as hostuser (uid=501) with sudo NOPASSWD:ALL — sudo works without password.
# - Truncates output to 4000 chars to avoid overwhelming the LLM.
# - sudo IS supported: bash terminal.sh "sudo apt-get install -y pkg"

if [ -z "$1" ]; then
    echo "Usage: terminal.sh \"<command>\""
    echo "Example: terminal.sh \"ls -la /tmp\""
    exit 1
fi

COMMAND="$1"

# Execute the command, capture stdout and stderr, timeout after 60 seconds
echo "Executing: $COMMAND"
echo "----------------------------------------"

# Use timeout to prevent hanging commands (e.g., interactive prompts, long tasks)
if timeout 60 bash -c "$COMMAND" > /tmp/terminal_out_$$.txt 2>&1; then
    EXIT_CODE=$?
else
    EXIT_CODE=$?
    if [ $EXIT_CODE -eq 124 ]; then
        echo "Error: Command timed out after 60 seconds." > /tmp/terminal_out_$$.txt
    fi
fi

# Read output, truncate if necessary
OUTPUT=$(cat /tmp/terminal_out_$$.txt | head -c 4000)
OUT_LEN=$(cat /tmp/terminal_out_$$.txt | wc -c)

echo "$OUTPUT"

if [ "$OUT_LEN" -gt 4000 ]; then
    echo ""
    echo "... [OUTPUT TRUNCATED] (Original size: $OUT_LEN bytes)"
fi

echo "----------------------------------------"
echo "Exit code: $EXIT_CODE"

rm -f /tmp/terminal_out_$$.txt
exit $EXIT_CODE
