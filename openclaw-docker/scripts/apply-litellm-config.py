#!/usr/bin/env python3
"""
Apply LiteLLM config from Obsidian router-config.md
Reads primaries, aliases, fallbacks from YAML sections in the markdown file.
Usage: python3 apply-litellm-config.py [--dry-run]
"""

import re
import sys
import subprocess
import os
import yaml

VAULT_PATH = "/data/obsidian/vault/Bot/LiteLLM"
CONFIG_SOURCE = f"{VAULT_PATH}/router-config.md"
CONFIG_TARGET = "/data/bot/openclaw-docker/litellm/config.yaml"
CONTAINER_NAME = "litellm-proxy"

def log(msg):
    print(f"  {msg}")

def extract_yaml_sections(content):
    """Split markdown by ## headers and parse each YAML section."""
    # Split by ## headers (but not ### or ####)
    parts = re.split(r'\n##\s+', content)
    
    sections = {}
    for part in parts[1:]:  # Skip the part before first ## (intro/comments)
        lines = part.split('\n')
        section_name = lines[0].strip()
        
        # Collect YAML lines (skip comments, blank lines at start)
        yaml_lines = []
        for line in lines[1:]:
            stripped = line.lstrip()
            # Skip blank lines and comment-only lines
            if stripped.startswith('#'):
                continue
            yaml_lines.append(line)
        
        yaml_text = '\n'.join(yaml_lines).strip()
        # Remove YAML document separators (---)
        yaml_text = yaml_text.replace('\n---\n', '\n').replace('\n---', '').replace('---\n', '')
        if yaml_text:
            try:
                parsed = yaml.safe_load(yaml_text)
                if isinstance(parsed, dict) and len(parsed) == 1:
                    # Always unwrap single-key dicts (the YAML section has the key name at top level)
                    parsed = list(parsed.values())[0]
                sections[section_name] = parsed if parsed else {}
            except yaml.YAMLError as e:
                print(f"  ⚠️  YAML parse error in '{section_name}': {e}")
                sections[section_name] = {}
    
    return sections

