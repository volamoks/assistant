---
name: jira-task
description: Create, list, update Jira tasks. Use when user asks to create, view, update, or search Jira tasks. Examples: "create Jira task", "list my Jira tasks", "update task CP-123 to done", "show all tasks in project CP"
---

# Jira Task Manager

## Credentials

Read from env:
- `JIRA_URL` — e.g. https://ucmg.atlassian.net
- `JIRA_EMAIL` — your Atlassian email
- `JIRA_API_TOKEN` — from https://id.atlassian.com/manage-profile/security/api-tokens

## API Endpoints

Base: `{JIRA_URL}/rest/api/3`

## Common Operations

### Get current user
```bash
curl -s -u "$JIRA_EMAIL:$JIRA_API_TOKEN" \
  "{JIRA_URL}/rest/api/3/myself"
```

### List projects
```bash
curl -s -u "$JIRA_EMAIL:$JIRA_API_TOKEN" \
  "{JIRA_URL}/rest/api/3/project"
```

### Create issue
```bash
curl -s -u "$JIRA_EMAIL:$JIRA_API_TOKEN" \
  -X POST "{JIRA_URL}/rest/api/3/issue" \
  -H "Content-Type: application/json" \
  -d '{
    "fields": {
      "project": {"key": "CP"},
      "summary": "Task title",
      "description": {"type":"doc","version":1,"content":[{"type":"paragraph","content":[{"type":"text","text":"Description"}]}]},
      "issuetype": {"name": "Task"}
    }
  }'
```

### Search issues (JQL)
```bash
curl -s -u "$JIRA_EMAIL:$JIRA_API_TOKEN" \
  "{JIRA_URL}/rest/api/3/search?jql=assignee=currentUser()"
```

### Update issue
```bash
curl -s -u "$JIRA_EMAIL:$JIRA_API_TOKEN" \
  -X PUT "{JIRA_URL}/rest/api/3/issue/{issue-key}" \
  -H "Content-Type: application/json" \
  -d '{"fields": {"summary": "New summary"}}'
```

### Transition issue (change status)
```bash
# First get transitions
curl -s -u "$JIRA_EMAIL:$JIRA_API_TOKEN" \
  "{JIRA_URL}/rest/api/3/issue/{issue-key}/transitions"

# Then transition
curl -s -u "$JIRA_EMAIL:$JIRA_API_TOKEN" \
  -X POST "{JIRA_URL}/rest/api/3/issue/{issue-key}/transitions" \
  -H "Content-Type: application/json" \
  -d '{"transition":{"id":"11"}}'
```

## Available Projects

| Key | Name |
|-----|------|
| ET | UI |
| YTASK | Y Board |
| AA | A2A |
| CP | Credit product |
| ETH | ETHICAL |
| ID | Interest on Debit |

## Rules

- Always confirm with user before creating issues
- Use project key from table above
- Default issue type: Task
- Check status transitions available for each project
