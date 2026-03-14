#!/bin/bash

# Configuration
CONFIG_FILE="${CONFIG_FILE:-$HOME/.config/opencode/config.json}"
LITELLM_URL="${LITELLM_HOST:-http://localhost:18788}"
LITELLM_KEY="${LITELLM_API_KEY:-sk-litellm-openclaw-proxy}"

# Models
MODEL_FREE="opencode/minimax-m2.5-free"
MODEL_KILO="litellm/kilocode/minimax-m2.5-free"
MODEL_PAID="litellm/claw-researcher"

usage() {
    echo "Usage: $0 [free|kilo|paid|status]"
    echo "  free   - Use Free MiniMax from OpenCode Zen"
    echo "  kilo   - Use Free MiniMax from KiloCode (via LiteLLM)"
    echo "  paid   - Use Paid MiniMax (via LiteLLM)"
    echo "  status - Show current configuration"
    exit 1
}

if [ ! -f "$CONFIG_FILE" ]; then
    echo "Error: Config file not found at $CONFIG_FILE"
    echo "Creating a default one..."
    mkdir -p "$(dirname "$CONFIG_FILE")"
    echo '{"$schema": "https://opencode.ai/config.json", "agent": {"researcher": {}}, "default_agent": "researcher"}' > "$CONFIG_FILE"
fi

get_current() {
    jq -r '.agent.researcher.model // "not set"' "$CONFIG_FILE"
}

set_model() {
    local mode=$1
    local model=$2
    echo "Switching to $mode mode ($model)..."

    # Ensure litellm provider exists for LiteLLM modes
    if [[ "$mode" == "kilo" || "$mode" == "paid" ]]; then
        # Remove old openai provider if it exists to avoid confusion
        jq 'del(.provider.openai)' "$CONFIG_FILE" > "$CONFIG_FILE.tmp" && mv "$CONFIG_FILE.tmp" "$CONFIG_FILE"

        jq --arg url "$LITELLM_URL/v1" --arg key "$LITELLM_KEY" \
           '.provider.litellm = {"npm": "@ai-sdk/openai-compatible", "name": "LiteLLM", "options": {"baseURL": $url, "apiKey": $key}, "models": {"claw-main": {}, "claw-researcher": {}, "kilocode/minimax-m2.5-free": {}}}' \
           "$CONFIG_FILE" > "$CONFIG_FILE.tmp" && mv "$CONFIG_FILE.tmp" "$CONFIG_FILE"
    fi

    # Update researcher agent model
    jq --arg model "$model" '.agent.researcher.model = $model' "$CONFIG_FILE" > "$CONFIG_FILE.tmp" && mv "$CONFIG_FILE.tmp" "$CONFIG_FILE"
    
    echo "✅ Successfully switched to $mode"
}

case "$1" in
    free)
        set_model "free" "$MODEL_FREE"
        ;;
    kilo)
        set_model "kilo" "$MODEL_KILO"
        ;;
    paid)
        set_model "paid" "$MODEL_PAID"
        ;;
    status)
        echo "Current model: $(get_current)"
        ;;
    *)
        usage
        ;;
esac
