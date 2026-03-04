#!/usr/bin/env python3
"""
debate.py — Multi-Agent Debate with real LLM calls via LiteLLM proxy.

Round 1: Proposer + Critic state positions independently (parallel)
Round 2: Each responds to the other's key points summary (parallel)
Final:   Moderator scores arguments and synthesizes recommendation

Usage:
  python3 debate.py "Topic to debate"
  python3 debate.py "Invest $10k in 2026?" --rounds 2
  python3 debate.py "Microservices vs Monolith?" --model kimi-k2.5
"""

import argparse
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

import requests

# Memory integration
sys.path.insert(0, '/home/node/.openclaw/skills')
try:
    from agent_memory.memory import Memory
    MEMORY_AVAILABLE = True
except ImportError:
    MEMORY_AVAILABLE = False
    print("[Debate] Memory not available, skipping persistence")

# ── Config ────────────────────────────────────────────────────────────────────

LITELLM_BASE = os.environ.get("LITELLM_BASE", "http://litellm-proxy:4000")
LITELLM_KEY  = os.environ.get("LITELLM_MASTER_KEY", "")
DEFAULT_MODEL = "qwen3.5-plus"  # Coding Plan (Bailian) compatible
OUTPUT_DIR = Path("/home/node/.openclaw/workspace-main/skills/debate-agents")

# ── LLM call ──────────────────────────────────────────────────────────────────

def call_llm(model: str, system: str, user: str, temperature: float = 0.7) -> str:
    headers = {"Content-Type": "application/json"}
    if LITELLM_KEY:
        headers["Authorization"] = f"Bearer {LITELLM_KEY}"
    resp = requests.post(
        f"{LITELLM_BASE}/chat/completions",
        headers=headers,
        json={
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user",   "content": user},
            ],
            "temperature": temperature,
            "stream": False,
        },
        timeout=120,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]

# ── Summarizer ────────────────────────────────────────────────────────────────

SUMMARY_MODEL = "qwen3.5-plus"  # Cheap/fast model for summarization

def summarize(text: str) -> str:
    """Compress a debate response to ~150 tokens (3-5 bullet key points).
    
    Uses a cheaper/faster model (qwen3.5-plus) to reduce costs while
    preserving key arguments for context passing between rounds.
    """
    return call_llm(
        SUMMARY_MODEL,
        "Summarize the key arguments into 3-5 bullet points. Be concise (~150 tokens). "
        "Preserve the main reasoning and evidence. No intro text, just bullets.",
        text,
        temperature=0.2,
    )

# ── RAG context ───────────────────────────────────────────────────────────────

def get_rag_context(topic: str) -> str:
    """Pull 2 relevant chunks from Obsidian ChromaDB vault."""
    try:
        ollama = os.environ.get("OLLAMA_HOST", "http://host.docker.internal:11434")
        chroma = os.environ.get("CHROMA_HOST", "http://chromadb:8000")

        emb = requests.post(
            f"{ollama}/api/embeddings",
            json={"model": "nomic-embed-text", "prompt": topic},
            timeout=8,
        ).json()["embedding"]

        coll_id = requests.get(
            f"{chroma}/api/v1/collections/obsidian_vault", timeout=5
        ).json()["id"]

        docs = requests.post(
            f"{chroma}/api/v1/collections/{coll_id}/query",
            json={"query_embeddings": [emb], "n_results": 2},
            timeout=8,
        ).json()["documents"][0]

        if docs:
            return "\n\nRelevant context from your notes:\n" + "\n---\n".join(
                d[:400] for d in docs
            )
    except Exception:
        pass
    return ""

# ── Debate ────────────────────────────────────────────────────────────────────

