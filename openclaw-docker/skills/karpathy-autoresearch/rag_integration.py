#!/usr/bin/env python3
"""
karpathy-autoresearch/rag_integration.py — RAG Integration with ChromaDB

Integrates with ChromaDB for semantic search of past sessions and error patterns.
Uses obsidian_search for finding similar historical issues.

Part of the Karpathy Autoresearch self-improvement cycle (P1).
"""

import argparse
import json
import os
import sys
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests
import yaml

# ── Config ────────────────────────────────────────────────────────────────────

CONFIG_PATH = Path("~/.openclaw/skills/karpathy-autoresearch/config.yaml").expanduser()
CHROMA_HOST = os.environ.get("CHROMA_HOST", "http://chromadb:8000")
OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://host.docker.internal:11434")
EMBEDDING_MODEL = "nomic-embed-text"
COLLECTION_NAME = "karpathy_sessions"

# ── Data Classes ────────────────────────────────────────────────────────────

@dataclass
class SessionContext:
    """Context from a historical session."""
    session_id: str
    timestamp: str
    error_pattern: str
    solution: Optional[str]
    metrics: Dict[str, float]
    skill_name: str


@dataclass
class SimilarPattern:
    """A similar error pattern found in history."""
    session_id: str
    timestamp: str
    error_description: str
    solution_applied: Optional[str]
    outcome: str  # "success", "partial", "failed"
    similarity_score: float


# ── Core Functions ───────────────────────────────────────────────────────────

def load_config() -> Dict[str, Any]:
    """Load configuration from YAML file."""
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH) as f:
            return yaml.safe_load(f)
    return {}


def get_memory_dir(config: Dict[str, Any]) -> Path:
    """Get the memory directory path from config."""
    paths = config.get("paths", {})
    memory_dir = paths.get("memory_dir", "/data/obsidian/vault/Bot")
    return Path(memory_dir)


def get_sessions_history_dir(config: Dict[str, Any]) -> Path:
    """Get the sessions_history directory path."""
    paths = config.get("paths", {})
    base_dir = paths.get("memory_dir", "/data/obsidian/vault/Bot")
    sessions_dir = Path(base_dir) / "sessions_history"
    return sessions_dir if sessions_dir.exists() else Path(base_dir)


def get_chroma_collection() -> Optional[str]:
    """Get or create ChromaDB collection for sessions."""
    try:
        # Check if collection exists
        resp = requests.get(
            f"{CHROMA_HOST}/api/v1/collections/{COLLECTION_NAME}",
            timeout=5
        )
        if resp.status_code == 200:
            return resp.json()["id"]
        
        # Create collection
        resp = requests.post(
            f"{CHROMA_HOST}/api/v1/collections",
            json={"name": COLLECTION_NAME, "metadata": {"hnsw:space": "cosine"}},
            timeout=5
        )
        resp.raise_for_status()
        return resp.json()["id"]
    except Exception as e:
        print(f"⚠️ ChromaDB unavailable: {e}")
        return None


def get_embedding(text: str) -> List[float]:
    """Generate embedding via Ollama."""
    try:
        resp = requests.post(
            f"{OLLAMA_HOST}/api/embeddings",
            json={"model": EMBEDDING_MODEL, "prompt": text},
            timeout=10
        )
        resp.raise_for_status()
        return resp.json()["embedding"]
    except Exception as e:
        print(f"⚠️ Embedding error: {e}")
        # Return zero embedding as fallback
        return [0.0] * 768


def index_session_to_chroma(
    session_id: str,
    content: str,
    metadata: Dict[str, Any],
    collection_id: str
) -> bool:
    """Index a session to ChromaDB for semantic search."""
    try:
        embedding = get_embedding(content)
        
        requests.post(
            f"{CHROMA_HOST}/api/v1/collections/{collection_id}/add",
            json={
                "ids": [session_id],
                "embeddings": [embedding],
                "documents": [content],
                "metadatas": [metadata]
            },
            timeout=10
        )
        return True
    except Exception as e:
        print(f"⚠️ Failed to index session: {e}")
        return False


