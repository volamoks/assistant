# obsidian_search

Semantic search over the Obsidian vault using local RAG (ChromaDB + nomic-embed-text).

## Tool: obsidian_search

Searches the vault for contextually similar content.

### Arguments

- `query` (string, required): The search query or question.
- `limit` (number, optional): Max results to return. Default: 3.

### Returns

Relevant markdown excerpts from vault notes with their source file paths.

### Example

```json
{ "query": "user preferences for coding", "limit": 3 }
```

### Notes

- Uses vector embeddings — finds semantically similar content even without exact keyword match
- Vault: `/data/obsidian/vault`
- Index: ChromaDB `obsidian_vault` collection (106 chunks)
- Re-indexed nightly at 03:00 Asia/Tashkent
- Depends on: ChromaDB at `http://chromadb:8000`, Ollama at `http://host.docker.internal:11434`
