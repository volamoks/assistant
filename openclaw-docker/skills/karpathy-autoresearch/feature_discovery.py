#!/usr/bin/env python3
"""
karpathy-autoresearch/feature_discovery.py — Feature Discovery Pipeline

Analyzes user request patterns to discover missing features and automation opportunities.
Part of the Karpathy Autoresearch v2 self-improvement cycle.

Discovery patterns:
- repeated_user_requests: "сделай X" в логах — частые запросы
- manual_workarounds: ручная работа → автоматизировать
- missing_integrations: "нет API для Y" — упоминания отсутствующих интеграций
"""

import argparse
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests
import yaml

# ── Config ────────────────────────────────────────────────────────────────────

CONFIG_PATH = Path("~/.openclaw/skills/karpathy-autoresearch/config.yaml").expanduser()
LITELLM_BASE = os.environ.get("LITELLM_BASE", "http://litellm-proxy:4000")
LITELLM_KEY = os.environ.get("LITELLM_MASTER_KEY", "")
DEFAULT_MODEL = "bailian/qwen3-max"

# ── Pattern Definitions ───────────────────────────────────────────────────────

REPEATED_REQUEST_PATTERNS = [
    r"сделай\s+(\w+)",
    r"создай\s+(\w+)",
    r"добавь\s+(\w+)",
    r"напиши\s+(\w+)",
    r"покажи\s+(\w+)",
    r"(?:can you|please|could you)\s+(\w+)",
    r"(?:make|create|add|write|show)\s+(\w+)",
]

MANUAL_WORKAROUND_PATTERNS = [
    r"вручную",
    r"ручная\s+работа",
    r"копирую",
    r"вставляю",
    r"открываю\s+и",
    r"захожу\s+в",
    r"manually",
    r"by hand",
    r"copy.*paste",
    r"open.*and",
]

MISSING_INTEGRATION_PATTERNS = [
    r"нет\s+api",
    r"нет\s+интеграции",
    r"не\s+поддерживает",
    r"нельзя\s+подключить",
    r"no\s+api",
    r"no\s+integration",
    r"doesn't\s+support",
    r"can't\s+connect",
]

# ── Core Functions ────────────────────────────────────────────────────────────

def load_config() -> Dict[str, Any]:
    """Load configuration from YAML file."""
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH) as f:
            return yaml.safe_load(f)
    return {}


def get_memory_files(days_back: int, memory_dir: Path) -> List[Path]:
    """Get list of memory files for the last N days."""
    files = []
    today = datetime.now()
    
    for i in range(days_back):
        date = today - timedelta(days=i)
        filename = date.strftime("%Y-%m-%d.md")
        filepath = memory_dir / filename
        if filepath.exists():
            files.append(filepath)
    
    return sorted(files, reverse=True)


def extract_repeated_requests(content: str) -> List[Dict[str, Any]]:
    """Extract repeated user requests from content."""
    requests = []
    
    for pattern in REPEATED_REQUEST_PATTERNS:
        matches = re.finditer(pattern, content, re.IGNORECASE)
        for match in matches:
            request_text = match.group(0)
            # Get context around match
            start = max(0, match.start() - 150)
            end = min(len(content), match.end() + 150)
            context = content[start:end].strip()
            
            requests.append({
                "type": "repeated_request",
                "pattern": pattern,
                "request": request_text,
                "context": context,
                "position": match.start(),
                "count": 1  # Will be aggregated later
            })
    
    return requests


def extract_manual_workarounds(content: str) -> List[Dict[str, Any]]:
    """Extract manual workaround mentions from content."""
    workarounds = []
    
    for pattern in MANUAL_WORKAROUND_PATTERNS:
        matches = re.finditer(pattern, content, re.IGNORECASE)
        for match in matches:
            start = max(0, match.start() - 200)
            end = min(len(content), match.end() + 200)
            context = content[start:end].strip()
            
            workarounds.append({
                "type": "manual_workaround",
                "pattern": pattern,
                "context": context,
                "position": match.start()
            })
    
    return workarounds


