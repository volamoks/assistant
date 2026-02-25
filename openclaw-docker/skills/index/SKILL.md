---
name: index
description: "Re-index the Obsidian vault into ChromaDB for semantic RAG search. Use after adding many new notes. Also re-runs nightly via cron automatically."
triggers:
  - reindex obsidian
  - rebuild index
  - update obsidian index
  - index vault
---

# /index — Rebuild Obsidian RAG Index

Re-indexes the Obsidian vault into **ChromaDB** for semantic search.
This runs automatically at **03:00 Asia/Tashkent** via the `obsidian-reindex` cron job.

## Run manually

```bash
OLLAMA_HOST=http://ollama:11434 \
CHROMA_HOST=http://chromadb:8000 \
OBSIDIAN_VAULT_PATH="/data/obsidian/To claw" \
node /home/node/.openclaw/skills/obsidian_search/ingest.js
```

Or trigger via sysadmin agent:
```
bash: /data/bot/openclaw-docker/scripts/jobs/obsidian_reindex.sh
```

Report: how many files processed, any errors.
