#!/bin/bash
# Apply model configuration from Obsidian
# Usage: ./apply-model-config.sh

set -e

OBSIDIAN_PATH="$HOME/Library/Mobile Documents/iCloud~md~obsidian/Documents/My Docs/Claw/Bot/model-config.md"
LITELLM_CONFIG="$HOME/Projects/bot/openclaw-docker/litellm/config.yaml"
BACKUP_DIR="$HOME/Projects/bot/openclaw-docker/litellm/backups"

echo "📋 Reading model config from Obsidian..."

# Check if file exists
if [ ! -f "$OBSIDIAN_PATH" ]; then
    echo "❌ Error: $OBSIDIAN_PATH not found"
    exit 1
fi

# Extract main_model from the active config section
MAIN_MODEL=$(sed -n '/^```yaml$/,/^```$/p' "$OBSIDIAN_PATH" | grep "main_model:" | head -1 | awk '{print $2}')
CODER_MODEL=$(sed -n '/^```yaml$/,/^```$/p' "$OBSIDIAN_PATH" | grep "coder_model:" | head -1 | awk '{print $2}')
THINKING_MODEL=$(sed -n '/^```yaml$/,/^```$/p' "$OBSIDIAN_PATH" | grep "thinking_model:" | head -1 | awk '{print $2}')
CRON_FAST=$(sed -n '/^```yaml$/,/^```$/p' "$OBSIDIAN_PATH" | grep "cron_fast:" | head -1 | awk '{print $2}')
CRON_SMART=$(sed -n '/^```yaml$/,/^```$/p' "$OBSIDIAN_PATH" | grep "cron_smart:" | head -1 | awk '{print $2}')
FALLBACK=$(sed -n '/^```yaml$/,/^```$/p' "$OBSIDIAN_PATH" | grep "fallback:" | head -1 | awk '{print $2}')

# Also check for "current" section in YAML frontmatter or alternative format
if [ -z "$MAIN_MODEL" ]; then
    MAIN_MODEL=$(grep -A 20 "Current:" "$OBSIDIAN_PATH" | grep "main_model:" | head -1 | awk '{print $2}')
    CODER_MODEL=$(grep -A 20 "Current:" "$OBSIDIAN_PATH" | grep "coder_model:" | head -1 | awk '{print $2}')
    THINKING_MODEL=$(grep -A 20 "Current:" "$OBSIDIAN_PATH" | grep "thinking_model:" | head -1 | awk '{print $2}')
    CRON_FAST=$(grep -A 20 "Current:" "$OBSIDIAN_PATH" | grep "cron_fast:" | head -1 | awk '{print $2}')
    CRON_SMART=$(grep -A 20 "Current:" "$OBSIDIAN_PATH" | grep "cron_smart:" | head -1 | awk '{print $2}')
    FALLBACK=$(grep -A 20 "Current:" "$OBSIDIAN_PATH" | grep "fallback:" | head -1 | awk '{print $2}')
fi

# Validate required fields
if [ -z "$MAIN_MODEL" ] || [ -z "$CRON_FAST" ] || [ -z "$CRON_SMART" ]; then
    echo "❌ Error: Missing required model configuration"
    echo "Found: main_model=$MAIN_MODEL, cron_fast=$CRON_FAST, cron_smart=$CRON_SMART"
    exit 1
fi

echo "📝 Configuration found:"
echo "   main: $MAIN_MODEL"
echo "   coder: $CODER_MODEL"
echo "   thinking: $THINKING_MODEL"
echo "   cron_fast: $CRON_FAST"
echo "   cron_smart: $CRON_SMART"
echo "   fallback: $FALLBACK"

# Set defaults for missing values
CODER_MODEL=${CODER_MODEL:-$MAIN_MODEL}
THINKING_MODEL=${THINKING_MODEL:-$MAIN_MODEL}
FALLBACK=${FALLBACK:-$CRON_SMART}

# Create backup
mkdir -p "$BACKUP_DIR"
cp "$LITELLM_CONFIG" "$BACKUP_DIR/config-$(date +%Y%m%d-%H%M%S).yaml"
echo "💾 Backup created"

