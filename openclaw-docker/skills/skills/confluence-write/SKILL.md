---
name: confluence-write
description: Push Obsidian markdown to Confluence (live edit). Examples: "push to Confluence", "sync note to Confluence", "publish to Confluence page", "write /data/obsidian/... to Confluence page LP/Data Model"
---

# Confluence Write — Push Obsidian → Confluence

## Credentials

Read from env (`/data/bot/openclaw-docker/core/.env`):
- `CONFLUENCE_URL` — e.g. https://ucmg.atlassian.net/wiki
- `CONFLUENCE_EMAIL` — your Atlassian email
- `CONFLUENCE_API_TOKEN` — same as Jira token

## How It Works

1. Read markdown from Obsidian path
2. Convert markdown → HTML (via `markdown` library)
3. Push to Confluence via `editor` representation (live edit — not draft)

**Important:** Uses `representation: editor` (Confluence Editor HTML), not `storage` (XHTML) or `atlas_doc_format` (ADF).

## Usage

```bash
PYTHONPATH=/home/node/.openclaw/pypackages \
  python3 /home/node/.openclaw/scripts/confluence_push.py \
  --file "/data/obsidian/vault/SomeNote.md" \
  --page-id "359268353"
```

```bash
# By title in space
PYTHONPATH=/home/node/.openclaw/pypackages \
  python3 /home/node/.openclaw/scripts/confluence_push.py \
  --file "/data/obsidian/vault/SomeNote.md" \
  --space "LP" \
  --title "Some Note Title"
```

```bash
# Create new page
PYTHONPATH=/home/node/.openclaw/pypackages \
  python3 /home/node/.openclaw/scripts/confluence_push.py \
  --file "/data/obsidian/vault/SomeNote.md" \
  --space "LP" \
  --title "New Page Title" \
  --create
```

## What Gets Converted

| Markdown | Output |
|----------|--------|
| `**bold**` | `<strong>bold</strong>` |
| `*italic*` | `<em>italic</em>` |
| `` `code` `` | `<code>code</code>` |
| ` ```sql ... ``` ` | `<pre class="code-block"><code class="language-sql">...</code></pre>` |
| `# Heading` | `<h1>Heading</h1>` |
| `---` | `<hr>` |
| `| col | col |` | `<table>...</table>` |
| `[text](url)` | `<a href="url">text</a>` |

## Known Pages

| Page | ID | Space |
|------|----|-------|
| UzCard Loyalty Platform — Data Model | 359268353 | LP |

## Rules

1. **Version is always fetched dynamically** — never hardcode version number
2. **Use `editor` representation** — not `storage` or `atlas_doc_format`
3. **Use env vars from .env** — never hardcode tokens
4. **Test with small content first**
