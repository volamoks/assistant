"""
CocoIndex flow for indexing the bot's codebase.

Usage:
  Setup:  COCOINDEX_DATABASE_URL=... cocoindex setup  scripts/cocoindex_flow.py
  Index:  COCOINDEX_DATABASE_URL=... cocoindex update scripts/cocoindex_flow.py
  Server: COCOINDEX_DATABASE_URL=... cocoindex server scripts/cocoindex_flow.py --port 18793
  Search: python3 scripts/cocoindex_flow.py "your query"
"""

import os
import cocoindex

CODEBASE_PATH = "/Users/abror_mac_mini/Projects/bot"
INCLUDE_PATTERNS = [
    "**/*.ts", "**/*.py", "**/*.md", "**/*.sh",
    "**/*.yaml", "**/*.yml", "**/*.json", "**/*.toml",
]
EXCLUDE_PATTERNS = [
    "**/node_modules/**", "**/.git/**", "**/__pycache__/**",
    "**/dist/**", "**/.pnpm/**", "**/build/**",
    "**/*.lock", "**/*.min.js", "**/*.jsonl",
]


@cocoindex.flow_def(name="BotCodebase")
def bot_codebase_flow(
    flow_builder: cocoindex.FlowBuilder,
    data_scope: cocoindex.DataScope,
):
    """Index the openclaw-docker bot codebase for semantic code search."""

    data_scope["files"] = flow_builder.add_source(
        cocoindex.sources.LocalFile(
            path=CODEBASE_PATH,
            included_patterns=INCLUDE_PATTERNS,
            excluded_patterns=EXCLUDE_PATTERNS,
            binary=False,
        )
    )

    # Split into chunks by language
    chunks = data_scope["files"].transform(
        "SplitRecursively",
        cocoindex.functions.SplitRecursively(),
        language=cocoindex.typing.deduce(),
        text=cocoindex.typing.deduce(),
    )

    # Embed with nomic-embed-text via Ollama (768-dim)
    chunks["embedding"] = chunks["text"].transform(
        "Embed",
        cocoindex.functions.EmbedText(
            api_type=cocoindex.llm.LlmApiType.OLLAMA,
            model="nomic-embed-text",
            address="http://localhost:11434",
        ),
    )

    # Store in pgvector
    chunks.export(
        "BotCodebaseEmbeddings",
        cocoindex.storages.Postgres(),
        primary_key_fields=["filename", "location"],
        vector_index=[
            cocoindex.VectorIndexDef(
                field="embedding",
                metric=cocoindex.VectorSimilarityMetric.COSINE_SIMILARITY,
            )
        ],
    )


def search(query: str, top_k: int = 8) -> list[dict]:
    """Search the indexed codebase by semantic similarity."""
    query_embedding = cocoindex.functions.EmbedText(
        api_type=cocoindex.llm.LlmApiType.OLLAMA,
        model="nomic-embed-text",
        address="http://localhost:11434",
    ).embed(query)

    results = cocoindex.query.search(
        "BotCodebaseEmbeddings",
        "embedding",
        query_embedding,
        top_k,
        result_fields=["filename", "location", "text"],
    )

    return [
        {
            "file": r["filename"],
            "location": str(r["location"]),
            "score": round(r["_score"], 3),
            "text": r["text"][:400],
        }
        for r in results
    ]


if __name__ == "__main__":
    import sys

    os.environ.setdefault(
        "COCOINDEX_DATABASE_URL",
        "postgresql://cocoindex:cocoindex@localhost:15432/cocoindex",
    )

    query = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "LCM context compression"
    print(f"🔍 Searching: {query!r}\n")

    for r in search(query):
        print(f"[{r['score']}] {r['file']}  @ {r['location']}")
        print(f"  {r['text'][:150].strip()}")
        print()
