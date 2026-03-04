---
name: python-coding
description: "Standards and patterns for writing Python scripts in the OpenClaw ecosystem. Use when creating new Python-based skills or scripts. Follows debate.py patterns: type hints, docstrings, environment variables, HTTP timeouts, parallel execution."
triggers:
  - python coding
  - write python script
  - python standards
  - type hints
  - function docstrings
---

# Python Coding Standards

Coding standards for Python scripts in the OpenClaw ecosystem, based on patterns from [`debate.py`](openclaw-docker/skills/debate/debate.py:1).

## Required Patterns

### 1. Type Hints (Mandatory)

All function parameters and return types must be annotated:

```python
from pathlib import Path
from typing import Optional, List, Dict, Any

def call_llm(model: str, system: str, user: str, temperature: float = 0.7) -> str:
    ...

def get_rag_context(topic: str) -> str:
    ...

def run_debate(task: str, model: str = DEFAULT_MODEL, rounds: int = 2) -> str:
    ...
```

### 2. Google-Style Docstrings

Use Google-style docstrings for all public functions:

```python
def summarize(text: str) -> str:
    """Compress a debate response to ~150 tokens (3-5 bullet key points).
    
    Uses a cheaper/faster model (qwen3.5-plus) to reduce costs while
    preserving key arguments for context passing between rounds.
    
    Args:
        text: The text to summarize.
        
    Returns:
        Summarized text as bullet points.
    """
    ...
```

### 3. Environment Variables with Defaults

Use `os.environ.get()` with sensible defaults for all configuration:

```python
import os

LITELLM_BASE = os.environ.get("LITELLM_BASE", "http://litellm-proxy:4000")
LITELLM_KEY  = os.environ.get("LITELLM_MASTER_KEY", "")
DEFAULT_MODEL = "minimax/MiniMax-M2.5"
OUTPUT_DIR = Path("/home/node/.openclaw/workspace-main/skills/debate-agents")
```

### 4. HTTP Requests with Timeouts and Error Handling

Always set timeouts and use `raise_for_status()`:

```python
import requests

def call_llm(model: str, system: str, user: str, temperature: float = 0.7) -> str:
    headers = {"Content-Type": "application/json"}
    if LITELLM_KEY:
        headers["Authorization"] = f"Bearer {LITELLM_KEY}"
    
    resp = requests.post(
        f"{LITELLM_BASE}/chat/completions",
        headers=headers,
        json={
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user",   "content": user},
            ],
            "temperature": temperature,
            "stream": False,
        },
        timeout=120,  # 120 second timeout for LLM calls
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]
```

### 5. Constants in UPPER_CASE at Module Level

```python
# ── Config ────────────────────────────────────────────────────────────────────

LITELLM_BASE = os.environ.get("LITELLM_BASE", "http://litellm-proxy:4000")
LITELLM_KEY  = os.environ.get("LITELLM_MASTER_KEY", "")
DEFAULT_MODEL = "minimax/MiniMax-M2.5"
OUTPUT_DIR = Path("/home/node/.openclaw/workspace-main/skills/debate-agents")
SUMMARY_MODEL = "qwen3.5-plus"  # Cheap/fast model for summarization
```

### 6. Small, Focused Functions

Functions should do one thing well. Example from [`debate.py`](openclaw-docker/skills/debate/debate.py:74):

```python
def get_rag_context(topic: str) -> str:
    """Pull 2 relevant chunks from Obsidian ChromaDB vault."""
    try:
        ollama = os.environ.get("OLLAMA_HOST", "http://host.docker.internal:11434")
        chroma = os.environ.get("CHROMA_HOST", "http://chromadb:8000")

        emb = requests.post(
            f"{ollama}/api/embeddings",
            json={"model": "nomic-embed-text", "prompt": topic},
            timeout=8,
        ).json()["embedding"]

        coll_id = requests.get(
            f"{chroma}/api/v1/collections/obsidian_vault", timeout=5
        ).json()["id"]

        docs = requests.post(
            f"{chroma}/api/v1/collections/{coll_id}/query",
            json={"query_embeddings": [emb], "n_results": 2},
            timeout=8,
        ).json()["documents"][0]

        if docs:
            return "\n\nRelevant context from your notes:\n" + "\n---\n".join(
                d[:400] for d in docs
            )
    except Exception:
        pass
    return ""
```