def extract_missing_integrations(content: str) -> List[Dict[str, Any]]:
    """Extract missing integration mentions from content."""
    integrations = []
    
    for pattern in MISSING_INTEGRATION_PATTERNS:
        matches = re.finditer(pattern, content, re.IGNORECASE)
        for match in matches:
            start = max(0, match.start() - 200)
            end = min(len(content), match.end() + 200)
            context = content[start:end].strip()
            
            # Try to extract what service is mentioned
            service_match = re.search(r'([A-Z][a-zA-Z]+|[a-z]+\.?[a-z]+)', context[:100])
            service = service_match.group(1) if service_match else "unknown"
            
            integrations.append({
                "type": "missing_integration",
                "pattern": pattern,
                "service": service,
                "context": context,
                "position": match.start()
            })
    
    return integrations


def aggregate_requests(requests: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Aggregate repeated requests by similarity."""
    aggregated = {}
    
    for req in requests:
        request_text = req["request"].lower().strip()
        # Create a simple key based on the action word
        key = re.sub(r'[^\w\s]', '', request_text)
        
        if key in aggregated:
            aggregated[key]["count"] += 1
            aggregated[key]["contexts"].append(req["context"])
        else:
            aggregated[key] = {
                "request": request_text,
                "count": 1,
                "contexts": [req["context"]],
                "type": "repeated_request"
            }
    
    # Sort by count
    return dict(sorted(aggregated.items(), key=lambda x: x[1]["count"], reverse=True))


def analyze_with_llm(
    patterns: Dict[str, Any],
    model: str = DEFAULT_MODEL
) -> List[Dict[str, Any]]:
    """Use LLM to analyze patterns and suggest new features."""
    
    fd_config = load_config().get("feature_discovery", {})
    max_features = fd_config.get("max_features_per_run", 2)
    
    system_prompt = """You are an expert product manager analyzing user behavior patterns.
Your task is to identify opportunities for new features or automations based on user request patterns.

Analyze the provided patterns and suggest specific, implementable features.

Output JSON with a "features" array. Each feature must have:
- id: unique identifier
- title: short feature name
- description: detailed explanation of what to build
- pattern_type: which pattern triggered this (repeated_user_requests, manual_workarounds, missing_integrations)
- evidence: specific examples from the patterns
- priority: "high", "medium", or "low"
- estimated_effort: "small", "medium", or "large"
- implementation_hint: brief suggestion on how to implement

Be specific and actionable. Focus on features that would have high user impact."""
    
    user_prompt = f"""Analyze these user behavior patterns and suggest up to {max_features} new features:

```json
{json.dumps(patterns, indent=2, ensure_ascii=False)[:5000]}
```

Output as JSON with "features" array."""
    
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
                "temperature": 0.4,
                "max_tokens": 3000
            },
            timeout=120
        )
        resp.raise_for_status()
        result = resp.json()["choices"][0]["message"]["content"]
        
        # Try to parse JSON from the response
        try:
            data = json.loads(result)
            return data.get("features", [])
        except json.JSONDecodeError:
            # Try to extract JSON from markdown code block
            json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', result, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group(1))
                return data.get("features", [])
            else:
                print(f"⚠️ Could not parse JSON from response")
                return []
    except Exception as e:
        print(f"❌ LLM error: {e}")
        return []


def discover_features(
    days_back: int = 7,
    memory_dir: Path = Path("/home/node/.openclaw/workspace-main/memory")
) -> Dict[str, Any]:
    """Run full feature discovery pipeline."""
    
    print(f"🔍 Feature Discovery: analyzing last {days_back} days...")
    
    # Get memory files
    memory_files = get_memory_files(days_back, memory_dir)
    print(f"📁 Found {len(memory_files)} memory files")
    
    if not memory_files:
        return {"error": "No memory files found", "features": []}
    
    # Extract patterns from each file
    all_requests = []
    all_workarounds = []
    all_integrations = []
    
    for filepath in memory_files:
        print(f"  📄 Parsing {filepath.name}...")
        content = filepath.read_text(encoding="utf-8")
        
        all_requests.extend(extract_repeated_requests(content))
        all_workarounds.extend(extract_manual_workarounds(content))
        all_integrations.extend(extract_missing_integrations(content))
    
    print(f"  • {len(all_requests)} repeated requests found")
    print(f"  • {len(all_workarounds)} manual workarounds found")
    print(f"  • {len(all_integrations)} missing integrations found")
    
    # Aggregate repeated requests
    aggregated_requests = aggregate_requests(all_requests)
    top_requests = dict(list(aggregated_requests.items())[:10])
    
    # Prepare patterns for LLM analysis
    patterns = {
        "repeated_user_requests": {
            "total": len(all_requests),
            "unique": len(aggregated_requests),
            "top_requests": top_requests
        },
        "manual_workarounds": {
            "total": len(all_workarounds),
            "examples": [w["context"][:200] for w in all_workarounds[:5]]
        },
        "missing_integrations": {
            "total": len(all_integrations),
            "services": list(set(i["service"] for i in all_integrations))[:10]
        }
    }
    
    # Run LLM analysis
    print("🤖 Running LLM analysis for feature suggestions...")
    features = analyze_with_llm(patterns)
    
    return {
        "discovered_at": datetime.now().isoformat(),
        "days_analyzed": days_back,
        "files_analyzed": len(memory_files),
        "patterns": patterns,
        "features": features,
        "total_features": len(features)
    }


def save_discovery_results(results: Dict[str, Any], output_path: Path) -> None:
    """Save discovery results to JSON file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)


