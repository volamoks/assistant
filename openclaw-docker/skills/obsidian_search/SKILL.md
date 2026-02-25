---
name: obsidian_search
description: "Semantic search in the local Obsidian vault using RAG (ChromaDB + nomic-embed-text). Use when you need user preferences, historical context, past decisions, or personal notes. Understands meaning — not just keywords."
triggers:
  - search obsidian
  - find in obsidian
  - obsidian search
  - search notes
  - what does the user prefer
  - user context
---

# Obsidian Semantic Search (RAG)

Searches the Obsidian vault semantically via ChromaDB + Ollama embeddings.
Vault: `/data/obsidian/To claw` | 106 indexed chunks | Re-indexed nightly.

## Usage

```bash
bash /data/bot/openclaw-docker/scripts/obsidian_rag_search.sh "your query here" 3
```

Replace `3` with desired number of results (default: 3).

## Examples

```bash
# Find user preferences
bash /data/bot/openclaw-docker/scripts/obsidian_rag_search.sh "user preferences coding style" 3

# Find project context
bash /data/bot/openclaw-docker/scripts/obsidian_rag_search.sh "OpenClaw architecture decisions" 5

# Find personal notes
bash /data/bot/openclaw-docker/scripts/obsidian_rag_search.sh "budget finance expenses" 3
```

## Notes

- Results are **semantic** — finds related content even without exact keyword match
- Each result shows the **source file** and a relevant excerpt (up to 800 chars)
- If results seem irrelevant, the vault may need reindexing: `bash /data/bot/openclaw-docker/scripts/jobs/obsidian_reindex.sh`
- Depends on: ChromaDB at `http://chromadb:8000`, Ollama `nomic-embed-text` at `http://ollama:11434`
