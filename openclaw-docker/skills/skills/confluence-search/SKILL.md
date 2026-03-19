---
name: confluence-search
description: Search and read Confluence pages. Use when user asks to search Confluence, get page content, or find documentation. Examples: "search Confluence for X", "get Confluence page about Y", "find API docs"
---

# Confluence Search

## Credentials

Read from env:
- `CONFLUENCE_URL` — e.g. https://ucmg.atlassian.net/wiki
- `CONFLUENCE_EMAIL` — your Atlassian email
- `CONFLUENCE_API_TOKEN` — same as Jira token

## API Endpoints

Base: `{CONFLUENCE_URL}/rest/api`

## Common Operations

### Get current user
```bash
curl -s -u "$CONFLUENCE_EMAIL:$CONFLUENCE_API_TOKEN" \
  "{CONFLUENCE_URL}/rest/api/user/current"
```

### List spaces
```bash
curl -s -u "$CONFLUENCE_EMAIL:$CONFLUENCE_API_TOKEN" \
  "{CONFLUENCE_URL}/rest/api/space"
```

### Search pages (CQL)
```bash
curl -s -u "$CONFLUENCE_EMAIL:$CONFLUENCE_API_TOKEN" \
  "{CONFLUENCE_URL}/rest/api/search?cql=text~'search-term'"
```

### Get page content
```bash
curl -s -u "$CONFLUENCE_EMAIL:$CONFLUENCE_API_TOKEN" \
  "{CONFLUENCE_URL}/rest/api/content/{page-id}?expand=body.storage,version"
```

### Get page by title
```bash
curl -s -u "$CONFLUENCE_EMAIL:$CONFLUENCE_API_TOKEN" \
  "{CONFLUENCE_URL}/rest/api/content?title=PageName&spaceKey=SPACE"
```

## Available Spaces

| Key | Name |
|-----|------|
| A2A | A2A |
| CPAS | Credit products and solutions |
| CX | CUSTOMER EXCELLENCE |
| Autopaytok | Autopay.token |

## Rules

- Use CQL (Confluence Query Language) for search
- Page content is in body.storage.value (HTML)
- Space key required for exact title lookups
