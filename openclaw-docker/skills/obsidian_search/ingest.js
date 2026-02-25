// ingest.js
// Script to parse, chunk, and embed Obsidian markdown notes into ChromaDB
import fs from 'node:fs';
import path from 'node:path';

const OLLAMA_HOST = process.env.OLLAMA_HOST || "http://ollama:11434";
const CHROMA_HOST = process.env.CHROMA_HOST || "http://chromadb:8000";
const VAULT_PATH = process.env.OBSIDIAN_VAULT_PATH || "/data/obsidian";
const COLLECTION_NAME = "obsidian_vault";
const EMBEDDING_MODEL = "nomic-embed-text";

// 1. Ensure Nomic is pulled
async function ensureModel() {
    console.log(`Checking if ${EMBEDDING_MODEL} is available in Ollama...`);
    const res = await fetch(`${OLLAMA_HOST}/api/tags`);
    const json = await res.json();
    const hasModel = json.models?.some(m => m.name.includes(EMBEDDING_MODEL));

    if (!hasModel) {
        console.log(`Pulling ${EMBEDDING_MODEL}... (This might take a minute)`);
        await fetch(`${OLLAMA_HOST}/api/pull`, {
            method: 'POST',
            body: JSON.stringify({ name: EMBEDDING_MODEL })
        });
        console.log(`Finished pulling ${EMBEDDING_MODEL}.`);
    } else {
        console.log(`${EMBEDDING_MODEL} is ready.`);
    }
}

// 2. Setup Chroma Collection
async function setupChroma() {
    console.log(`Setting up ChromaDB collection: ${COLLECTION_NAME}...`);
    // First try to GET the collection
    const getRes = await fetch(`${CHROMA_HOST}/api/v1/collections/${COLLECTION_NAME}`);
    if (getRes.ok) {
        return await getRes.json();
    }

    // Create collection if it doesn't exist
    await fetch(`${CHROMA_HOST}/api/v1/collections`, {
        method: 'POST',
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: COLLECTION_NAME })
    });

    // Fetch it again to get the ID safely
    const fetchRes = await fetch(`${CHROMA_HOST}/api/v1/collections/${COLLECTION_NAME}`);
    return await fetchRes.json();
}

// Helper to chunk text
function chunkText(text, maxChars = 1000) {
    const chunks = [];
    let currentChunk = "";
    const paragraphs = text.split('\n\n');

    for (const p of paragraphs) {
        if (currentChunk.length + p.length > maxChars) {
            chunks.push(currentChunk.trim());
            currentChunk = p + '\n\n';
        } else {
            currentChunk += p + '\n\n';
        }
    }
    if (currentChunk.trim()) chunks.push(currentChunk.trim());
    return chunks;
}

// 3. Recursive directory reading
function getMarkdownFiles(dir, filesList = []) {
    const files = fs.readdirSync(dir);
    for (const file of files) {
        // Skip hidden folders
        if (file.startsWith('.')) continue;

        const filePath = path.join(dir, file);
        if (fs.statSync(filePath).isDirectory()) {
            getMarkdownFiles(filePath, filesList);
        } else if (file.endsWith('.md')) {
            filesList.push(filePath);
        }
    }
    return filesList;
}

// 4. Ingest Loop
async function run() {
    try {
        await ensureModel();
        const collection = await setupChroma();

        const files = getMarkdownFiles(VAULT_PATH);
        console.log(`Found ${files.length} markdown files in ${VAULT_PATH}`);

        const collectionId = collection.id;

        for (const file of files) {
            console.log(`Processing: ${file}`);
            const content = fs.readFileSync(file, 'utf8');
            const chunks = chunkText(content);
            const relativePath = path.relative(VAULT_PATH, file);

            for (let i = 0; i < chunks.length; i++) {
                const chunk = chunks[i];
                const id = `${relativePath}-chunk-${i}`;

                // Get Embedding
                const embRes = await fetch(`${OLLAMA_HOST}/api/embeddings`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ model: EMBEDDING_MODEL, prompt: chunk })
                });
                const embData = await embRes.json();

                // Upsert to Chroma
                await fetch(`${CHROMA_HOST}/api/v1/collections/${collectionId}/upsert`, {
                    method: 'POST',
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        ids: [id],
                        embeddings: [embData.embedding],
                        documents: [chunk],
                        metadatas: [{ source: relativePath }]
                    })
                });
            }
        }
        console.log("✅ Ingestion complete!");
    } catch (e) {
        console.error("❌ Ingestion failed:", e);
    }
}

run();
