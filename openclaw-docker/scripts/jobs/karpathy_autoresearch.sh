#!/bin/bash
# Karpathy Autoresearch - Daily self-improvement cycle
# Runs the complete autoresearch pipeline

set -e

echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] Starting Karpathy Autoresearch cycle"

# Run the autoresearch cycle
python3 /home/node/.openclaw/skills/karpathy-autoresearch/run.py --compact

echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] Karpathy Autoresearch cycle complete"
