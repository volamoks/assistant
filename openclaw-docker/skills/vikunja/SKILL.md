---
name: vikunja
description: "Task management via Vikunja API. Create tasks, list tasks, get task details, update tasks, delete tasks, and manage projects/lists. Use for creating todo items, tracking tasks, and task organization."
triggers:
  - task
  - задача
  - todo
  - vikunja
  - create task
  - add task
  - new task
  - list tasks
  - my tasks
  - "/task"
---

# Vikunja Task Management Skill

Vikunja is a self-hosted task management application running at `http://localhost:3456`.

## Setup

The API token is stored in environment variable `VIKUNJA_TOKEN`. Already configured.

## Commands

### List all tasks (inbox)
```bash
bash /home/node/.openclaw/skills/vikunja/vikunja.sh list
```

### List tasks from a specific project/list
```bash
bash /home/node/.openclaw/skills/vikunja/vikunja.sh list-by-project <project_id>
```

### Get task details
```bash
bash /home/node/.openclaw/skills/vikunja/vikunja.sh get <task_id>
```

### Create a new task
```bash
# Basic task
bash /home/node/.openclaw/skills/vikunja/vikunja.sh create "Buy groceries"

# With description
bash /home/node/.openclaw/skills/vikunja/vikunja.sh create "Finish report" "Complete Q4 analysis for meeting"

# With due date (ISO format)
bash /home/node/.openclaw/skills/vikunja/vikunja.sh create "Submit invoice" "Invoice #123" "20246-03-01"

# With priority (1=low, 2=medium, 3=high)
bash /home/node/.openclaw/skills/vikunja/vikunja.sh create "Urgent task" "High priority" "" 3
```

### Update a task
```bash
bash /home/node/.openclaw/skills/vikunja/vikunja.sh update <task_id> "New title"
bash /home/node/.openclaw/skills/vikunja/vikunja.sh update <task_id> "" "New description"
```

### Complete/Delete a task
```bash
# Mark as done
bash /home/node/.openclaw/skills/vikunja/vikunja.sh done <task_id>

# Delete task
bash /home/node/.openclaw/skills/vikunja/vikunja.sh delete <task_id>
```

### List projects
```bash
bash /home/node/.openclaw/skills/vikunja/vikunja.sh projects
```

### Create a project
```bash
bash /home/node/.openclaw/skills/vikunja/vikunja.sh create-project "Work Projects"
```

## API Reference

- Base URL: `http://localhost:3456/api/v1`
- Auth: Bearer token via `VIKUNJA_TOKEN` environment variable
- Endpoints:
  - `GET /tasks` - List all tasks
  - `GET /projects` - List projects
  - `POST /tasks` - Create task
  - `PUT /tasks/:id` - Update task
  - `DELETE /tasks/:id` - Delete task
  - `POST /tasks/:id/done` - Mark task done
  - `POST /tasks/:id/undone` - Mark task undone

## Examples

### Career Agent: Track job applications
```bash
# Create task for job application follow-up
bash /home/node/.openclaw/skills/vikunja/vikunja.sh create "Follow up with Google" "Send follow-up email after interview" "2026-03-05"
```

### Daily task management
```bash
# List today's tasks
bash /home/node/.openclaw/skills/vikunja/vikunja.sh list

# Add new task from conversation
bash /home/node/.openclaw/skills/vikunja/vikunja.sh create "Call dentist" "" "2026-02-28"
```

## Environment

- `VIKUNJA_TOKEN` — API token for authentication (configured)
- `VIKUNJA_URL` — API base URL (default: `http://localhost:3456/api/v1`)
