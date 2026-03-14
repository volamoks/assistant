#!/usr/bin/env python3
import sys
import re
import os
import subprocess

CONFIG_FILE = "litellm/config.yaml"

MODELS = {
    "paid": {
        "model": "openai/MiniMax-M2.5",
        "api_key": "os.environ/MINIMAX_API_KEY",
        "api_base": "https://api.minimax.io/v1"
    },
    "kilo": {
        "model": "openai/minimax/minimax-m2.5:free",
        "api_key": "os.environ/KILOCODE_API_KEY",
        "api_base": "https://api.kilo.ai/api/gateway/"
    },
    "deepseek": {
        "model": "deepseek/deepseek-chat",
        "api_key": "os.environ/DEEPSEEK_API_KEY",
        "api_base": "https://api.deepseek.com/v1"
    },
    "qwen": {
        "model": "openai/qwen3-max-2026-01-23",
        "api_key": "os.environ/DASHSCOPE_API_KEY",
        "api_base": "os.environ/DASHSCOPE_API_BASE"
    }
}

TARGET_ALIASES = ["claw-main", "claw-coder", "claw-researcher"]

def update_config(mode):
    if not os.path.exists(CONFIG_FILE):
        print(f"Error: {CONFIG_FILE} not found. Please run this script from the openclaw-docker directory.")
        sys.exit(1)
        
    with open(CONFIG_FILE, 'r') as f:
        lines = f.readlines()
        
    new_lines = []
    in_target_block = False
    current_alias = None
    target_config = MODELS[mode]
    
    i = 0
    while i < len(lines):
        line = lines[i]
        
        # Check if entering a target alias block
        match = re.match(r'^\s*-\s*model_name:\s*([\w\-]+)', line)
        if match:
            alias = match.group(1)
            if alias in TARGET_ALIASES:
                in_target_block = True
                current_alias = alias
            else:
                in_target_block = False
                current_alias = None
        
        if in_target_block:
            # Replace model, api_key, api_base, preserving indentation
            if re.match(r'^\s*model:\s*', line):
                space_prefix = line[:len(line) - len(line.lstrip())]
                new_lines.append(f"{space_prefix}model: {target_config['model']}\n")
                i += 1
                continue
            elif re.match(r'^\s*api_key:\s*', line):
                space_prefix = line[:len(line) - len(line.lstrip())]
                new_lines.append(f"{space_prefix}api_key: {target_config['api_key']}\n")
                i += 1
                continue
            elif re.match(r'^\s*api_base:\s*', line):
                space_prefix = line[:len(line) - len(line.lstrip())]
                new_lines.append(f"{space_prefix}api_base: {target_config['api_base']}\n")
                i += 1
                continue
                
        new_lines.append(line)
        i += 1
        
    with open(CONFIG_FILE, 'w') as f:
        f.writelines(new_lines)
        
    print(f"✅ Successfully updated {CONFIG_FILE} to mode: {mode}")

def print_status():
    if not os.path.exists(CONFIG_FILE):
        print(f"Error: {CONFIG_FILE} not found. Please run this script from the openclaw-docker directory.")
        sys.exit(1)
        
    with open(CONFIG_FILE, 'r') as f:
        lines = f.readlines()
        
    in_target_block = False
    current_alias = None
    
    print("Current configuration for main aliases:")
    for line in lines:
        match = re.match(r'^\s*-\s*model_name:\s*([\w\-]+)', line)
        if match:
            alias = match.group(1)
            if alias in TARGET_ALIASES:
                in_target_block = True
                current_alias = alias
                print(f"\n[{current_alias}]")
            else:
                in_target_block = False
                
        if in_target_block:
            if re.match(r'^\s*(model|api_key|api_base):\s*', line):
                print("  " + line.strip())

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: ./switch_main_models.py [paid|kilo|deepseek|qwen|status]")
        sys.exit(1)
        
    cmd = sys.argv[1].lower()
    
    if cmd == "status":
        print_status()
    elif cmd in MODELS:
        update_config(cmd)
        print("🔄 Restarting litellm-proxy container...")
        subprocess.run(["docker", "restart", "litellm-proxy"])
    else:
        print("Invalid mode. Use: paid, kilo, deepseek, qwen, or status")
        sys.exit(1)
