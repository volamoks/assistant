---
name: web_clip
description: "Clip a web page to Obsidian vault as clean Markdown. Use when user sends a URL and wants to save it for later, create knowledge base, or read an article. Works with articles, Wikipedia, X.com threads, Notion pages, documentation, etc."
triggers:
  - save this page
  - clip this
  - save to obsidian
  - add to knowledge base
  - save article
  - clip url
  - сохрани страницу
  - добавь в базу знаний
---

# Web Clipper → Obsidian

Converts any web page to clean Markdown and saves it to your Obsidian vault under `Web Clips/`.

## Usage

```bash
# Clip and save to Obsidian (default):
bash /data/bot/openclaw-docker/scripts/web_clip.sh "https://example.com/article"

# Clip with custom size limit (tokens control):
bash /data/bot/openclaw-docker/scripts/web_clip.sh "https://example.com/article" 3000

# Clip and just display (no save):
bash /data/bot/openclaw-docker/scripts/web_clip.sh "https://example.com/article" 3000 false
```

## Arguments

| Argument | Default | Description |
|---|---|---|
| URL | required | Page to clip |
| max_chars | 4000 | Clip size limit (controls token usage) |
| save | true | `true` = save to Obsidian, `false` = print only |

## Where files are saved

```
/data/obsidian/vault/Web Clips/YYYY-MM-DD-<title>.md
```

Each file has frontmatter:
```yaml
---
source: <url>
clipped: <timestamp>
tags: [web-clip]
---
```

## Workflow for building knowledge base

1. User sends URL
2. Agent clips it: `bash web_clip.sh "<url>" 4000 true`
3. Confirm: "✅ Saved to Web Clips/2026-02-25-title.md (N words)"
4. Offer: "Want me to also reindex Obsidian RAG? (`bash obsidian_reindex.sh`)"

## Notes

- Automatically strips JS, CSS, nav, footer — keeps article text only
- max_chars=4000 ≈ ~1000 tokens — keeps responses cheap
- After clipping multiple pages, run reindex to make them searchable via RAG
