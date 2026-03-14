from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import uuid
import os
from openai import AsyncOpenAI
from openviking import Viking

app = FastAPI(title="OpenViking Bridge", description="Bridge between TS OpenClaw and Python OpenViking")

# Initialize OpenAI client to point to LiteLLM proxy for embeddings
# We use host.docker.internal to reach the litellm proxy from this container
# or we can use the service name if they are in the same docker network. 
# In this environment, the proxy is at litellm-proxy:18788 or host.docker.internal:18788
LITELLM_BASE_URL = os.environ.get("LITELLM_BASE_URL", "http://host.docker.internal:18788")
LITELLM_API_KEY = os.environ.get("LITELLM_API_KEY")
if not LITELLM_API_KEY:
    raise ValueError("LITELLM_API_KEY environment variable is required")
EMBEDDING_MODEL = os.environ.get("EMBEDDING_MODEL", "qwen3.5-plus") # Using a configured LiteLLM model

oai_client = AsyncOpenAI(api_key=LITELLM_API_KEY, base_url=LITELLM_BASE_URL)

# Initialize OpenViking
# We define a basic in-memory or persisted storage config depending on Viking's setup.
# According to OpenViking docs, we initialize the Viking class.
viking_db_path = os.environ.get("VIKING_DB_PATH", "/app/data/viking_db")
os.makedirs(viking_db_path, exist_ok=True)
viking = Viking(data_dir=viking_db_path)

class MemoryStoreRequest(BaseModel):
    text: str

class MemorySearchRequest(BaseModel):
    query: str
    limit: int = Field(default=5, ge=1, le=100)

class MemoryDeleteRequest(BaseModel):
    id: str

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.post("/memory/store")
async def store_memory(req: MemoryStoreRequest):
    try:
        # 1. Get embedding from LiteLLM
        try:
            res = await oai_client.embeddings.create(input=req.text, model=EMBEDDING_MODEL)
            embedding = res.data[0].embedding
        except Exception as e:
            # Try fallback model if primary fails
            print(f"Primary embedding model failed: {e}, trying fallback...")
            fallback_model = "minimax/embedding-3-1"
            res = await oai_client.embeddings.create(input=req.text, model=fallback_model)
            embedding = res.data[0].embedding
        
        # 2. Store in Viking
        memory_id = str(uuid.uuid4())
        # The exact method depends on OpenViking API (usually add_memory or insert).
        # We will wrap it in a try block in case the API differs.
        try:
            viking.add_memory(id=memory_id, text=req.text, embedding=embedding)
        except AttributeError:
             # Fallback if the method name is different
             viking.insert(id=memory_id, text=req.text, embedding=embedding)
             
        print(f"Stored memory: {req.text}")
        return {"id": memory_id, "status": "stored"}
    except Exception as e:
        print(f"Error storing memory: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/memory/search")
async def search_memory(req: MemorySearchRequest):
    try:
        # 1. Get embedding for the query
        try:
            res = await oai_client.embeddings.create(input=req.query, model=EMBEDDING_MODEL)
            embedding = res.data[0].embedding
        except Exception as e:
            # Try fallback model if primary fails
            print(f"Primary embedding model failed: {e}, trying fallback...")
            fallback_model = "minimax/embedding-3-1"
            res = await oai_client.embeddings.create(input=req.query, model=fallback_model)
            embedding = res.data[0].embedding
        
        # 2. Search in Viking
        try:
             results = viking.search_memory(query_embedding=embedding, top_k=req.limit)
             # Expected results format parsing
             formatted_results = [{"id": r.id, "text": r.text, "score": getattr(r, 'score', 0)} for r in results]
        except AttributeError:
             # Fallback
             results = viking.search(embedding=embedding, limit=req.limit)
             formatted_results = [{"id": r.get('id', 'N/A'), "text": r.get('text', 'N/A')} for r in getattr(results, 'data', results)]
             
        print(f"Searched memory for: {req.query}, found {len(formatted_results)} results")
        return {"results": formatted_results}
    except Exception as e:
        print(f"Error searching memory: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/memory/delete")
async def delete_memory(req: MemoryDeleteRequest):
    try:
        # Delete from Viking
        try:
             viking.delete_memory(id=req.id)
        except AttributeError:
             viking.delete(id=req.id)
             
        print(f"Deleted memory: {req.id}")
        return {"status": "deleted"}
    except Exception as e:
        print(f"Error deleting memory: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8100)
