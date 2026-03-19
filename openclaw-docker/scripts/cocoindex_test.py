"""
CocoIndex — индексация Obsidian vault через nomic-embed-text (LiteLLM)
Запуск: docker exec openclaw-latest python3 /data/bot/openclaw-docker/scripts/cocoindex_test.py
"""

import cocoindex

LITELLM_URL = "http://litellm:4000"
LITELLM_KEY = "sk-litellm-openclaw-proxy"
SOURCE_PATH = "/data/obsidian/vault/Bot"
EMBED_DIM = 768


@cocoindex.flow_def(name="ObsidianBotFlow")
def obsidian_flow(flow_builder: cocoindex.FlowBuilder, data_scope: cocoindex.DataScope):
    cocoindex.add_auth_entry("litellm_key", LITELLM_KEY)

    data_scope["files"] = flow_builder.add_source(
        cocoindex.sources.LocalFile(
            path=SOURCE_PATH,
            included_patterns=["**/*.md"],
        )
    )

    collector = data_scope.add_collector()

    with data_scope["files"].row() as doc:
        doc["chunks"] = doc["content"].transform(
            cocoindex.functions.SplitRecursively(),
            language="markdown",
            chunk_size=400,
            chunk_overlap=50,
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
        "obsidian_bot_chunks",
        cocoindex.storages.Postgres(),
        primary_key_fields=["filename", "location"],
        vector_indexes=[
            cocoindex.VectorIndexDef(
                field_name="embedding",
                metric=cocoindex.VectorSimilarityMetric.COSINE_SIMILARITY,
            )
        ],
    )


def get_embedding(text: str) -> list:
    import urllib.request, json
    payload = json.dumps({"model": "nomic-embed-text", "input": text}).encode()
    req = urllib.request.Request(
        f"{LITELLM_URL}/embeddings",
        data=payload,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {LITELLM_KEY}"},
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.load(resp)["data"][0]["embedding"]


def test_query(query: str):
    import psycopg2
    print(f"\n=== Query: '{query}' ===")
    query_vec = get_embedding(query)
    conn = psycopg2.connect("postgresql://cocoindex:cocoindex@cocoindex-db:5432/cocoindex")
    cur = conn.cursor()
    cur.execute("""
        SELECT filename, location, text,
               1 - (embedding <=> %s::vector) AS score
        FROM obsidianbotflow__obsidian_bot_chunks
        ORDER BY embedding <=> %s::vector
        LIMIT 5
    """, (str(query_vec), str(query_vec)))
    rows = cur.fetchall()
    conn.close()
    for filename, location, text, score in rows:
        print(f"\n  [{score:.3f}] {filename} @ {location}")
        print(f"  {text[:200].strip()}")


def main():
    cocoindex.init()

    print("=== Setup flow ===")
    obsidian_flow.setup()
    print("Done.")

    print("\n=== Indexing (may take a few minutes) ===")
    obsidian_flow.update()
    print("Indexing complete!")

    test_query("crash watchdog openclaw")
    test_query("user preferences abror")

    print("\n=== Done ===")


if __name__ == "__main__":
    main()