def search_similar_sessions(
    query: str,
    collection_id: str,
    limit: int = 5,
    filter_metadata: Optional[Dict[str, Any]] = None
) -> List[SimilarPattern]:
    """Search for similar sessions in ChromaDB."""
    try:
        embedding = get_embedding(query)
        
        query_params = {
            "query_embeddings": [embedding],
            "n_results": limit
        }
        
        if filter_metadata:
            query_params["where"] = filter_metadata
        
        resp = requests.post(
            f"{CHROMA_HOST}/api/v1/collections/{collection_id}/query",
            json=query_params,
            timeout=10
        )
        resp.raise_for_status()
        data = resp.json()
        
        results = []
        docs = data.get("documents", [[]])[0]
        metas = data.get("metadatas", [[]])[0]
        ids = data.get("ids", [[]])[0]
        distances = data.get("distances", [[]])[0]
        
        for doc, meta, sid, dist in zip(docs, metas, ids, distances):
            # Convert distance to similarity (1 - distance for cosine)
            similarity = 1.0 - dist if dist else 0.0
            
            results.append(SimilarPattern(
                session_id=sid,
                timestamp=meta.get("timestamp", ""),
                error_description=doc[:500],  # Truncate for display
                solution_applied=meta.get("solution"),
                outcome=meta.get("outcome", "unknown"),
                similarity_score=similarity
            ))
        
        return results
        
    except Exception as e:
        print(f"⚠️ Search error: {e}")
        return []


def parse_session_history_file(filepath: Path) -> List[SessionContext]:
    """Parse a session_history file to extract context."""
    sessions = []
    
    try:
        content = filepath.read_text(encoding="utf-8")
    except Exception as e:
        print(f"  ⚠️ Failed to read {filepath}: {e}")
        return sessions
    
    # Parse session blocks
    session_blocks = re.split(r"##\s+Session\s+", content)
    
    for block in session_blocks:
        if not block.strip() or len(block.strip()) < 50:
            continue
        
        # Extract session ID
        session_id_match = re.search(r"^(\S+)", block)
        session_id = session_id_match.group(1) if session_id_match else filepath.stem
        
        # Extract timestamp
        timestamp_match = re.search(r"(\d{4}-\d{2}-\d{2}[T\s]\d{2}:\d{2})", block)
        timestamp = timestamp_match.group(1) if timestamp_match else filepath.stem
        
        # Extract error patterns
        errors = []
        for pattern in [r"error[:\s]+(.+)", r"failed[:\s]+(.+)", r"exception[:\s]+(.+)"]:
            matches = re.findall(pattern, block, re.IGNORECASE)
            errors.extend(matches)
        
        # Extract solutions
        solutions = []
        for pattern in [r"solution[:\s]+(.+)", r"fixed[:\s]+(.+)", r"resolved[:\s]+(.+)"]:
            matches = re.findall(pattern, block, re.IGNORECASE)
            solutions.extend(matches)
        
        # Extract metrics if present
        metrics = {}
        for pattern in [r"success_rate[:\s]+([\d.]+)", r"latency[:\s]+([\d.]+)",
                       r"tokens[:\s]+(\d+)", r"errors[:\s]+(\d+)"]:
            match = re.search(pattern, block, re.IGNORECASE)
            if match:
                key = pattern.split("[:\\s]+")[0]
                metrics[key] = float(match.group(1))
        
        # Determine skill from file path or content
        skill_name = "general"
        if "python" in block.lower():
            skill_name = "python-coding"
        elif "search" in block.lower() or "web" in block.lower():
            skill_name = "search"
        
        if errors or solutions:
            sessions.append(SessionContext(
                session_id=session_id,
                timestamp=timestamp,
                error_pattern="; ".join(errors[:3]),  # Limit to 3
                solution="; ".join(solutions[:2]) if solutions else None,
                metrics=metrics,
                skill_name=skill_name
            ))
    
    return sessions


