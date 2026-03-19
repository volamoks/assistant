from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import uuid
import os
import json
import httpx
import numpy as np
from pathlib import Path

app = FastAPI(title="Viking RAG", description="Simple RAG memory store")

# Config — use LiteLLM (OpenAI-compatible) instead of Ollama for reliability
LITELLM_BASE_URL = os.environ.get("LITELLM_BASE_URL", "http://litellm:4000")
LITELLM_API_KEY = os.environ.get("LITELLM_API_KEY", "sk-litellm-openclaw-proxy")
EMBEDDING_MODEL = os.environ.get("EMBEDDING_MODEL", "nomic-embed-text")
PERSIST_PATH = Path(os.environ.get("VIKING_DATA_DIR", "/data/viking")) / "memories.json"

# In-memory store, loaded from disk on startup
memories = []  # List of {id, text, embedding}

def load_from_disk():
    global memories
    if PERSIST_PATH.exists():
        try:
            with open(PERSIST_PATH) as f:
                memories = json.load(f)
        except Exception:
            memories = []

def save_to_disk():
    PERSIST_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(PERSIST_PATH, "w") as f:
        json.dump(memories, f)

@app.on_event("startup")
def startup():
    load_from_disk()

def cosine_similarity(a, b):
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-8)

class MemoryStoreRequest(BaseModel):
    text: str

class MemorySearchRequest(BaseModel):
    query: str
    limit: int = Field(default=5, ge=1, le=100)

class MemoryDeleteRequest(BaseModel):
    id: str

@app.get("/health")
def health_check():
    return {"status": "ok", "memories": len(memories)}

@app.post("/memory/store")
async def store_memory(req: MemoryStoreRequest):
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            r = await client.post(
                f"{LITELLM_BASE_URL}/v1/embeddings",
                json={"model": EMBEDDING_MODEL, "input": req.text},
                headers={"Authorization": f"Bearer {LITELLM_API_KEY}"}
            )
            data = r.json()
            embedding = data["data"][0]["embedding"]

        memory_id = str(uuid.uuid4())
        memories.append({
            "id": memory_id,
            "text": req.text,
            "embedding": embedding
        })
        save_to_disk()

        return {"id": memory_id, "status": "stored", "total": len(memories)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/memory/search")
async def search_memory(req: MemorySearchRequest):
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            r = await client.post(
                f"{LITELLM_BASE_URL}/v1/embeddings",
                json={"model": EMBEDDING_MODEL, "input": req.query},
                headers={"Authorization": f"Bearer {LITELLM_API_KEY}"}
            )
            data = r.json()
            query_embedding = data["data"][0]["embedding"]

        results = []
        for mem in memories:
            sim = cosine_similarity(query_embedding, mem["embedding"])
            results.append({
                "id": mem["id"],
                "text": mem["text"],
                "score": float(sim)
            })

        results.sort(key=lambda x: x["score"], reverse=True)
        return {"results": results[:req.limit], "total": len(memories)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/memory/delete")
async def delete_memory(req: MemoryDeleteRequest):
    global memories
    memories = [m for m in memories if m["id"] != req.id]
    save_to_disk()
    return {"status": "deleted", "total": len(memories)}

@app.get("/memory/count")
def count_memories():
    return {"total": len(memories)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8100)
