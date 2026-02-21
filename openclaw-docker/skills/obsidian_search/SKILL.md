---
name: obsidian_search
description: "Search the local Obsidian vault using semantic RAG (Retrieval-Augmented Generation) to find relevant user context, preferences, and historical notes."
version: 1.0.0
---

# Obsidian Memory Search
This skill allows agents to semantically search the user's localized Obsidian vault to retrieve long-term memory, project specifications, and user preferences. It uses local embeddings (ChromaDB + Ollama) to guarantee privacy and reduce context window costs.

## Tool 1: obsidian_search
- **Description**: Searches the Obsidian vault for semantically similar content based on a query string. Use this when you need background information, user preferences, or historical context.
- **Arguments**:
  - `query` (string): The search query or question (e.g., "What are the user's preferred frontend frameworks?").
  - `limit` (number, optional): The maximum number of relevant document chunks to return. Defaults to 3.