def load_sessions_history(days_back: int, sessions_dir: Path) -> List[SessionContext]:
    """Load sessions from sessions_history directory."""
    print(f"📂 Loading sessions from {sessions_dir}...")
    
    all_sessions = []
    today = datetime.now()
    
    for i in range(days_back):
        date = today - timedelta(days=i)
        
        # Try different filename patterns
        date_str = date.strftime("%Y-%m-%d")
        
        # Look for session files
        for pattern in [f"session_{date_str}.md", f"{date_str}.md", "*.md"]:
            files = list(sessions_dir.glob(pattern))
            for filepath in files:
                if filepath.name == "sessions.md" or "sessions" not in filepath.name.lower():
                    continue  # Skip main sessions file
                    
                sessions = parse_session_history_file(filepath)
                all_sessions.extend(sessions)
    
    print(f"   Loaded {len(all_sessions)} historical sessions")
    return all_sessions


def search_obsidian_for_patterns(
    query: str,
    db_path: Optional[Path] = None,
    limit: int = 5
) -> List[Dict[str, Any]]:
    """Search Obsidian FTS5 index for similar patterns."""
    import sqlite3
    
    if db_path is None:
        db_path = Path("/data/obsidian/vault/Bot/obsidian.db")
    
    if not db_path.exists():
        print(f"⚠️ Obsidian index not found: {db_path}")
        return []
    
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        
        # Use FTS5 for full-text search
        rows = conn.execute("""
            SELECT file_path, section_title, content, rank
            FROM chunks WHERE chunks MATCH ? ORDER BY rank LIMIT ?
        """, (query, limit)).fetchall()
        
        conn.close()
        
        results = []
        for row in rows:
            results.append({
                "file_path": row["file_path"],
                "section_title": row["section_title"],
                "content": row["content"][:500],  # Truncate
                "rank": row["rank"]
            })
        
        return results
        
    except Exception as e:
        print(f"⚠️ Obsidian search error: {e}")
        return []


