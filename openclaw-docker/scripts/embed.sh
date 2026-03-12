#!/bin/bash
# embed.sh — Unified text embedding via LiteLLM (OpenAI-compatible).
#
# Primary:  LiteLLM proxy  http://litellm:4000/embeddings  (OpenAI format)
# Fallback: Direct Ollama  $OLLAMA_HOST/api/embeddings      (Ollama format)
#
# Usage:
#   bash embed.sh "text to embed"
#   TEXT="hello world" bash embed.sh
#
# Output:  JSON array on stdout, e.g. [0.1, -0.3, ...]
# Exit 0:  success
# Exit 1:  both endpoints failed
#
# Config via env:
#   LITELLM_HOST        — default: http://litellm:4000
#   LITELLM_MASTER_KEY  — Bearer token (auto-set in container via docker-compose)
#   OLLAMA_HOST         — default: http://host.docker.internal:11434
#   EMBED_MODEL         — default: nomic-embed-text

set -euo pipefail

TEXT="${1:-${TEXT:-}}"
LITELLM_HOST="${LITELLM_HOST:-http://litellm:4000}"
LITELLM_MASTER_KEY="${LITELLM_MASTER_KEY:-}"
OLLAMA_HOST="${OLLAMA_HOST:-http://host.docker.internal:11434}"
EMBED_MODEL="${EMBED_MODEL:-nomic-embed-text}"

if [ -z "$TEXT" ]; then
  echo "Usage: bash embed.sh 'text to embed'" >&2
  exit 1
fi

# JSON-escape the input text
ESCAPED=$(python3 -c "import json,sys; print(json.dumps(sys.stdin.read().strip()))" <<< "$TEXT")

# ── Primary: LiteLLM (OpenAI-compatible) ─────────────────────────────────────
AUTH_HEADER=""
if [ -n "$LITELLM_MASTER_KEY" ]; then
  AUTH_HEADER="-H Authorization: Bearer ${LITELLM_MASTER_KEY}"
fi

LITELLM_RESP=$(curl -sf --max-time 20 \
  -H "Content-Type: application/json" \
  ${LITELLM_MASTER_KEY:+-H "Authorization: Bearer ${LITELLM_MASTER_KEY}"} \
  -d "{\"model\":\"${EMBED_MODEL}\",\"input\":${ESCAPED}}" \
  "${LITELLM_HOST}/embeddings" 2>/dev/null) || LITELLM_RESP=""

if [ -n "$LITELLM_RESP" ]; then
  EMBEDDING=$(echo "$LITELLM_RESP" | python3 -c \
    "import json,sys; d=json.load(sys.stdin); print(json.dumps(d['data'][0]['embedding']))" \
    2>/dev/null) || EMBEDDING=""
  if [ -n "$EMBEDDING" ]; then
    echo "$EMBEDDING"
    exit 0
  fi
fi

# ── Fallback: Direct Ollama ───────────────────────────────────────────────────
OLLAMA_RESP=$(curl -sf --max-time 30 \
  -H "Content-Type: application/json" \
  -d "{\"model\":\"${EMBED_MODEL}\",\"prompt\":${ESCAPED}}" \
  "${OLLAMA_HOST}/api/embeddings" 2>/dev/null) || OLLAMA_RESP=""

if [ -n "$OLLAMA_RESP" ]; then
  EMBEDDING=$(echo "$OLLAMA_RESP" | python3 -c \
    "import json,sys; d=json.load(sys.stdin); print(json.dumps(d['embedding']))" \
    2>/dev/null) || EMBEDDING=""
  if [ -n "$EMBEDDING" ]; then
    echo "$EMBEDDING"
    exit 0
  fi
fi

echo "ERROR: embed.sh — both LiteLLM (${LITELLM_HOST}) and Ollama (${OLLAMA_HOST}) failed" >&2
exit 1