def generate_config_yaml(primaries, aliases, fallbacks):
    """Generate LiteLLM config.yaml from parsed sections."""
    
    model_defs = {
        # MiniMax Native
        "minimax-m27": {
            "model": "openai/MiniMax-M2.7",
            "api_base": "https://api.minimax.io/v1",
            "env_key": "MINIMAX_API_KEY",
            "vision": True,
        },
        "minimax-m25": {
            "model": "openai/MiniMax-M2.5",
            "api_base": "https://api.minimax.io/v1",
            "env_key": "MINIMAX_API_KEY",
            "vision": True,
        },
        # Coding Plan models
        "coding-minimax-m25": {
            "model": "openai/MiniMax-M2.5",
            "api_base": "https://coding-intl.dashscope.aliyuncs.com/v1",
            "env_key": "DASHSCOPE_API_KEY",
            "vision": True,
        },
        "coding-qwen-3.5-plus": {
            "model": "openai/qwen3.5-plus",
            "api_base": "https://coding-intl.dashscope.aliyuncs.com/v1",
            "env_key": "DASHSCOPE_API_KEY",
            "vision": True,
        },
        "coding-kimi-k25": {
            "model": "openai/kimi-k2.5",
            "api_base": "https://coding-intl.dashscope.aliyuncs.com/v1",
            "env_key": "DASHSCOPE_API_KEY",
            "vision": True,
        },
        "coding-glm-5": {
            "model": "openai/glm-5",
            "api_base": "https://coding-intl.dashscope.aliyuncs.com/v1",
            "env_key": "DASHSCOPE_API_KEY",
        },
        "coding-glm-4.7": {
            "model": "openai/glm-4.7",
            "api_base": "https://coding-intl.dashscope.aliyuncs.com/v1",
            "env_key": "DASHSCOPE_API_KEY",
        },
        "coding-qwen3-max": {
            "model": "openai/qwen3-max-2026-01-23",
            "api_base": "https://coding-intl.dashscope.aliyuncs.com/v1",
            "env_key": "DASHSCOPE_API_KEY",
        },
        "coding-qwen3-coder-plus": {
            "model": "openai/qwen3-coder-plus",
            "api_base": "https://coding-intl.dashscope.aliyuncs.com/v1",
            "env_key": "DASHSCOPE_API_KEY",
        },
        "coding-qwen3-coder-next": {
            "model": "openai/qwen3-coder-next",
            "api_base": "https://coding-intl.dashscope.aliyuncs.com/v1",
            "env_key": "DASHSCOPE_API_KEY",
        },
        # Kilo.ai
        "kilo-minimax": {
            "model": "openai/minimax/minimax-m2.5:free",
            "api_base": "https://api.kilo.ai/api/gateway/",
            "env_key": "KILOCODE_API_KEY",
            "vision": True,
        },
        "kilo-minimax2": {
            "model": "openai/minimax/minimax-m2.5:free",
            "api_base": "https://api.kilo.ai/api/gateway/",
            "env_key": "KILOCODE_API_KEY",
            "vision": True,
        },
        "kilo-nemotron": {
            "model": "openai/nvidia/nemotron-3-super-120b-a12b-20230311:free",
            "api_base": "https://api.kilo.ai/api/gateway/",
            "env_key": "KILOCODE_API_KEY",
            "reasoning": True,
        },
        "kilo-deepseek": {
            "model": "openai/deepseek/deepseek-chat",
            "api_base": "https://api.kilo.ai/api/gateway/",
            "env_key": "KILOCODE_API_KEY",
        },
        "kilo-deepseek-terminus": {
            "model": "openai/deepseek/deepseek-v3.1-terminus",
            "api_base": "https://api.kilo.ai/api/gateway/",
            "env_key": "KILOCODE_API_KEY",
        },
        # OpenCode
        "oc-nemotron": {
            "model": "openai/nemotron-3-super-free",
            "api_base": "https://opencode.ai/zen/v1",
            "env_key": "OPENCODE_API_KEY",
            "reasoning": True,
        },
        "oc-minimax": {
            "model": "openai/minimax/minimax-m2.5:free",
            "api_base": "https://api.kilo.ai/api/gateway/",
            "env_key": "KILOCODE_API_KEY",
            "vision": True,
        },
        # DashScope Free
        "qwen-max": {
            "model": "openai/qwen3-max",
            "api_base": "https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
            "env_key": "DASHSCOPE_FREE_API_KEY",
        },
        "qwen-plus": {
            "model": "openai/qwen-plus-2025-07-28",
            "api_base": "https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
            "env_key": "DASHSCOPE_FREE_API_KEY",
        },
        "qwen-vl-max": {
            "model": "openai/qwen-vl-max-2025-04-08",
            "api_base": "https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
            "env_key": "DASHSCOPE_FREE_API_KEY",
            "vision": True,
        },
        "qwen-vl-plus": {
            "model": "openai/qwen-vl-plus-2025-05-07",
            "api_base": "https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
            "env_key": "DASHSCOPE_FREE_API_KEY",
            "vision": True,
        },
        "qwen-vl-72b": {
            "model": "openai/qwen2.5-vl-72b-instruct",
            "api_base": "https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
            "env_key": "DASHSCOPE_FREE_API_KEY",
            "vision": True,
        },
        # Local
        "local-small": {
            "model": "ollama/qwen2.5-coder:3b",
            "api_base": "os.environ/OLLAMA_HOST",
            "local": True,
        },
        "local-medium": {
            "model": "ollama/qwen3.5:9b",
            "api_base": "os.environ/OLLAMA_HOST",
            "local": True,
        },
        "nomic-embed-text": {
            "model": "ollama/nomic-embed-text",
            "api_base": "http://host.docker.internal:11434",
            "local": True,
            "drop_params": True,
        },
    }
    
    # Collect all models referenced in primaries + fallbacks
    models_to_include = set()
    for model in primaries.values():
        if isinstance(model, str):
            models_to_include.add(model)
    for fb_list in fallbacks.values():
        if isinstance(fb_list, list):
            for m in fb_list:
                if isinstance(m, str):
                    models_to_include.add(m)
    
    # Always include core infrastructure models
    always_include = [
        "minimax-m27", "minimax-m25", "qwen-vl-max", "qwen-vl-plus",
        "qwen-vl-72b", "local-small", "local-medium", "nomic-embed-text",
        "kilo-deepseek", "kilo-deepseek-terminus", "kilo-nemotron",
        "qwen-max", "qwen-plus", "oc-nemotron", "oc-minimax",
        "kilo-minimax", "kilo-minimax2",
    ]
    models_to_include.update(always_include)
    
    # Build model_list
    lines = ["model_list:"]
    for model_name in sorted(models_to_include):
        if model_name in model_defs:
            d = model_defs[model_name]
            lines.append(f"- model_name: {model_name}")
            lines.append(f"  litellm_params:")
            lines.append(f"    model: {d['model']}")
            lines.append(f"    api_base: {d['api_base']}")
            if not d.get('local'):
                lines.append(f"    api_key: os.environ/{d['env_key']}")
            if d.get('local') and d.get('drop_params'):
                lines.append(f"    drop_params: true")
            if d.get('vision'):
                lines.append(f"  model_info:")
                lines.append(f"    supports_vision: true")
            elif d.get('reasoning'):
                lines.append(f"  model_info:")
                lines.append(f"    supports_reasoning: true")
    
    # litellm_settings
    lines.extend([
        "litellm_settings:",
        "  cache: true",
        "  cache_params:",
        "    type: redis",
        "    host: redis-cache",
        "  request_timeout: 60",
        "  json_logs: true",
        "  success_callback:",
        "  - prometheus",
        "  failure_callback:",
        "  - prometheus",
        "  master_key: os.environ/LITELLM_MASTER_KEY",
        "  pass_through_headers: true",
    ])
    
    # router_settings - model_group_alias
    lines.append("router_settings:")
    lines.append("  model_group_alias:")
    for alias, model in sorted(primaries.items()):
        if isinstance(model, str):
            lines.append(f"    {alias}: {model}")
    for alias, model in sorted(aliases.items()):
        if isinstance(model, str) and alias not in primaries:
            lines.append(f"    {alias}: {model}")
    
    # router_settings - fallbacks
    lines.append("  fallbacks:")
    for model, fb_list in sorted(fallbacks.items()):
        if isinstance(fb_list, list) and fb_list:
            lines.append(f"  - {model}:")
            for fb in fb_list:
                if isinstance(fb, str):
                    lines.append(f"    - {fb}")
    
    # general_settings
    lines.extend([
        "general_settings:",
        "  master_key: os.environ/LITELLM_MASTER_KEY",
        "  model_health_check: false",
        "  health_check_interval: 0",
        "  store_model_in_db: false",
        "  store_prompts_in_spend_logs: false",
        "  disable_spend_logs: true",
    ])
    
    return "\n".join(lines) + "\n"

