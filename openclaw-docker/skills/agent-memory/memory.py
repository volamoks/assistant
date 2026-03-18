#!/usr/bin/env python3
"""
Agent Memory Layer (mem0-style) using existing ChromaDB infrastructure.

Store and retrieve long-term memory for skills:
- crypto: portfolio preferences, strategies, alerts
- finance: budget patterns, goals
- debate: past conclusions
- general: user preferences

Usage:
    from memory import Memory
    
    m = Memory(collection="crypto")
    m.store("Abror prefers P2P below 15%", {"category": "preference"})
    results = m.search("P2P premium", limit=3)
"""

import os
import sys
import json
from datetime import datetime
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
from pathlib import Path

import requests

# ── Config ────────────────────────────────────────────────────────────────────

CHROMA_HOST = os.environ.get("CHROMA_HOST", "http://chromadb:8000")
LITELLM_HOST = os.environ.get("LITELLM_HOST", "http://litellm:4000")
LITELLM_API_KEY = os.environ.get("LITELLM_API_KEY", "sk-litellm-openclaw-proxy")
EMBEDDING_MODEL = "nomic-embed-text"
COLLECTION_NAME = "agent_memories"

USER_MD_PATH = Path("/data/obsidian/vault/Bot/USER.md")


@dataclass
class MemoryEntry:
    """Single memory entry."""
    text: str
    metadata: Dict[str, Any]
    id: Optional[str] = None
    distance: Optional[float] = None


