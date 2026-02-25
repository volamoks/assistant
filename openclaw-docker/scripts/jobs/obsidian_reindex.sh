#!/bin/bash
# obsidian_reindex.sh — Full reindex of Obsidian vault into ChromaDB
# Phase 1: Markdown files via ingest.js (Node.js)
# Phase 2: Binary docs (PDF, DOCX, RTF, XLSX, PPTX) via ingest_docs.py (Python/markitdown)

set -e

OLLAMA_HOST="${OLLAMA_HOST:-http://ollama:11434}"
CHROMA_HOST="${CHROMA_HOST:-http://chromadb:8000}"
VAULT_PATH="${OBSIDIAN_VAULT_PATH:-/data/obsidian/To claw}"
INGEST_JS="/home/node/.openclaw/skills/obsidian_search/ingest.js"
INGEST_DOCS="/data/bot/openclaw-docker/scripts/ingest_docs.py"

echo "[obsidian-reindex] ============================================"
echo "[obsidian-reindex] Starting at $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "[obsidian-reindex] Vault: $VAULT_PATH"
echo "[obsidian-reindex] ============================================"

# ── Phase 1: Markdown files ──────────────────────────────────────────────────
echo ""
echo "[obsidian-reindex] Phase 1/2: Indexing markdown (.md) files..."
OLLAMA_HOST="$OLLAMA_HOST" CHROMA_HOST="$CHROMA_HOST" \
  OBSIDIAN_VAULT_PATH="$VAULT_PATH" \
  node "$INGEST_JS"

echo "[obsidian-reindex] ✅ Phase 1 done"

# ── Phase 2: Binary documents ────────────────────────────────────────────────
echo ""
echo "[obsidian-reindex] Phase 2/2: Indexing documents (PDF, DOCX, RTF, XLSX, PPTX)..."
OLLAMA_HOST="$OLLAMA_HOST" CHROMA_HOST="$CHROMA_HOST" \
  OBSIDIAN_VAULT_PATH="$VAULT_PATH" \
  python3 "$INGEST_DOCS"

echo ""
echo "[obsidian-reindex] ✅ All phases complete at $(date -u +%Y-%m-%dT%H:%M:%SZ)"