# Function to get model config based on model name
get_model_config() {
    local model=$1
    case $model in
        kilo-deepseek-chat)
            echo "openai/deepseek/deepseek-chat|https://api.kilo.ai/api/gateway/|KILOCODE_API_KEY"
            ;;
        local-small)
            echo "ollama_chat/qwen3.5:0.8b|os.environ/OLLAMA_HOST|ollama-local"
            ;;
        local-medium)
            echo "ollama_chat/qwen3.5:9b|os.environ/OLLAMA_HOST|ollama-local"
            ;;
        claw-main)
            echo "openai/MiniMax-M2.5|https://api.minimax.io/v1|MINIMAX_API_KEY"
            ;;
        claw-thinking)
            echo "openai/deepseek/deepseek-reasoner|https://api.kilo.ai/api/gateway/|KILOCODE_API_KEY"
            ;;
        *)
            echo "ERROR: Unknown model $model"
            exit 1
            ;;
    esac
}

# Now generate the config (simplified - just update key models)
echo "🔧 Updating LiteLLM config..."

# Use Python to do the replacement
python3 << PYEOF
import re
import datetime

config_path = "$LITELLM_CONFIG"
main_model = "$MAIN_MODEL"
coder_model = "$CODER_MODEL"
thinking_model = "$THINKING_MODEL"
cron_fast = "$CRON_FAST"
cron_smart = "$CRON_SMART"
fallback = "$FALLBACK"

# Map model aliases to actual LiteLLM configs
def get_model_config(model_name):
    """Map user-friendly model names to LiteLLM configs"""
    configs = {
        # MiniMax (coding subscription)
        "claw-main": {
            "model": "openai/MiniMax-M2.5",
            "api_base": "https://api.minimax.io/v1",
            "api_key": "os.environ/MINIMAX_API_KEY"
        },
        # DeepSeek R1 via KiloCode
        "claw-thinking": {
            "model": "openai/deepseek/deepseek-reasoner",
            "api_base": "https://api.kilo.ai/api/gateway/",
            "api_key": "os.environ/KILOCODE_API_KEY"
        },
        # KiloCode DeepSeek Chat (cheap fallback)
        "kilo-deepseek-chat": {
            "model": "openai/deepseek/deepseek-chat",
            "api_base": "https://api.kilo.ai/api/gateway/",
            "api_key": "os.environ/KILOCODE_API_KEY"
        },
        # Ollama local models
        "local-small": {
            "model": "ollama_chat/qwen3.5:0.8b",
            "api_base": "os.environ/OLLAMA_HOST",
            "api_key": "os.environ/OLLAMA_API_KEY"
        },
        "local-medium": {
            "model": "ollama_chat/qwen3.5:9b",
            "api_base": "os.environ/OLLAMA_HOST",
            "api_key": "os.environ/OLLAMA_API_KEY"
        }
    }
    return configs.get(model_name, configs["kilo-deepseek-chat"])

# Get configs for each role
main_cfg = get_model_config(main_model)
thinking_cfg = get_model_config(thinking_model)
cron_fast_cfg = get_model_config(cron_fast)
cron_smart_cfg = get_model_config(cron_smart)
fallback_cfg = get_model_config(fallback)