class Memory:
    """Long-term memory interface for agents."""
    
    def __init__(self, collection: str = "general"):
        """
        Initialize memory for a specific collection.
        
        Args:
            collection: Domain collection (crypto, finance, debate, general)
        """
        self.collection = collection
        self._collection_id: Optional[str] = None
        self._ensure_collection()
    
    def _ensure_collection(self) -> None:
        """Ensure the collection exists in ChromaDB."""
        try:
            # Check if collection exists
            resp = requests.get(
                f"{CHROMA_HOST}/api/v1/collections/{COLLECTION_NAME}",
                timeout=5
            )
            if resp.status_code == 200:
                self._collection_id = resp.json()["id"]
                return
        except Exception:
            pass
        
        # Create collection if not exists
        try:
            resp = requests.post(
                f"{CHROMA_HOST}/api/v1/collections",
                json={"name": COLLECTION_NAME, "metadata": {"hnsw:space": "cosine"}},
                timeout=5
            )
            resp.raise_for_status()
            self._collection_id = resp.json()["id"]
        except Exception as e:
            print(f"[Memory] Warning: Could not create collection: {e}")
    
    def _get_embedding(self, text: str) -> List[float]:
        """Generate embedding via LiteLLM."""
        try:
            resp = requests.post(
                f"{LITELLM_HOST}/v1/embeddings",
                json={"model": EMBEDDING_MODEL, "input": text},
                headers={"Authorization": f"Bearer {LITELLM_API_KEY}"},
                timeout=10
            )
            resp.raise_for_status()
            return resp.json()["data"][0]["embedding"]
        except Exception as e:
            print(f"[Memory] Embedding error: {e}")
            # Return zero embedding as fallback
            return [0.0] * 768
    
    def store(
        self,
        text: str,
        metadata: Optional[Dict[str, Any]] = None,
        update_user_md: bool = False
    ) -> str:
        """
        Store a memory.
        
        Args:
            text: The memory content
            metadata: Optional metadata (category, source, etc.)
            update_user_md: If True, also append to USER.md
            
        Returns:
            Memory ID
        """
        if metadata is None:
            metadata = {}
        
        # Add collection and timestamp
        metadata["collection"] = self.collection
        metadata["timestamp"] = datetime.now().isoformat()
        
        # Generate ID from text hash + timestamp
        mem_id = f"{self.collection}_{hash(text) % 10000000}_{int(datetime.now().timestamp())}"
        
        # Get embedding
        embedding = self._get_embedding(text)
        
        # Store in ChromaDB
        try:
            requests.post(
                f"{CHROMA_HOST}/api/v1/collections/{self._collection_id}/add",
                json={
                    "ids": [mem_id],
                    "embeddings": [embedding],
                    "documents": [text],
                    "metadatas": [metadata]
                },
                timeout=10
            )
        except Exception as e:
            print(f"[Memory] Store error: {e}")
            return ""
        
        # Optionally update USER.md
        if update_user_md or metadata.get("update_user_md"):
            self._update_user_md(text, metadata)
        
        return mem_id
    
    def search(self, query: str, limit: int = 3) -> List[MemoryEntry]:
        """
        Search memories by query.
        
        Args:
            query: Search query
            limit: Number of results
            
        Returns:
            List of memory entries
        """
        if not self._collection_id:
            return []
        
        # Get query embedding
        embedding = self._get_embedding(query)
        
        try:
            resp = requests.post(
                f"{CHROMA_HOST}/api/v1/collections/{self._collection_id}/query",
                json={
                    "query_embeddings": [embedding],
                    "n_results": limit,
                    "where": {"collection": self.collection}
                },
                timeout=10
            )
            resp.raise_for_status()
            data = resp.json()
            
            results = []
            docs = data.get("documents", [[]])[0]
            metas = data.get("metadatas", [[]])[0]
            ids = data.get("ids", [[]])[0]
            distances = data.get("distances", [[]])[0]
            
            for doc, meta, mid, dist in zip(docs, metas, ids, distances):
                results.append(MemoryEntry(
                    text=doc,
                    metadata=meta,
                    id=mid,
                    distance=dist
                ))
            
            return results
            
        except Exception as e:
            print(f"[Memory] Search error: {e}")
            return []
    
    def get_by_category(self, category: str, limit: int = 10) -> List[MemoryEntry]:
        """
        Get memories by category.
        
        Args:
            category: Metadata category value
            limit: Number of results
        """
        if not self._collection_id:
            return []
        
        try:
            resp = requests.post(
                f"{CHROMA_HOST}/api/v1/collections/{self._collection_id}/get",
                json={
                    "where": {
                        "$and": [
                            {"collection": self.collection},
                            {"category": category}
                        ]
                    },
                    "limit": limit
                },
                timeout=10
            )
            resp.raise_for_status()
            data = resp.json()
            
            results = []
            docs = data.get("documents", [])
            metas = data.get("metadatas", [])
            ids = data.get("ids", [])
            
            for doc, meta, mid in zip(docs, metas, ids):
                results.append(MemoryEntry(
                    text=doc,
                    metadata=meta,
                    id=mid
                ))
            
            return results
            
        except Exception as e:
            print(f"[Memory] Get error: {e}")
            return []
    
    def _update_user_md(self, text: str, metadata: Dict[str, Any]) -> None:
        """Append memory to USER.md if significant."""
        try:
            category = metadata.get("category", "general")
            timestamp = datetime.now().strftime("%Y-%m-%d")
            
            entry = f"\n- [{timestamp}] [{category}] {text}\n"
            
            # Append to USER.md
            with open(USER_MD_PATH, "a", encoding="utf-8") as f:
                f.write(entry)
            
            print(f"[Memory] Updated USER.md: {text[:50]}...")
            
        except Exception as e:
            print(f"[Memory] Could not update USER.md: {e}")
    
    def format_for_prompt(self, memories: List[MemoryEntry]) -> str:
        """Format memories for injection into LLM prompt."""
        if not memories:
            return ""
        
        lines = ["\n### Relevant memories from previous sessions:"]
        for mem in memories:
            cat = mem.metadata.get("category", "note")
            lines.append(f"- [{cat}] {mem.text}")
        
        return "\n".join(lines)


# ── CLI Interface ─────────────────────────────────────────────────────────────

def main():
    """CLI for testing memory."""
    import argparse
    
    p = argparse.ArgumentParser(description="Agent Memory CLI")
    p.add_argument("action", choices=["store", "search", "list"], help="Action")
    p.add_argument("--collection", "-c", default="general", help="Collection name")
    p.add_argument("--text", "-t", help="Text to store")
    p.add_argument("--query", "-q", help="Search query")
    p.add_argument("--category", help="Filter by category")
    p.add_argument("--limit", "-n", type=int, default=3, help="Result limit")
    
    args = p.parse_args()
    
    m = Memory(collection=args.collection)
    
    if args.action == "store":
        if not args.text:
            print("Error: --text required for store")
            sys.exit(1)
        mid = m.store(args.text, {"category": args.category or "note"})
        print(f"Stored: {mid}")
        
    elif args.action == "search":
        query = args.query or args.text or ""
        results = m.search(query, limit=args.limit)
        for r in results:
            print(f"[{r.distance:.3f}] {r.text[:100]}...")
            
    elif args.action == "list":
        if args.category:
            results = m.get_by_category(args.category, limit=args.limit)
        else:
            results = m.search("*", limit=args.limit)
        for r in results:
            print(f"- {r.text[:100]}...")


if __name__ == "__main__":
    main()