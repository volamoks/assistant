---
name: Plaud Note Integration
description: Interact with Plaud Note AI recorder via plaud-unofficial API.
---

# Plaud Note Skill

This skill allows agents to sync, retrieve, and summarize recordings from Plaud Note devices using the `plaud-unofficial` package.

## Capabilities
- `plaud.sync`: Sync latest recordings.
- `plaud.list`: List recent recordings.
- `plaud.summary`: Get AI summary of a recording.

## Usage
Run via `shell.execute`:
```bash
node skills/plaud/scripts/plaud.mjs [command] [args]
```

## Setup
Requires `PLAUD_USERNAME` and `PLAUD_PASSWORD` env vars.