def main():
    dry_run = "--dry-run" in sys.argv
    
    print(f"\n{'[DRY RUN] ' if dry_run else ''}Applying LiteLLM config from: {CONFIG_SOURCE}")
    
    if not os.path.exists(CONFIG_SOURCE):
        print(f"❌ Source file not found: {CONFIG_SOURCE}")
        sys.exit(1)
    
    with open(CONFIG_SOURCE, 'r') as f:
        content = f.read()
    
    # Extract sections
    sections = extract_yaml_sections(content)
    primaries = sections.get("Primaries", {})
    aliases = sections.get("Aliases", {})
    fallbacks = sections.get("Fallbacks", {})
    
    print(f"\n✅ Parsed:")
    log(f"primaries: {len(primaries)} entries → {list(primaries.keys())}")
    log(f"aliases: {len(aliases)} entries → {list(aliases.keys())}")
    log(f"fallbacks: {len(fallbacks)} entries → {list(fallbacks.keys())}")
    
    if not primaries:
        print(f"\n❌ No primaries found! Check section name in source file.")
        sys.exit(1)
    
    # Generate config
    config_yaml = generate_config_yaml(primaries, aliases, fallbacks)
    
    if dry_run:
        print(f"\n[DRY RUN] Generated config ({len(config_yaml)} chars):\n")
        print(config_yaml[:5000])
        if len(config_yaml) > 5000:
            print(f"\n... [{len(config_yaml) - 5000} more chars]")
        return
    
    # Validate YAML syntax
    try:
        yaml.safe_load(config_yaml)
        print(f"\n✅ YAML syntax valid")
    except yaml.YAMLError as e:
        print(f"\n❌ YAML syntax error: {e}")
        sys.exit(1)
    
    # Backup current config
    if os.path.exists(CONFIG_TARGET):
        import shutil
        import time
        backup = f"{CONFIG_TARGET}.bak.{int(time.time())}"
        shutil.copy2(CONFIG_TARGET, backup)
        print(f"✅ Backed up → {backup}")
    
    # Write new config
    with open(CONFIG_TARGET, 'w') as f:
        f.write(config_yaml)
    print(f"✅ Written: {CONFIG_TARGET}")
    
    # Restart container
    print(f"\n🔄 Restarting {CONTAINER_NAME}...")
    result = subprocess.run(
        ["docker", "restart", CONTAINER_NAME],
        capture_output=True, text=True, timeout=30
    )
    if result.returncode == 0:
        print(f"✅ Container restarted")
        import time
        time.sleep(4)
        result = subprocess.run(
            ["docker", "logs", "--tail", "5", CONTAINER_NAME],
            capture_output=True, text=True
        )
        if result.returncode == 0 and "Ready" not in result.stdout and "Application startup complete" not in result.stdout:
            print(f"⚠️  Logs look different, check: docker logs {CONTAINER_NAME}")
        else:
            print(f"✅ LiteLLM is up")
    else:
        print(f"❌ Restart failed: {result.stderr}")
        sys.exit(1)
    
    print(f"\n🎉 Done!")

if __name__ == "__main__":
    main()
