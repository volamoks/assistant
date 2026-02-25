// obsidian_search RAG skill

const OLLAMA_HOST = process.env.OLLAMA_HOST || "http://ollama:11434";
const CHROMA_HOST = process.env.CHROMA_HOST || "http://chromadb:8000";
const COLLECTION_NAME = "obsidian_vault";
const EMBEDDING_MODEL = "nomic-embed-text";

async function getEmbedding(text) {
    const response = await fetch(`${OLLAMA_HOST}/api/embeddings`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            model: EMBEDDING_MODEL,
            prompt: text
        })
    });

    if (!response.ok) {
        throw new Error(`Failed to get embedding from Ollama: ${response.statusText}`);
    }
    const data = await response.json();
    return data.embedding;
}

export async function run(args) {
    try {
        const query = args.query;
        const limit = args.limit || 3;

        // 1. Get embedding for the user's query
        const queryEmbedding = await getEmbedding(query);

        // 2. Query ChromaDB
        const resColl = await fetch(`${CHROMA_HOST}/api/v1/collections/${COLLECTION_NAME}`);
        if (!resColl.ok) {
            console.error("Coll Err:", resColl.status, await resColl.text());
            return `The Obsidian RAG database is currently empty or hasn't been initialized. Please run the ingestion script first.`;
        }
        const collection = await resColl.json();
        console.log("Collection ID:", collection.id);

        const chromaResponse = await fetch(`${CHROMA_HOST}/api/v1/collections/${collection.id}/query`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                query_embeddings: [queryEmbedding],
                n_results: limit
            })
        });

        if (!chromaResponse.ok) {
            // Check if collection doesn't exist yet
            if (chromaResponse.status === 404) {
                return `The Obsidian RAG database is currently empty or hasn't been initialized. Please run the ingestion script first.`;
            }
            throw new Error(`ChromaDB error: ${chromaResponse.statusText}`);
        }

        const data = await chromaResponse.json();

        if (!data.documents || data.documents.length === 0 || !data.documents[0] || data.documents[0].length === 0) {
            return `No relevant information found in the Obsidian vault for: "${query}".`;
        }

        // Format the results
        let resultString = `Search results for "${query}":\n\n`;
        const documents = data.documents[0];
        const metadatas = data.metadatas[0];
        const distances = data.distances[0];

        for (let i = 0; i < documents.length; i++) {
            const doc = documents[i];
            const meta = metadatas[i] || {};
            const source = meta.source || "Unknown File";
            // Lower distance is better in Chroma
            const relevanceScore = (1 - (distances[i] || 0)).toFixed(2);

            resultString += `### Source: ${source}\n`;
            // resultString += `Relevance: ${relevanceScore}\n`;
            resultString += `${doc}\n\n---\n\n`;
        }

        return resultString;

    } catch (error) {
        return `Error executing obsidian_search: ${error.message}`;
    }
}
