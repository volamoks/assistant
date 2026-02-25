#!/bin/bash
# Reindex Obsidian vault into ChromaDB for RAG search
# Runs nightly to keep the vector index up to date

OLLAMA_HOST="http://ollama:11434"
CHROMA_HOST="http://chromadb:8000"
VAULT_PATH="${OBSIDIAN_VAULT_PATH:-/data/obsidian/To claw}"

echo "[obsidian-reindex] Starting at $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "[obsidian-reindex] Vault: $VAULT_PATH"

node /home/node/.openclaw/skills/obsidian_search/ingest.js

EXIT_CODE=$?
if [ $EXIT_CODE -eq 0 ]; then
  echo "[obsidian-reindex] ✅ Done at $(date -u +%Y-%m-%dT%H:%M:%SZ)"
else
  echo "[obsidian-reindex] ❌ Failed with exit code $EXIT_CODE"
  exit $EXIT_CODE
fi
