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

Self-hosted meta-search. No API key needed.

## Usage

```bash
curl -s "http://searxng:8080/search?q=QUERY&format=json&language=en" \
  | python3 -c "
import json, sys
d = json.load(sys.stdin)
for r in d['results'][:5]:
    print(f\"### {r['title']}\")
    print(f\"URL: {r['url']}\")
    print(f\"{r.get('content','')[:300]}\")
    print()
"
```

Replace `QUERY` with URL-encoded search terms.

## Options

- `&language=en` — language (en, ru, uz, etc.)
- `&time_range=day` — filter by time: day, week, month, year
- `&categories=general` — categories: general, news, images, science, it
- `&engines=google,duckduckgo` — specific engines

## Examples

Search recent news:
```bash
curl -s "http://searxng:8080/search?q=OpenAI+news&format=json&time_range=week&categories=news" \
  | python3 -c "import json,sys; [print(r['title'], '\n', r['url'], '\n') for r in json.load(sys.stdin)['results'][:5]]"
```

Search and get full snippets:
```bash
curl -s "http://searxng:8080/search?q=YOUR+QUERY+HERE&format=json" \
  | python3 -c "
import json, sys, urllib.parse
d = json.load(sys.stdin)
print(f'Found {len(d[\"results\"])} results')
for i, r in enumerate(d['results'][:7], 1):
    print(f'{i}. {r[\"title\"]}')
    print(f'   {r[\"url\"]}')
    if r.get('content'):
        print(f'   {r[\"content\"][:200]}')
    print()
"
```

## Notes

- Internal URL: `http://searxng:8080` (from inside Docker network)
- External URL: `http://localhost:3017` (from host)
- JSON format must be enabled in settings.yml (already done)
- Results from multiple engines: Google, DuckDuckGo, Wikipedia, Bing
