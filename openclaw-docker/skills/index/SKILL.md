---
name: index
description: "Rebuild Obsidian FTS5 search index. Run after adding large files to vault."
---

# /index — Rebuild Obsidian Search Index

Run via sysadmin agent:

```
python3 /data/bot/openclaw-docker/scripts/obsidian_index.py \
  --vault /data/obsidian \
  --db "/data/obsidian/To claw/Bot/obsidian.db" \
  --force
```

Report: how many files indexed, any errors.
