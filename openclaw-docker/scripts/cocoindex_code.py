"""
CocoIndex — индексация кодовой базы бота через nomic-embed-text (LiteLLM)
Запуск: docker exec openclaw-latest python3 /data/bot/openclaw-docker/scripts/cocoindex_code.py
Обновление (инкрементальное): тот же запуск, только изменённые файлы пересчитаются
"""

import cocoindex

LITELLM_URL = "http://litellm:4000"
LITELLM_KEY = "sk-litellm-openclaw-proxy"
SOURCE_PATH = "/data/bot/openclaw-docker"
EMBED_DIM = 768

# Только реальный исходный код
INCLUDED = [
    "*.ts", "*.py", "*.sh", "*.md", "*.yaml", "*.yml",
    "**/*.ts", "**/*.py", "**/*.sh", "**/*.md", "**/*.yaml", "**/*.yml",
]

# Мусор пропускаем
EXCLUDED = [
    # зависимости и сборка
    "**/node_modules/**", "**/dist/**", "**/build/**",
    "**/__pycache__/**", "**/*.pyc",
    # данные и рантайм
    "**/memory/**", "**/workspace/**", "**/workspace-*/**",
    "**/pip/**", "**/pip-packages/**",
    "**/chroma/**", "**/redis-data/**", "**/langfuse-data/**",
    "**/beszel_agent_data/**", "**/actual-data/**",
    "**/ollama/**", "**/open-webui/**", "**/homebridge/**",
    "**/logs/**", "**/*.log",
    # сторонние либы и кэши
    "**/extensions/**", "**/vendor/**",
    "**/opencode-cache/**",
    "**/skills/docs/**",
    # скомпилированный JS (оставляем только .ts)
    "**/*.js",
    # тесты и декларации типов
    "**/*.test.ts", "**/*.spec.ts", "**/*.d.ts",
    "**/*.test.py", "**/*.spec.py",
    # git
    "**/.git/**",
    # большие бинарники и БД
    "**/*.db", "**/*.db-shm", "**/*.db-wal",
    "**/*.whl", "**/*.tar.gz",
]


@cocoindex.flow_def(name="BotCodeFlow")
def code_flow(flow_builder: cocoindex.FlowBuilder, data_scope: cocoindex.DataScope):
    cocoindex.add_auth_entry("litellm_key", LITELLM_KEY)

    data_scope["files"] = flow_builder.add_source(
        cocoindex.sources.LocalFile(
            path=SOURCE_PATH,
            included_patterns=INCLUDED,
            excluded_patterns=EXCLUDED,
        )
    )

    collector = data_scope.add_collector()

    with data_scope["files"].row() as doc:
        doc["chunks"] = doc["content"].transform(
            cocoindex.functions.SplitRecursively(),
            chunk_size=500,
            chunk_overlap=80,
        )

        with doc["chunks"].row() as chunk:
            chunk["embedding"] = chunk["text"].transform(
                cocoindex.functions.EmbedText(
                    api_type=cocoindex.LlmApiType.OPENAI,
                    model="nomic-embed-text",
                    address=LITELLM_URL,
                    output_dimension=EMBED_DIM,
                    api_key=cocoindex.ref_auth_entry("litellm_key"),
                )
            )
            collector.collect(
                filename=doc["filename"],
                location=chunk["location"],
                text=chunk["text"],
                embedding=chunk["embedding"],
            )

    collector.export(
        "bot_code_chunks",
        cocoindex.storages.Postgres(),
        primary_key_fields=["filename", "location"],
        vector_indexes=[
            cocoindex.VectorIndexDef(
                field_name="embedding",
                metric=cocoindex.VectorSimilarityMetric.COSINE_SIMILARITY,
            )
        ],
    )


def search(query: str, limit: int = 5):
    """Семантический поиск по кодовой базе."""
    import urllib.request, json, psycopg2

    payload = json.dumps({"model": "nomic-embed-text", "input": query}).encode()
    req = urllib.request.Request(
        f"{LITELLM_URL}/embeddings", data=payload,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {LITELLM_KEY}"},
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        vec = json.load(resp)["data"][0]["embedding"]

    conn = psycopg2.connect("postgresql://cocoindex:cocoindex@cocoindex-db:5432/cocoindex")
    cur = conn.cursor()
    cur.execute("""
        SELECT filename, location, text,
               1 - (embedding <=> %s::vector) AS score
        FROM botcodeflow__bot_code_chunks
        ORDER BY embedding <=> %s::vector
        LIMIT %s
    """, (str(vec), str(vec), limit))
    results = cur.fetchall()
    conn.close()
    return results


def main():
    import sys
    cocoindex.init()

    # Режим поиска: python3 cocoindex_code.py search "query"
    if len(sys.argv) >= 3 and sys.argv[1] == "search":
        query = " ".join(sys.argv[2:])
        print(f"Searching: {query}")
        for fn, loc, text, score in search(query):
            print(f"\n[{score:.3f}] {fn} @ {loc}")
            print(f"  {text[:300].strip()}")
        return

    print("=== Setup ===")
    code_flow.setup()
    print("Done.\n")

    print("=== Indexing (incremental) ===")
    code_flow.update()
    print("Done!\n")

    # Быстрый тест
    print("=== Test queries ===")
    for q in ["telegram webhook handler", "cocoindex install", "watchdog restart container"]:
        print(f"\n--- {q} ---")
        for fn, loc, text, score in search(q, limit=3):
            print(f"  [{score:.3f}] {fn} @ {loc}")
            print(f"  {text[:150].strip()}")


if __name__ == "__main__":
    main()
