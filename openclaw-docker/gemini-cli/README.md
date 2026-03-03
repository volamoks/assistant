# Gemini CLI Docker Service

Containerized Google Gemini CLI with MCP (Model Context Protocol) support for OpenClaw.

## Quick Start

```bash
# Build and start the service
cd openclaw-docker
docker compose up -d gemini-cli

# Access Gemini CLI interactively
docker compose exec -it gemini-cli gemini

# Run a single command
docker compose exec gemini-cli gemini "Your prompt here"
```

## Features

- **Gemini CLI**: Full Google Gemini CLI access
- **MCP Support**: Integrated Composio MCP server for tool use
- **Network Access**: Shares network with other OpenClaw services
- **Volume Mounts**: Access to shared data directories

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `COMPOSIO_API_KEY` | Composio API key for MCP tools | Yes |
| `GEMINI_API_KEY` | Google Gemini API key (optional, uses OAuth flow) | No |

## Configuration

MCP configuration is automatically generated at startup from the template. The Composio MCP server will be configured if `COMPOSIO_API_KEY` is provided.

## Access from Other Services

### From OpenClaw container:
```bash
docker compose exec gemini-cli gemini "Your prompt"
```

### Using wrapper script:
```bash
./gemini-cli/gemini-wrapper.sh "Your prompt"
```

## Available Tools via MCP

When Composio is configured, Gemini CLI can access:
- Gmail (send/search emails)
- Notion (pages, databases)
- GitHub (repos, issues, PRs)
- Slack (messages, channels)
- And 100+ other integrations

## Troubleshooting

### Check service status:
```bash
docker compose ps gemini-cli
docker compose logs gemini-cli
```

### Verify MCP configuration:
```bash
docker compose exec gemini-cli cat ~/.gemini/settings.json
```

### Test Composio connection:
```bash
docker compose exec gemini-cli composio --version
```

## Files

- `Dockerfile` - Container image definition
- `entrypoint.sh` - Initialization script
- `mcp-config.json` - MCP server configuration template
- `gemini-wrapper.sh` - Wrapper for external access
