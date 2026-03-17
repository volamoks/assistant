#!/bin/bash

# Configuration
CONFIG_FILE="${CONFIG_FILE:-$HOME/.config/opencode/config.json}"
LITELLM_URL="${LITELLM_HOST:-http://localhost:18788}"
LITELLM_KEY="${LITELLM_API_KEY:-sk-litellm-openclaw-proxy}"

# Model aliases (resolved via litellm router)
MODEL_OPENCODE="litellm/claw-opencode"       # kilo.ai MiniMax free (OPENCODE_API_KEY quota)
MODEL_KILO="litellm/kilo-minimax"            # kilo.ai MiniMax free (KILOCODE_API_KEY quota)
MODEL_NEMOTRON="litellm/oc-nemotron"         # NVIDIA Nemotron free via opencode.ai (fast!)
MODEL_PAID="litellm/claw-main"               # minimax.io premium
MODEL_LOCAL="litellm/local-medium"           # Ollama qwen3.5:9b

usage() {
    echo "Usage: $0 [opencode|kilo|nemotron|paid|local|status]"
    echo "  opencode  - Use OpenCode free MiniMax (OPENCODE_API_KEY quota)"
    echo "  kilo      - Use KiloCode free MiniMax (KILOCODE_API_KEY quota)"
    echo "  nemotron  - Use NVIDIA Nemotron 120B free (fast, kilo.ai)"
    echo "  paid      - Use premium MiniMax (minimax.io subscription)"
    echo "  local     - Use local Ollama (qwen3.5:9b)"
    echo "  status    - Show current configuration"
    exit 1
}

if [ ! -f "$CONFIG_FILE" ]; then
    echo "Error: Config file not found at $CONFIG_FILE"
    exit 1
fi

get_current() {
    jq -r '.model // .agent.coder.model // "not set"' "$CONFIG_FILE"
}

set_model() {
    local mode=$1
    local model=$2
    echo "Switching to $mode mode ($model)..."

    jq --arg url "$LITELLM_URL/v1" --arg key "$LITELLM_KEY" --arg model "$model" \
       '.provider.litellm.options.baseURL = $url
        | .provider.litellm.options.apiKey = $key
        | .model = $model
        | .agent.coder.model = $model' \
       "$CONFIG_FILE" > "$CONFIG_FILE.tmp" && mv "$CONFIG_FILE.tmp" "$CONFIG_FILE"

    echo "Done. Current model: $(get_current)"
}

case "$1" in
    opencode)   set_model "opencode"  "$MODEL_OPENCODE" ;;
    kilo)       set_model "kilo"      "$MODEL_KILO" ;;
    nemotron)   set_model "nemotron"  "$MODEL_NEMOTRON" ;;
    paid)       set_model "paid"      "$MODEL_PAID" ;;
    local)      set_model "local"     "$MODEL_LOCAL" ;;
    status)     echo "Current model: $(get_current)" ;;
    *)          usage ;;
esac