# Write the configuration we'll use
new_config = f"""# AUTO-GENERATED MODEL CONFIG
# Generated at: {datetime.datetime.now().isoformat()}
# main: {main_model}, coder: {coder_model}, thinking: {thinking_model}
# cron_fast: {cron_fast}, cron_smart: {cron_smart}, fallback: {fallback}

model_list:
  # === CLAW-MAIN (Primary conversation - {main_model}) ===
  - model_name: claw-main
    litellm_params:
      model: {main_cfg['model']}
      api_base: {main_cfg['api_base']}
      api_key: {main_cfg['api_key']}

  # === CLAW-CODER (Coding tasks) ===
  - model_name: claw-coder
    litellm_params:
      model: {main_cfg['model']}
      api_base: {main_cfg['api_base']}
      api_key: {main_cfg['api_key']}

  # === CLAW-THINKING (Deep reasoning - {thinking_model}) ===
  - model_name: claw-thinking
    litellm_params:
      model: {thinking_cfg['model']}
      api_base: {thinking_cfg['api_base']}
      api_key: {thinking_cfg['api_key']}

  - model_name: claw-architect
    litellm_params:
      model: {thinking_cfg['model']}
      api_base: {thinking_cfg['api_base']}
      api_key: {thinking_cfg['api_key']}

  # === CLAW-RESEARCHER ===
  - model_name: claw-researcher
    litellm_params:
      model: {main_cfg['model']}
      api_base: {main_cfg['api_base']}
      api_key: {main_cfg['api_key']}

  # === CLAW-VISION ===
  - model_name: claw-vision
    litellm_params:
      model: {main_cfg['model']}
      api_base: {main_cfg['api_base']}
      api_key: {main_cfg['api_key']}

  # === CLAW-FREE (Fallback - {fallback}) ===
  - model_name: claw-free-fast
    litellm_params:
      model: {fallback_cfg['model']}
      api_base: {fallback_cfg['api_base']}
      api_key: {fallback_cfg['api_key']}

  - model_name: claw-free-smart
    litellm_params:
      model: {fallback_cfg['model']}
      api_base: {fallback_cfg['api_base']}
      api_key: {fallback_cfg['api_key']}

  # === CRON FAST (Quick checks - {cron_fast}) ===
  - model_name: claw-cron-fast
    litellm_params:
      model: {cron_fast_cfg['model']}
      api_base: {cron_fast_cfg['api_base']}
      api_key: {cron_fast_cfg['api_key']}

  # === CRON SMART (Complex tasks - {cron_smart}) ===
  - model_name: claw-cron-smart
    litellm_params:
      model: {cron_smart_cfg['model']}
      api_base: {cron_smart_cfg['api_base']}
      api_key: {cron_smart_cfg['api_key']}

  # === LOCAL MODELS (Ollama) ===
  - model_name: local-small
    litellm_params:
      model: ollama_chat/qwen3.5:0.8b
      api_base: os.environ/OLLAMA_HOST

  - model_name: local-medium
    litellm_params:
      model: ollama_chat/qwen3.5:9b
      api_base: os.environ/OLLAMA_HOST

litellm_settings:
  cache: true
  cache_params:
    type: redis
    host: redis-cache
  request_timeout: 300

router_settings:
  fallbacks:
    - claw-main: ["claw-free-fast", "claw-cron-smart"]
    - claw-coder: ["claw-free-fast", "claw-cron-smart"]
    - claw-architect: ["claw-thinking", "claw-main"]
    - claw-thinking: ["claw-main", "claw-free-fast"]
    - claw-researcher: ["claw-free-fast"]
    - claw-vision: ["claw-free-fast"]
    - claw-summarizer: ["claw-free-fast"]
    - claw-free-fast: ["local-medium", "local-small"]
    - claw-free-smart: ["local-medium", "local-small"]
    - claw-cron-fast: ["local-small", "kilo-deepseek-chat"]
    - claw-cron-smart: ["local-medium", "kilo-deepseek-chat"]

general_settings:
  master_key: os.environ/LITELLM_MASTER_KEY
  model_health_check: false
  health_check_interval: 0
"""

with open(config_path, 'w') as f:
    f.write(new_config)

print("Config written successfully")
PYEOF

echo "✅ Config updated"
echo "🔄 Restarting LiteLLM..."
docker restart litellm-proxy

sleep 5
echo ""
echo "🧪 Testing configuration..."

# Test the main model
RESULT=$(curl -s -X POST http://localhost:18788/chat/completions \
  -H "Authorization: Bearer sk-litellm-openclaw-proxy" \
  -H "Content-Type: application/json" \
  -d '{"model": "claw-main", "messages": [{"role": "user", "content": "Hi"}], "max_tokens": 10}' | python3 -c "import json,sys; d=json.load(sys.stdin); print('✅ OK' if 'content' in d.get('choices',[{}])[0].get('message',{}) else '❌ ' + d.get('error',{}).get('message','')[:50])" 2>/dev/null || echo "❌ Failed")

echo "   claw-main: $RESULT"

# Test cron-fast
RESULT=$(curl -s -X POST http://localhost:18788/chat/completions \
  -H "Authorization: Bearer sk-litellm-openclaw-proxy" \
  -H "Content-Type: application/json" \
  -d '{"model": "claw-cron-fast", "messages": [{"role": "user", "content": "Hi"}], "max_tokens": 10}' | python3 -c "import json,sys; d=json.load(sys.stdin); print('✅ OK' if 'content' in d.get('choices',[{}])[0].get('message',{}) else '❌ ' + d.get('error',{}).get('message','')[:50])" 2>/dev/null || echo "❌ Failed")

echo "   claw-cron-fast: $RESULT"

echo ""
echo "✅ Done! Bot is now using the new model configuration."