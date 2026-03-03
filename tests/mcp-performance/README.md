# Composio SDK vs Gemini MCP Performance Comparison

This test setup compares the performance of two approaches for using Composio tools:

1. **Current Approach**: Direct Node.js SDK calling Composio API
2. **New Approach**: Gemini CLI with Composio MCP server

## Prerequisites

- Node.js 18+ installed
- Gemini CLI installed (`npm install -g @google/gemini-cli`)
- Composio API key (`export COMPOSIO_API_KEY='your-key'`)
- Gmail account connected to Composio

## Quick Start

### 1. Configure Gemini with Composio MCP

Run the setup script to add Composio MCP server to Gemini configuration:

```bash
cd tests/mcp-performance
chmod +x setup-gemini-mcp.sh
./setup-gemini-mcp.sh
```

This will:
- Check for Gemini CLI and Composio API key
- Backup existing `~/.gemini/settings.json`
- Add MCP server configuration

### 2. Run Performance Comparison

```bash
node compare.mjs
```

## What is Being Tested

### Test Operations

1. **List Gmail Messages** (read operation)
   - Fetches 5 most recent emails
   - Measures initialization + execution time

2. **Send Email** (write operation - optional)
   - Sends a test email to configured recipient
   - Disabled by default to avoid spam

### Metrics Measured

| Metric | Description |
|--------|-------------|
| **Init Time** | Time to initialize (SDK import / Gemini startup) |
| **Execution Time** | Time to perform the actual operation |
| **Total Time** | Total latency from start to result |

### Test Configuration

Edit `compare.mjs` to customize:

```javascript
const TEST_CONFIG = {
  iterations: 3,        // Number of test runs
  testEmailRecipient: "s7abror@gmail.com",
  skipWriteTests: true, // Set to false to test email sending
};
```

## Understanding Results

### Sample Output

```
=== Direct Composio SDK ===
  Successful runs:               3
  Total time (avg):              2450.50ms
  Init time (avg):               450.20ms
  Execution time (avg):          2000.30ms
  Range:                         2100.00ms - 2800.00ms

=== Gemini CLI with MCP ===
  Successful runs:               3
  Total time (avg):              8500.00ms
  Init time (avg):               2000.00ms
  Execution time (avg):          6500.00ms
  Range:                         7800.00ms - 9200.00ms

=== Comparison ===
⚠ Gemini MCP is 6049.50ms slower (246.9% slower)
ℹ Direct SDK is faster for this operation
```

### Interpretation

**When Direct SDK is faster:**
- Lower-level API access
- No LLM processing overhead
- Better for automated scripts
- Preferred for high-frequency operations

**When Gemini MCP might be preferable:**
- Complex multi-step tasks
- Interactive CLI usage
- Natural language processing needed
- Task decomposition handled automatically

## Architecture Comparison

### Direct SDK Approach

```
Your Code → Composio SDK → HTTP API → Composio → Gmail API
     ↑______________________________________________↓
                    (Direct Response)
```

**Pros:**
- Lower latency
- Direct control
- Better error handling
- Easier debugging

**Cons:**
- Requires coding
- Manual parameter formatting
- No natural language understanding

### Gemini MCP Approach

```
Your Prompt → Gemini CLI → LLM Processing → MCP Server → Composio → Gmail API
                    ↓_________________________________________________↓
                          (Tool Use + Response Generation)
```

**Pros:**
- Natural language interface
- Automatic tool selection
- Multi-step task handling
- No code required for new operations

**Cons:**
- Higher latency (LLM processing)
- Less predictable
- Depends on LLM capabilities
- More complex setup

## Troubleshooting

### Gemini MCP not connecting

Check the MCP server is properly configured:

```bash
# View Gemini settings
cat ~/.gemini/settings.json

# Test MCP server manually
npx -y composio-core@latest mcp start
```

### Composio authentication errors

Ensure your API key is set:

```bash
export COMPOSIO_API_KEY="your-api-key"
echo $COMPOSIO_API_KEY
```

### Gmail not connected

Check connected accounts in Composio:

```bash
npx composio-core@latest connections list
```

## File Structure

```
tests/mcp-performance/
├── README.md              # This file
├── setup-gemini-mcp.sh    # Configuration script
├── compare.mjs            # Performance test runner
└── results.json           # Generated after test run
```

## Next Steps

Based on test results:

1. **If SDK is significantly faster** (>50%):
   - Keep using SDK for programmatic automation
   - Use Gemini MCP only for interactive CLI tasks

2. **If MCP is comparable** (within 50%):
   - Consider MCP for tasks requiring LLM reasoning
   - Use SDK for simple, repetitive operations

3. **If MCP is faster**:
   - Investigate further with more complex operations
   - Consider migration strategy

## Additional Resources

- [Composio Documentation](https://docs.composio.dev)
- [Gemini CLI Documentation](https://github.com/google-gemini/gemini-cli)
- [MCP Protocol Specification](https://modelcontextprotocol.io)

## Notes

- This is a proof-of-concept test, not a full benchmark
- Results may vary based on network conditions
- MCP performance depends on LLM response times
- Always back up your Gemini settings before changes
