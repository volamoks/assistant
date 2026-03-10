#!/usr/bin/env python3
"""
karpathy-autoresearch/hypothesis.py — Hypothesis Generator

Generates testable improvement hypotheses based on analyzed patterns.
Part of the Karpathy Autoresearch self-improvement cycle.
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests
import yaml

# ── Config ────────────────────────────────────────────────────────────────────

CONFIG_PATH = Path("~/.openclaw/skills/karpathy-autoresearch/config.yaml").expanduser()
LITELLM_BASE = os.environ.get("LITELLM_BASE", "http://litellm-proxy:4000")
LITELLM_KEY = os.environ.get("LITELLM_MASTER_KEY", "")
DEFAULT_MODEL = "minimax/MiniMax-M2.5"

# ── Core Functions ────────────────────────────────────────────────────────────

def load_config() -> Dict[str, Any]:
    """Load configuration from YAML file."""
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH) as f:
            return yaml.safe_load(f)
    return {}


def load_patterns(patterns_file: Path) -> Dict[str, Any]:
    """Load analyzed patterns from JSON file."""
    with open(patterns_file) as f:
        return json.load(f)


def generate_hypotheses(patterns: Dict[str, Any], config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Generate improvement hypotheses using LLM."""
    
    hypothesis_config = config.get("hypothesis", {})
    max_hypotheses = hypothesis_config.get("max_hypotheses", 5)
    categories = hypothesis_config.get("categories", ["prompt_improvement", "tool_optimization"])
    model = hypothesis_config.get("llm_model", DEFAULT_MODEL)
    
    system_prompt = """You are an expert AI agent improvement researcher.
Your task is to generate specific, testable hypotheses for improving an AI agent's performance.

Based on the analyzed patterns, generate hypotheses that:
1. Are specific and measurable (e.g., "Adding timeout X reduces errors by Y%")
2. Can be tested via A/B comparison
3. Address real problems found in the data
4. Are safe to implement (won't break existing functionality)

Output JSON with a "hypotheses" array. Each hypothesis must have:
- id: unique identifier
- title: short description
- description: detailed explanation
- category: one of [prompt_improvement, tool_optimization, workflow_enhancement, error_handling, performance_tuning]
- target_file: which file/skill to modify
- current_behavior: what happens now
- proposed_change: what to change
- expected_outcome: predicted improvement
- confidence: 0-1 score based on pattern strength
- test_approach: how to validate (A/B test description)

Be creative but grounded in the data."""
    
    user_prompt = f"""Generate up to {max_hypotheses} improvement hypotheses based on these patterns:

```json
{json.dumps(patterns, indent=2, ensure_ascii=False)[:4000]}
```

Categories to consider: {', '.join(categories)}

Output as JSON with "hypotheses" array."""
    
    headers = {"Content-Type": "application/json"}
    if LITELLM_KEY:
        headers["Authorization"] = f"Bearer {LITELLM_KEY}"
    
    try:
        resp = requests.post(
            f"{LITELLM_BASE}/chat/completions",
            headers=headers,
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "temperature": 0.5,
                "max_tokens": 3000
            },
            timeout=60
        )
        resp.raise_for_status()
        result = resp.json()["choices"][0]["message"]["content"]
        # Try to parse JSON from the response
        try:
            data = json.loads(result)
            return data.get("hypotheses", [])
        except json.JSONDecodeError:
            # If not valid JSON, try to extract JSON from markdown code block
            import re
            json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', result, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group(1))
                return data.get("hypotheses", [])
            else:
                print(f"⚠️ Could not parse JSON from response")
                return []
    except Exception as e:
        print(f"❌ LLM error: {e}")
        return []