def build_rag_context(
    current_error: str,
    category: str,
    config: Dict[str, Any],
    collection_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Build context for hypothesis generation from historical data.
    
    This is the main entry point for RAG integration.
    """
    context = {
        "query": current_error,
        "category": category,
        "similar_sessions": [],
        "obsidian_results": [],
        "historical_patterns": []
    }
    
    days_back = config.get("analysis", {}).get("days_back", 7)
    
    # 1. Search ChromaDB for similar sessions
    if collection_id:
        similar = search_similar_sessions(
            current_error,
            collection_id,
            limit=5,
            filter_metadata={"category": category} if category else None
        )
        context["similar_sessions"] = [
            {
                "session_id": s.session_id,
                "timestamp": s.timestamp,
                "description": s.error_description,
                "solution": s.solution_applied,
                "outcome": s.outcome,
                "similarity": s.similarity_score
            }
            for s in similar
        ]
    
    # 2. Search Obsidian for relevant content
    obsidian_results = search_obsidian_for_patterns(current_error, limit=5)
    context["obsidian_results"] = obsidian_results
    
    # 3. Load sessions_history for direct context
    sessions_dir = get_sessions_history_dir(config)
    if sessions_dir.exists():
        sessions = load_sessions_history(days_back, sessions_dir)
        
        # Filter by category
        if category:
            sessions = [s for s in sessions if s.skill_name == category]
        
        # Take most recent
        sessions = sessions[:10]
        
        context["historical_patterns"] = [
            {
                "session_id": s.session_id,
                "timestamp": s.timestamp,
                "error": s.error_pattern,
                "solution": s.solution,
                "metrics": s.metrics
            }
            for s in sessions
        ]
    
    return context


def format_context_for_prompt(context: Dict[str, Any]) -> str:
    """Format RAG context for injection into LLM prompt."""
    lines = ["\n### Historical Context from Past Sessions:"]
    
    # Similar sessions from ChromaDB
    if context.get("similar_sessions"):
        lines.append("\n#### Similar Past Errors (semantic search):")
        for s in context["similar_sessions"][:3]:
            lines.append(f"- **{s['timestamp']}** [{s['outcome']}] Similarity: {s['similarity']:.1%}")
            if s.get("solution"):
                lines.append(f"  Solution: {s['solution'][:200]}")
            lines.append(f"  Error: {s['description'][:200]}")
    
    # Historical patterns from sessions_history
    if context.get("historical_patterns"):
        lines.append("\n#### Recent Error Patterns:")
        for p in context["historical_patterns"][:3]:
            lines.append(f"- **{p['session_id']}** @ {p['timestamp']}")
            lines.append(f"  Error: {p['error'][:150]}")
            if p.get("solution"):
                lines.append(f"  Fixed: {p['solution'][:150]}")
            if p.get("metrics"):
                metrics_str = ", ".join(f"{k}={v}" for k, v in p["metrics"].items())
                lines.append(f"  Metrics: {metrics_str}")
    
    # Obsidian results
    if context.get("obsidian_results"):
        lines.append("\n#### Relevant Documentation:")
        for r in context["obsidian_results"][:2]:
            lines.append(f"- {r['file_path']} [§ {r['section_title']}]")
            lines.append(f"  {r['content'][:200]}")
    
    return "\n".join(lines)


def index_sessions_to_chroma(
    sessions: List[SessionContext],
    collection_id: str,
    force: bool = False
) -> int:
    """Index sessions to ChromaDB for future semantic search."""
    indexed = 0
    
    for session in sessions:
        # Build content for embedding
        content = f"Error: {session.error_pattern}"
        if session.solution:
            content += f" | Solution: {session.solution}"
        
        metadata = {
            "session_id": session.session_id,
            "timestamp": session.timestamp,
            "category": session.skill_name,
            "solution": session.solution or "",
            "outcome": "success" if session.solution else "unresolved"
        }
        
        if index_session_to_chroma(session.session_id, content, metadata, collection_id):
            indexed += 1
    
    return indexed


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="RAG Integration for Karpathy Autoresearch",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Build context for hypothesis generation
  python3 rag_integration.py --query "timeout error in tool execution" --category coding
  
  # Index sessions to ChromaDB
  python3 rag_integration.py --index-sessions --days 14
  
  # Search for similar patterns
  python3 rag_integration.py --search "file read error" --limit 5
        """
    )
    parser.add_argument("--query", type=str, help="Query to search for")
    parser.add_argument("--category", type=str, default=None, help="Filter by category")
    parser.add_argument("--limit", type=int, default=5, help="Number of results")
    parser.add_argument("--index-sessions", action="store_true", help="Index sessions to ChromaDB")
    parser.add_argument("--days", type=int, default=7, help="Days of history to load")
    parser.add_argument("--output", type=Path, default=Path("/tmp/karpathy_rag_context.json"))
    args = parser.parse_args()
    
    print("🔍 RAG Integration for Karpathy Autoresearch")
    print("=" * 60)
    
    # Load config
    config = load_config()
    
    # Get ChromaDB collection
    collection_id = get_chroma_collection()
    
    if args.index_sessions:
        # Index sessions to ChromaDB
        print("\n📚 Indexing sessions to ChromaDB...")
        
        if not collection_id:
            print("❌ ChromaDB unavailable. Exiting.")
            sys.exit(1)
        
        sessions_dir = get_sessions_history_dir(config)
        sessions = load_sessions_history(args.days, sessions_dir)
        
        if sessions:
            indexed = index_sessions_to_chroma(sessions, collection_id)
            print(f"✅ Indexed {indexed} sessions to ChromaDB")
        else:
            print("⚠️ No sessions found to index")
    
    elif args.query:
        # Search for similar patterns
        print(f"\n🔎 Searching for: {args.query}")
        
        context = build_rag_context(args.query, args.category or "general", config, collection_id)
        
        # Save context
        with open(args.output, "w") as f:
            json.dump(context, f, indent=2, ensure_ascii=False)
        print(f"💾 Context saved to {args.output}")
        
        # Print formatted context
        print("\n" + format_context_for_prompt(context))
    
    else:
        print("❌ Please specify --query or --index-sessions")
        parser.print_help()
        sys.exit(1)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
