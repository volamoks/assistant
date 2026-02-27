#!/bin/bash
# Plaud.ai API CLI
# Usage: bash /data/bot/openclaw-docker/skills/plaud/plaud.sh <command> [args...]

set -e

# Configuration
PLAUD_API_DOMAIN="${PLAUD_API_DOMAIN:-https://api-euc1.plaud.ai}"
PLAUD_TOKEN="${PLAUD_TOKEN:-}"

if [ -z "$PLAUD_TOKEN" ]; then
    echo "Error: PLAUD_TOKEN environment variable is not set"
    exit 1
fi

# Headers
HEADERS=(-H "Authorization: Bearer $PLAUD_TOKEN" -H "Content-Type: application/json")

# Commands
case "$1" in
    list)
        # List all recordings
        curl -s "${HEADERS[@]}" "$PLAUD_API_DOMAIN/file/simple/web" | jq -r '(.data_file_list // []) | ["ID", "Title", "Created At"], ["---", "---", "---"], (.[] | [.id, .filename, (.edit_time | strftime("%Y-%m-%d %H:%M:%S"))]) | @tsv' | column -t -s $'\t'
        ;;
    summary)
        # Get recording details (transcript + summary)
        FILE_ID="$2"
        if [ -z "$FILE_ID" ]; then
            echo "Usage: plaud.sh summary <file_id>"
            exit 1
        fi
        RESULT=$(curl -s "${HEADERS[@]}" "$PLAUD_API_DOMAIN/file/detail/$FILE_ID")
        echo "$RESULT" | jq -r '.data | if . == null then "Error: File not found" else "# \(.file_name)\n\n**Created At:** \((.start_time / 1000) | strftime("%Y-%m-%d %H:%M:%S"))\n\n## Content Links\n\n\(.content_list[] | "- [\(.data_title)](\(.data_link))")" end'
        ;;
    download)
        # Get download URL
        FILE_ID="$2"
        if [ -z "$FILE_ID" ]; then
            echo "Usage: plaud.sh download <file_id>"
            exit 1
        fi
        curl -s "${HEADERS[@]}" "$PLAUD_API_DOMAIN/file/download/$FILE_ID" | jq -r '.data.download_url'
        ;;
    *)
        echo "Plaud CLI - Recording Management"
        echo ""
        echo "Usage: plaud.sh <command> [args...]"
        echo ""
        echo "Commands:"
        echo "  list                 List recent recordings"
        echo "  summary <id>         Get transcript and summary"
        echo "  download <id>        Get download URL for the recording"
        echo ""
        exit 1
        ;;
esac
