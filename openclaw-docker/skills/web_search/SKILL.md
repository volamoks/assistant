---
name: web_search
description: Search the web using SearXNG (self-hosted). Returns titles, URLs, and snippets from Google, DuckDuckGo, Wikipedia and other engines.
triggers:
  - web search
  - search the web
  - find online
  - look up online
  - google
---

# Web Search via SearXNG

Self-hosted meta-search. No API key needed. **Token-efficient by default** — returns only titles + URLs + short snippets.

## Basic search (low token cost ≈ 300–500 tokens)

```bash
curl -s "http://searxng:8080/search?q=QUERY&format=json&language=en" \
  | python3 -c "
import json, sys
d = json.load(sys.stdin)
for r in d['results'][:5]:
    print(f\"### {r['title']}\")
    print(f\"URL: {r['url']}\")
    print(f\"{r.get('content','')[:200]}\")
    print()
"
```

Replace `QUERY` with URL-encoded search terms.

## Fetch full page content (for deeper research)

**PinchTab — primary (fast, ~800 tokens, accessibility tree):**

```bash
PT="bash /data/bot/openclaw-docker/skills/browser-automation/pinchtab.sh"
$PT navigate "URL_HERE"
$PT text           # clean text, ~800 tokens
$PT snapshot       # structured accessibility tree
```

**web_clip.sh — for JS-heavy pages or saving to Obsidian:**

```bash
# Read inline (2000 chars ≈ 500 tokens):
bash /data/bot/openclaw-docker/scripts/web_clip.sh "URL_HERE" 2000 false

# Save to Obsidian for later reference:
bash /data/bot/openclaw-docker/scripts/web_clip.sh "URL_HERE" 4000 true
```

> `web_clip.sh` tries PinchTab first, then Crawl4AI. Never starts Crawl4AI unnecessarily.

## Token-saving strategy

| Need | Command | ~Tokens |
|---|---|---|
| Quick answer | SearXNG search (5 results) | 300–500 |
| Read one page | `pinchtab.sh navigate + text` | ~800 |
| Save article | `web_clip.sh url 4000 true` | 0 (saved to Obsidian) |
| Deep research | search + pinchtab top 2–3 pages | 1500–2500 |

**Rule:** PinchTab for page content. SearXNG for search. Never use paid APIs — we run everything locally.

## Options

- `&language=en` — language (en, ru, uz, etc.)
- `&time_range=day` — filter: day, week, month, year
- `&categories=general` — categories: general, news, images, science, it
- `&engines=google,duckduckgo` — specific engines

## Examples

Search recent news:
```bash
curl -s "http://searxng:8080/search?q=OpenAI+news&format=json&time_range=week&categories=news" \
  | python3 -c "import json,sys; [print(r['title'], '\n', r['url'], '\n') for r in json.load(sys.stdin)['results'][:5]]"
```

## Notes

- Internal URL: `http://searxng:8080` (Docker network)
- External URL: `http://localhost:3017` (host)
- JSON format enabled in settings.yml
- Sources: Google, DuckDuckGo, Wikipedia, Bing
