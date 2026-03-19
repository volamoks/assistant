---
name: notion-read
description: Read Notion pages and databases. Use when user asks to get Notion page, query database, or find information in Notion. Examples: "get Notion page X", "query Notion database", "search Notion for Y"
---

# Notion Reader

## Credentials

Read from env:
- `NOTION_API_KEY` — from https://www.notion.so/my-integrations
- Database IDs need to be provided by user

## API Endpoints

Base: https://api.notion.com/v1
Header: `Notion-Version: 2022-06-28`

## Common Operations

### Get current bot
```bash
curl -s -H "Authorization: Bearer $NOTION_API_KEY" \
  -H "Notion-Version: 2022-06-28" \
  "https://api.notion.com/v1/users/me"
```

### Search all
```bash
curl -s -H "Authorization: Bearer $NOTION_API_KEY" \
  -H "Notion-Version: 2022-06-28" \
  -X POST "https://api.notion.com/v1/search" \
  -d '{"query":"search-term"}'
```

### Get page
```bash
curl -s -H "Authorization: Bearer $NOTION_API_KEY" \
  -H "Notion-Version: 2022-06-28" \
  "https://api.notion.com/v1/pages/{page-id}"
```

### Get database
```bash
curl -s -H "Authorization: Bearer $NOTION_API_KEY" \
  -H "Notion-Version: 2022-06-28" \
  "https://api.notion.com/v1/databases/{database-id}"
```

### Query database
```bash
curl -s -H "Authorization: Bearer $NOTION_API_KEY" \
  -H "Notion-Version: 2022-06-28" \
  -X POST "https://api.notion.com/v1/databases/{database-id}/query" \
  -d '{}'
```

## Known Databases

- Tasks Tracker: `1917b580-3119-8024-849b-dd6e44fe5e8c`
- Projects: `1d17b580-3119-8093-9be5-f78209ff1102`

## Notes

- Integration must be connected to page/database via "Connect to" menu
- Page IDs start with page- prefix in URLs
- Database IDs are 32 hex chars