def score_hypothesis(hypothesis: Dict[str, Any], patterns: Dict[str, Any]) -> float:
    """Score a hypothesis based on data support and feasibility."""
    score = 0.0
    
    # Base confidence from LLM
    score += hypothesis.get("confidence", 0.5) * 30
    
    # Check if problem is significant in patterns
    problem_areas = patterns.get("llm_analysis", {}).get("problem_areas", [])
    hypothesis_desc = hypothesis.get("description", "").lower()
    
    for problem in problem_areas:
        if problem.lower() in hypothesis_desc:
            score += 20
            break
    
    # Feasibility bonus
    category = hypothesis.get("category", "")
    if category in ["prompt_improvement", "error_handling"]:
        score += 15  # Easier to implement
    elif category == "tool_optimization":
        score += 10
    
    # Testability bonus
    if "test_approach" in hypothesis and hypothesis["test_approach"]:
        score += 15
    
    # Safety check
    target = hypothesis.get("target_file", "")
    if any(x in target for x in ["SKILL.md", "prompts/", "config"]):
        score += 10  # Safer targets
    
    return min(score, 100)


def rank_hypotheses(hypotheses: List[Dict[str, Any]], patterns: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Rank hypotheses by score and filter low-confidence ones."""
    config = load_config()
    min_confidence = config.get("hypothesis", {}).get("min_confidence", 0.6)
    
    # Score each hypothesis
    for h in hypotheses:
        h["score"] = score_hypothesis(h, patterns)
        h["rank"] = 0  # Will be set after sorting
    
    # Sort by score
    sorted_hypotheses = sorted(hypotheses, key=lambda x: x["score"], reverse=True)
    
    # Filter by confidence and assign ranks
    filtered = []
    for i, h in enumerate(sorted_hypotheses):
        if h.get("confidence", 0) >= min_confidence:
            h["rank"] = i + 1
            filtered.append(h)
    
    return filtered


def save_hypotheses(hypotheses: List[Dict[str, Any]], output_path: Path) -> None:
    """Save hypotheses to JSON file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump({"hypotheses": hypotheses}, f, indent=2, ensure_ascii=False)


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Generate improvement hypotheses")
    parser.add_argument("--patterns-file", type=Path, default=Path("/tmp/karpathy_patterns.json"))
    parser.add_argument("--output", type=Path, default=Path("/tmp/karpathy_hypotheses.json"))
    args = parser.parse_args()
    
    print("🧠 Generating improvement hypotheses...")
    
    # Load config
    config = load_config()
    
    # Load patterns
    if not args.patterns_file.exists():
        print(f"❌ Patterns file not found: {args.patterns_file}")
        sys.exit(1)
    
    patterns = load_patterns(args.patterns_file)
    print(f"📊 Loaded patterns: {patterns.get('total_errors', 0)} errors, {patterns.get('total_successes', 0)} successes")
    
    # Generate hypotheses
    print("🤖 Asking LLM to generate hypotheses...")
    hypotheses = generate_hypotheses(patterns, config)
    
    if not hypotheses:
        print("⚠️ No hypotheses generated")
        sys.exit(1)
    
    print(f"💡 Generated {len(hypotheses)} raw hypotheses")
    
    # Rank and filter
    print("📈 Ranking hypotheses...")
    ranked = rank_hypotheses(hypotheses, patterns)
    
    # Save results
    save_hypotheses(ranked, args.output)
    print(f"💾 Saved {len(ranked)} ranked hypotheses to {args.output}")
    
    # Print summary
    print("\n🎯 Top Hypotheses:")
    for h in ranked[:5]:
        print(f"\n  #{h.get('rank')} [{h.get('category', 'unknown')}]")
        print(f"     Title: {h.get('title', 'N/A')}")
        print(f"     Score: {h.get('score', 0):.1f}/100")
        print(f"     Confidence: {h.get('confidence', 0):.0%}")
        print(f"     Target: {h.get('target_file', 'N/A')}")
        print(f"     Expected: {h.get('expected_outcome', 'N/A')[:80]}...")


if __name__ == "__main__":
    main()
