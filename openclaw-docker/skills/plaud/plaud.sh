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
        curl -s "${PLAUD_API_DOMAIN}/file/simple/web" "${HEADERS[@]}" | jq -r '(.data_file_list // []) | ["ID", "Title", "Created At"], ["---", "---", "---"], (.[] | [.id, .filename, (.edit_time | strftime("%Y-%m-%d %H:%M:%S"))]) | @tsv' | column -t -s $'\t'
        ;;
    summary)
        # Get recording details (transcript + summary)
        FILE_ID="$2"
        if [ -z "$FILE_ID" ]; then
            echo "Usage: plaud.sh summary <file_id>"
            exit 1
        fi
        RESULT=$(curl -s "${PLAUD_API_DOMAIN}/file/detail/$FILE_ID" "${HEADERS[@]}")
        echo "$RESULT" | jq -r '.data | if . == null then "Error: File not found" else "# \(.file_name)\n\n**Created At:** \((.start_time / 1000) | strftime("%Y-%m-%d %H:%M:%S"))\n\n## Content Links\n\n\(.content_list[] | "- [\(.data_title)](\(.data_link))")" end'
        ;;
    download)
        # Download audio file
        FILE_ID="$2"
        OUTPUT="${3:-audio.mp3}"
        if [ -z "$FILE_ID" ]; then
            echo "Usage: plaud.sh download <file_id> [output_path]"
            exit 1
        fi

        echo "Requesting download for file: $FILE_ID"
        TMP_RESP="/tmp/plaud_resp_$FILE_ID"
        curl -s -D /tmp/plaud_head_$FILE_ID "${PLAUD_API_DOMAIN}/file/download/$FILE_ID" "${HEADERS[@]}" -o "$TMP_RESP"
        
        CTYPE=$(grep -i "content-type" /tmp/plaud_head_$FILE_ID | awk '{print $2}' | tr -d '\r')
        
        if [[ "$CTYPE" == *"application/json"* ]]; then
            DOWNLOAD_URL=$(cat "$TMP_RESP" | jq -r '.data.download_url // empty')
            if [ -n "$DOWNLOAD_URL" ]; then
                echo "Downloading from external URL: $DOWNLOAD_URL"
                curl -L -o "$OUTPUT" "$DOWNLOAD_URL"
            else
                MSG=$(cat "$TMP_RESP" | jq -r '.msg // "Unknown error"')
                echo "Error from API: $MSG"
                exit 1
            fi
        else
            echo "Direct binary download detected."
            mv "$TMP_RESP" "$OUTPUT"
        fi


        if [ $? -eq 0 ]; then
            FILE_SIZE=$(du -h "$OUTPUT" | cut -f1)
            echo "✅ Download complete: $OUTPUT ($FILE_SIZE)"
        else
            echo "❌ Download failed"
            exit 1
        fi
        ;;
    transcribe)
        # Download audio + transcribe via Whisper → plain text
        FILE_ID="$2"
        OUTPUT="${3:-/tmp/plaud_transcript.txt}"
        AUDIO_TMP="/tmp/plaud_${FILE_ID}.mp3"

        if [ -z "$FILE_ID" ]; then
            echo "Usage: plaud.sh transcribe <file_id> [output_path]"
            exit 1
        fi

        echo "📥 Downloading recording $FILE_ID..."
        bash "$0" download "$FILE_ID" "$AUDIO_TMP"

        echo ""
        echo "🎙️  Transcribing with Whisper..."
        python3 /data/bot/openclaw-docker/workspace/plaud_audio/transcribe_pipeline.py "$AUDIO_TMP" -o "$OUTPUT"

        rm -f "$AUDIO_TMP"

        echo ""
        echo "=== TRANSCRIPT ==="
        cat "$OUTPUT"
        ;;
    *)
        echo "Plaud CLI - Recording Management"
        echo ""
        echo "Usage: plaud.sh <command> [args...]"
        echo ""
        echo "Commands:"
        echo "  list                          List recent recordings"
        echo "  summary <id>                  Get Plaud built-in transcript/summary"
        echo "  download <id> [path]          Download audio file (default: audio.mp3)"
        echo "  transcribe <id> [output.txt]  Download + Whisper transcription"
        echo ""
        exit 1
        ;;
esac