def generate_feature_id(feature: Dict[str, Any]) -> str:
    """Generate unique ID for a feature."""
    content = f"{feature.get('title', '')}:{feature.get('pattern_type', '')}:{datetime.now().isoformat()}"
    return hashlib.md5(content.encode()).hexdigest()[:12]


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Discover new features from user patterns"
    )
    parser.add_argument("--days", type=int, default=7, help="Days of logs to analyze")
    parser.add_argument("--output", type=Path, default=Path("/tmp/karpathy_features.json"))
    parser.add_argument("--memory-dir", type=Path, 
                        default=Path("/home/node/.openclaw/workspace-main/memory"))
    parser.add_argument("--no-llm", action="store_true", help="Skip LLM analysis")
    args = parser.parse_args()
    
    print("🚀 Feature Discovery Pipeline")
    print("=" * 60)
    
    # Run discovery
    results = discover_features(args.days, args.memory_dir)
    
    if "error" in results:
        print(f"❌ {results['error']}")
        sys.exit(1)
    
    # Generate IDs for features
    for feature in results.get("features", []):
        feature["id"] = generate_feature_id(feature)
    
    # Save results
    save_discovery_results(results, args.output)
    print(f"\n💾 Results saved to {args.output}")
    
    # Print summary
    print("\n📊 Discovery Summary:")
    print(f"  Files analyzed: {results['files_analyzed']}")
    print(f"  Repeated requests: {results['patterns']['repeated_user_requests']['total']}")
    print(f"  Manual workarounds: {results['patterns']['manual_workarounds']['total']}")
    print(f"  Missing integrations: {results['patterns']['missing_integrations']['total']}")
    print(f"  Features suggested: {results['total_features']}")
    
    if results.get("features"):
        print("\n💡 Suggested Features:")
        for f in results["features"]:
            print(f"\n  [{f.get('priority', 'medium').upper()}] {f.get('title', 'Unknown')}")
            print(f"     Type: {f.get('pattern_type', 'unknown')}")
            print(f"     Effort: {f.get('estimated_effort', 'unknown')}")
            desc = f.get('description', '')
            if desc:
                print(f"     {desc[:100]}...")


if __name__ == "__main__":
    main()