### 7. Parallel Execution with ThreadPoolExecutor

Use [`ThreadPoolExecutor`](openclaw-docker/skills/debate/debate.py:162) for parallel operations:

```python
from concurrent.futures import ThreadPoolExecutor

# Both agents run in parallel every round
with ThreadPoolExecutor(max_workers=2) as ex:
    f_p = ex.submit(call_llm, model, p_sys, p_usr)
    f_c = ex.submit(call_llm, model, c_sys, c_usr)
    p_resp = f_p.result()
    c_resp = f_c.result()

# Summarization also runs in parallel
with ThreadPoolExecutor(max_workers=2) as ex:
    f_ps = ex.submit(summarize, p_resp)
    f_cs = ex.submit(summarize, c_resp)
    proposer_sum = f_ps.result()
    critic_sum = f_cs.result()
```

### 8. Standard Imports Pattern

Follow the existing import pattern:

```python
#!/usr/bin/env python3
"""Module docstring describing purpose and usage."""

# Standard library imports
import argparse
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

# Third-party imports
import requests
```

### 9. Logging Instead of Print Statements

For production skills, use the `logging` module instead of print:

```python
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Use logger.info(), logger.error(), etc.
logger.info(f"Round {r}/{rounds}")
```

For simple scripts, print statements with emojis are acceptable as seen in [`debate.py`](openclaw-docker/skills/debate/debate.py:108).

### 10. JSON Handling Pattern

Always use `raise_for_status()` before parsing JSON:

```python
resp = requests.post(url, json=payload, timeout=30)
resp.raise_for_status()
data = resp.json()
```

## Complete Example Template

```python
#!/usr/bin/env python3
"""
skill_name.py — Brief description of what this skill does.

Usage:
  python3 skill_name.py "required argument"
  python3 skill_name.py "argument" --option value
"""

import argparse
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Optional

import requests

# ── Config ────────────────────────────────────────────────────────────────────

API_BASE = os.environ.get("API_BASE", "http://default:8080")
API_KEY = os.environ.get("API_KEY", "")
DEFAULT_TIMEOUT = 30
OUTPUT_DIR = Path("/home/node/.openclaw/workspace-main/skills/output")


# ── Core Functions ────────────────────────────────────────────────────────────

def fetch_data(query: str, timeout: int = DEFAULT_TIMEOUT) -> dict:
    """Fetch data from the API.
    
    Args:
        query: The search query.
        timeout: Request timeout in seconds.
        
    Returns:
        JSON response as dictionary.
        
    Raises:
        requests.RequestException: If the request fails.
    """
    headers = {"Content-Type": "application/json"}
    if API_KEY:
        headers["Authorization"] = f"Bearer {API_KEY}"
    
    resp = requests.post(
        f"{API_BASE}/endpoint",
        headers=headers,
        json={"query": query},
        timeout=timeout,
    )
    resp.raise_for_status()
    return resp.json()


def process_item(item: dict) -> str:
    """Process a single item.
    
    Args:
        item: The item to process.
        
    Returns:
        Processed result string.
    """
    return str(item.get("value", ""))


def run_parallel(items: list[dict], max_workers: int = 4) -> list[str]:
    """Process items in parallel.
    
    Args:
        items: List of items to process.
        max_workers: Maximum number of parallel workers.
        
    Returns:
        List of processed results.
    """
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futures = [ex.submit(process_item, item) for item in items]
        return [f.result() for f in futures]


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Brief description")
    parser.add_argument("query", help="Search query")
    parser.add_argument("--workers", type=int, default=4, help="Parallel workers")
    args = parser.parse_args()
    
    # Implementation here
    result = fetch_data(args.query)
    print(f"Found {len(result)} results")


if __name__ == "__main__":
    main()
```

## References

- [`debate.py`](openclaw-docker/skills/debate/debate.py:1) — Full example of all patterns
- [`obsidian_index.py`](openclaw-docker/scripts/obsidian_index.py:1) — Database and indexing patterns
