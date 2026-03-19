---
name: obsidian_search
description: "Semantic search in the local Obsidian vault using RAG (ChromaDB + nomic-embed-text via LiteLLM). Use when you need user preferences, historical context, past decisions, or personal notes. Understands meaning — not just keywords."
triggers:
  - search obsidian
  - find in obsidian
  - obsidian search
  - search notes
  - what does the user prefer
  - user context
---

# Obsidian Semantic Search (RAG)

Searches the Obsidian vault semantically via ChromaDB + LiteLLM embeddings (nomic-embed-text).
Vault: `/data/obsidian/vault` | Re-indexed nightly.

## Usage

This skill is invoked automatically as a tool (index.mjs). Simply call it with a query:

```
obsidian_search({ query: "your query here", limit: 3 })
```

Or trigger manually via tool call with the query parameter.

## Examples

- `obsidian_search({ query: "user preferences coding style", limit: 3 })`
- `obsidian_search({ query: "OpenClaw architecture decisions", limit: 5 })`
- `obsidian_search({ query: "budget finance expenses", limit: 3 })`

## Notes

- Results are **semantic** — finds related content even without exact keyword match
- Each result shows the **source file** and a relevant excerpt (up to 800 chars)
- If results seem irrelevant, the vault may need reindexing: `bash /data/bot/openclaw-docker/scripts/jobs/obsidian_reindex.sh`
- Depends on: ChromaDB at `http://chromadb:8000`, LiteLLM `nomic-embed-text` at `http://litellm:4000`
