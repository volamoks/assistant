---
name: model-benchmark
description: "Ping test different AI models to measure latency. Useful for comparing speed of free models across providers."
triggers:
  - /ping
  - /benchmark
  - /model ping
  - test model speed
  - model latency
---

# /ping — Model Benchmark

Ping test different AI models to measure their response latency.

## Available Models to Test

### OpenCode (FREE - ~700ms):
- nemotron-3-super-free (fastest!)
- trinity-large-preview-free
- minimax-m2.5-free
- mimo-v2-flash-free

### MiniMax Portal (Your Plan - ~1100ms):
- MiniMax-M2.5-Highspeed
- MiniMax-M2.5-Lightning

### Ollama Cloud (~3000-8000ms):
- kimi-k2.5:cloud (requires ollama login)

### Kilocode (~1000-10000ms):
- nvidia/nemotron-3-super-120b-a12b:free
- kilo-auto/free

## Steps

1. **Run ping test** using curl with timing:
   
   For OpenCode models:
   ```bash
   curl -s "https://opencode.ai/zen/v1/chat/completions" \
     -H "Authorization: Bearer <API_KEY>" \
     -H "Content-Type: application/json" \
     -d '{"model": "nemotron-3-super-free", "messages": [{"role": "user", "content": "ok"}], "max_tokens": 5}'
   ```
   
   API Keys (already configured in environment):
   - OpenCode: `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJlbnYiOiJwcm9kdWN0aW9uIiwia2lsb1VzZXJJZCI6ImFjMDNkMDQyLWU1YTYtNGE5My05Yzc0LTZkYTYzZDQ2MTNjNiIsImFwaVRva2VuUGVwcGVyIjpudWxsLCJ2ZXJzaW9uIjozLCJpYXQiOjE3NzM0ODMzNTEsImV4cCI6MTkzMTE2MzM1MX0.pU6c_h5qOcaSUeLigeHahVG6vyBautBzkoGZQE26pzg`

2. **Run multiple times** (at least 3) to get average latency

3. **Report results** in this format:

```
📊 Model Benchmark Results:

| Model | Latency (ms) |
|-------|-------------|
| nemotron-3-super-free | ~700 |
| MiniMax-Highspeed | ~1100 |
| ... | ... |

🏆 Fastest: <model>
```

## Example

When user says "/ping" or "/benchmark", run tests for these models:
- OpenCode: nemotron-3-super-free
- MiniMax: M2.5-Highspeed

Return a summary table with latencies.