def run_debate(task: str, model: str = DEFAULT_MODEL, rounds: int = 2) -> str:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    print(f"\n🎬 Debate: {task}")
    print(f"   Model: {model} | Rounds: {rounds} | {ts}\n")

    print("🔍 Searching relevant notes...")
    rag = get_rag_context(task)
    print(f"   {'✅ Found context' if rag else '⚪ No relevant notes'}\n")

    sections = [
        f"# Debate: {task}\n",
        f"**Date:** {ts} | **Model:** {model} | **Rounds:** {rounds}\n\n---\n",
    ]
    transcript = []  # Full text for moderator
    proposer_sum = ""
    critic_sum = ""

    for r in range(1, rounds + 1):
        print(f"📍 Round {r}/{rounds}")

        # Build prompts per round
        if r == 1:
            p_sys = (
                f"You are PROPOSER in a structured debate. "
                f"Be specific, data-driven, and constructively optimistic. "
                f"300-400 words.{rag}"
            )
            p_usr = (
                f"Topic: {task}\n\n"
                f"Propose your solution with concrete recommendations and reasoning."
            )
            c_sys = (
                f"You are CRITIC in a structured debate. "
                f"Identify risks, gaps, and flawed assumptions rigorously. "
                f"300-400 words.{rag}"
            )
            c_usr = (
                f"Topic: {task}\n\n"
                f"Analyze the risks, challenges, and critical considerations."
            )
        else:
            p_sys = f"You are PROPOSER in round {r}. Respond to the critic's points. 250-350 words."
            p_usr = (
                f"Topic: {task}\n\n"
                f"Critic's key points from last round:\n{critic_sum}\n\n"
                f"Address each point — defend your position or adjust where valid."
            )
            c_sys = f"You are CRITIC in round {r}. Evaluate the proposer's response. 250-350 words."
            c_usr = (
                f"Topic: {task}\n\n"
                f"Proposer's key points from last round:\n{proposer_sum}\n\n"
                f"Evaluate, push back on weak points, acknowledge valid ones."
            )

        # Both agents run in parallel every round
        print("   ⚡ Proposer + Critic running in parallel...")
        with ThreadPoolExecutor(max_workers=2) as ex:
            f_p = ex.submit(call_llm, model, p_sys, p_usr)
            f_c = ex.submit(call_llm, model, c_sys, c_usr)
            p_resp = f_p.result()
            c_resp = f_c.result()

        print(f"   ✅ Round {r} done ({len(p_resp) + len(c_resp)} chars)")

        sections.append(f"## Round {r}: Proposer\n\n{p_resp}\n")
        sections.append(f"## Round {r}: Critic\n\n{c_resp}\n")
        transcript.append(f"[Round {r} — Proposer]\n{p_resp}")
        transcript.append(f"[Round {r} — Critic]\n{c_resp}")

        # Summarize for next round (context compression)
        if r < rounds:
            print(f"   📝 Summarizing round {r} for next round...")
            with ThreadPoolExecutor(max_workers=2) as ex:
                f_ps = ex.submit(summarize, p_resp)
                f_cs = ex.submit(summarize, c_resp)
                proposer_sum = f_ps.result()
                critic_sum = f_cs.result()

    # Moderator synthesis
    print(f"\n⚖️  Moderator synthesizing...")
    mod_sys = (
        "You are MODERATOR evaluating a structured debate. "
        "Score each key argument (1-10 for strength/validity). "
        "Produce: 1) Argument evaluation table, 2) Final recommendation, 3) Confidence level with key uncertainties."
    )
    mod_usr = f"Topic: {task}\n\nFull debate:\n\n" + "\n\n---\n\n".join(transcript)
    moderator = call_llm(model, mod_sys, mod_usr, temperature=0.4)
    print("   ✅ Done")

    sections.append(f"---\n\n## Moderator Synthesis\n\n{moderator}\n")

    # Save
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M")
    out_file = OUTPUT_DIR / f"debate-{stamp}.md"
    latest   = OUTPUT_DIR / "debate-output.md"

    content = "\n".join(sections)
    out_file.write_text(content, encoding="utf-8")
    latest.write_text(content, encoding="utf-8")

    print(f"\n✅ Saved: {out_file}")
    print(f"\n{'='*60}\nMODERATOR SYNTHESIS\n{'='*60}")
    print(moderator[:2000])

    # Store in memory for future reference
    if MEMORY_AVAILABLE:
        try:
            mem = Memory(collection="debate")
            # Extract key conclusion (first paragraph)
            conclusion = moderator.split('\n\n')[0][:500]
            mem.store(
                text=f"Debate on '{task}': {conclusion}",
                metadata={
                    "category": "conclusion",
                    "topic": task[:100],
                    "model": model,
                    "rounds": rounds,
                    "file": str(out_file)
                }
            )
            print(f"\n💾 Stored in memory (collection: debate)")
        except Exception as e:
            print(f"\n⚠️  Could not store in memory: {e}")

    return content


def main():
    p = argparse.ArgumentParser(description="Multi-Agent Debate (real LLM calls)")
    p.add_argument("task",   help="Topic or question to debate")
    p.add_argument("--model",  default=DEFAULT_MODEL, help=f"LiteLLM model (default: {DEFAULT_MODEL})")
    p.add_argument("--rounds", type=int, default=2,   help="Debate rounds (default: 2)")
    args = p.parse_args()
    run_debate(args.task, args.model, args.rounds)


if __name__ == "__main__":
    main()
