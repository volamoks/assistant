# ACPX Provenance Integration Guide

This directory contains the JavaScript provenance module for integration with the acpx ACP server.

## Files

- `provenance.js` - Main provenance module

## Integration Steps

### 1. Copy the Module to Container

Copy `provenance.js` to the acpx extensions directory:

```bash
docker cp openclaw-docker/acpx-integration/provenance.js openclaw:/app/extensions/acpx/provenance.js
```

Or add to volume mount in docker-compose.yml:

```yaml
volumes:
  - ./openclaw-docker/acpx-integration:/app/extensions/acpx
```

### 2. Update ACP Server Code

In the acpx server initialization, add:

```javascript
const { ProvenanceManager, parseProvenanceMode } = require('./provenance');

// Parse --provenance flag
const provenanceIndex = process.argv.indexOf('--provenance');
const provenanceMode = provenanceIndex >= 0 
  ? parseProvenanceMode(process.argv[provenanceIndex + 1])
  : parseProvenanceMode(process.env.OPENCLAW_PROVENANCE);

// Create manager
const provenance = new ProvenanceManager(provenanceMode);

// Capture ingress
provenance.captureIngress({
  sessionKey: options.session,
  cliArgs: process.argv.slice(2),
  workingDirectory: process.cwd()
});
```

### 3. Inject Receipts at Key Points

#### At Session Start
```javascript
// After session initialization
const receipt = provenance.injectIngress(sessionKey);
if (receipt) {
  // Inject into conversation
  conversation.addSystemMessage(receipt);
}
```

#### At Tool Calls
```javascript
// Before tool execution
const receipt = provenance.injectToolCall(toolName, params);
if (receipt) {
  conversation.addSystemMessage(receipt);
}
```

#### At Agent Start
```javascript
const receipt = provenance.injectAgentStart(agentId);
if (receipt) {
  conversation.addSystemMessage(receipt);
}
```

#### At Completion
```javascript
const receipt = provenance.injectCompletion(tokenCount);
if (receipt) {
  conversation.addSystemMessage(receipt);
}
```

#### At Errors
```javascript
const receipt = provenance.injectError(error);
if (receipt) {
  conversation.addSystemMessage(receipt);
}
```

### 4. Propagate to Sub-agents

When spawning sub-agents:

```javascript
const childProvenance = provenance.createChild();
childProvenance.injectSubAgentSpawn(agentId);

// Pass trace context to sub-agent
message.provenance = childProvenance.buildEnvelope();
```

### 5. Attach to Messages

For gateway bridge messages:

```javascript
// Add to message payload
message.provenance = provenance.buildEnvelope();

// Or as headers
websocket.send(JSON.stringify(message), {
  headers: {
    'x-openclaw-trace-id': provenance.getTraceContext().currentTraceId,
    'x-openclaw-provenance-mode': provenance.getTraceContext().mode
  }
});
```

## Environment Variables

- `OPENCLAW_PROVENANCE` - Default provenance mode (off|meta|meta+receipt)
- `OPENCLAW_PROVENANCE_FORMAT` - Receipt format (compact|verbose|json)
- `OPENCLAW_VERSION` - OpenClaw version for metadata

## Example Usage

```bash
# Full provenance with visible receipts
openclaw acp --provenance=meta+receipt --session=main

# Metadata only (no visible receipts)
openclaw acp --provenance=meta --session=main

# No provenance tracking
openclaw acp --provenance=off --session=main
# or
openclaw acp --session=main
```

## Receipt Formats

### Compact (default)
```
[ingress] ACP session started: main
[processing] Tool invoked: read_file
[completion] Response generated (1234 tokens)
```

### Verbose
```
[2024-01-15T10:30:00.000Z] [ingress] ACP session started: main
[2024-01-15T10:30:01.000Z] [processing] Tool invoked: read_file
[2024-01-15T10:30:05.000Z] [completion] Response generated (1234 tokens)
```

### JSON
```json
{"receiptId":"rcpt_1234...","traceId":"tr_5678...","operation":"ingress","timestamp":"2024-01-15T10:30:00.000Z","description":"ACP session started: main","metadata":{"sessionKey":"main"}}
```

## Testing

Test the integration:

```bash
# Start container with mounted provenance module
docker run -v ./openclaw-docker/acpx-integration:/app/extensions/acpx ...

# Test with provenance
docker exec <container> openclaw acp --provenance=meta+receipt --session=test
```
