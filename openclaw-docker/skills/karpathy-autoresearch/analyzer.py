#!/usr/bin/env python3
"""
karpathy-autoresearch/analyzer.py — Session Log Analyzer

Analyzes session logs and memory files to extract success/failure patterns.
Part of the Karpathy Autoresearch self-improvement cycle.
"""

import argparse
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
DEFAULT_MODEL = "minimax/MiniMax-M2.5"

# ── Pattern Definitions ────────────────────────────────────────────────────────

ERROR_PATTERNS = [
    r"error", r"failed", r"timeout", r"exception", r"traceback",
    r"crash", r"broken", r"❌", r"не удалось", r"ошибка"
]

SUCCESS_PATTERNS = [
    r"✅", r"success", r"completed", r"done", r"finished",
    r"готово", r"выполнено", r"успешно"
]

TOOL_PATTERNS = [
    r"tool_calls", r"sessions_spawn", r"subagents", r"exec",
    r"read\s+", r"write\s+", r"web_search", r"browser"
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


def parse_memory_file(filepath: Path) -> Dict[str, Any]:
    """Parse a single memory file and extract patterns."""
    content = filepath.read_text(encoding="utf-8")
    
    patterns = {
        "errors": [],
        "successes": [],
        "tools_used": [],
        "sessions": [],
        "metadata": {
            "file": str(filepath),
            "date": filepath.stem,
            "size": len(content),
            "lines": len(content.splitlines())
        }
    }
    
    # Extract errors
    for pattern in ERROR_PATTERNS:
        matches = re.finditer(pattern, content, re.IGNORECASE)
        for match in matches:
            # Get context around match
            start = max(0, match.start() - 100)
            end = min(len(content), match.end() + 100)
            context = content[start:end].strip()
            patterns["errors"].append({
                "pattern": pattern,
                "context": context,
                "position": match.start()
            })
    
    # Extract successes
    for pattern in SUCCESS_PATTERNS:
        matches = re.finditer(pattern, content, re.IGNORECASE)
        for match in matches:
            start = max(0, match.start() - 100)
            end = min(len(content), match.end() + 100)
            context = content[start:end].strip()
            patterns["successes"].append({
                "pattern": pattern,
                "context": context,
                "position": match.start()
            })
    
    # Extract tool usage
    for pattern in TOOL_PATTERNS:
        count = len(re.findall(pattern, content, re.IGNORECASE))
        if count > 0:
            patterns["tools_used"].append({
                "tool": pattern.strip(),
                "count": count
            })
    
    # Extract session markers
    session_markers = re.findall(r"##\s+🕐\s+(\d{2}:\d{2})\s+UTC", content)
    patterns["sessions"] = session_markers
    
    return patterns


def analyze_with_llm(patterns: Dict[str, Any], model: str = DEFAULT_MODEL, config: Dict[str, Any] = None) -> Dict[str, Any]:
    """Use LLM to analyze patterns and identify insights."""
    
    # Check if night mode is active for extended analysis
    from datetime import datetime
    night_config = config.get("night_mode", {}) if config else {}
    is_night = night_config.get("enabled", False) and night_config.get("start_hour", 2) <= datetime.now().hour < night_config.get("end_hour", 6)
    
    # Prepare summary for LLM (extended for night mode)
    summary = {
        "total_errors": len(patterns.get("errors", [])),
        "total_successes": len(patterns.get("successes", [])),
        "tools_used": patterns.get("tools_used", []),
        "sessions_count": len(patterns.get("sessions", [])),
        "sample_errors": patterns.get("errors", [])[:10 if is_night else 5],
        "sample_successes": patterns.get("successes", [])[:10 if is_night else 5],
        "mode": "night" if is_night else "day"
    }
    
    system_prompt = """You are an expert at analyzing AI agent performance logs.
Your task is to identify patterns in success/failure data and suggest specific improvements.

Analyze the provided data and output JSON with:
1. key_patterns: List of recurring patterns (both good and bad)
2. problem_areas: Specific areas needing improvement
3. strengths: What's working well
4. recommendations: Actionable suggestions for improvement

Be specific and data-driven."""
    
    user_prompt = f"""Analyze these agent performance patterns:

```json
{json.dumps(summary, indent=2, ensure_ascii=False)}
```

Provide your analysis as JSON."""
    
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
                "temperature": 0.3,
                "response_format": {"type": "json_object"}
            },
            timeout=60
        )
        resp.raise_for_status()
        analysis = resp.json()["choices"][0]["message"]["content"]
        return json.loads(analysis)
    except Exception as e:
        return {
            "error": str(e),
            "key_patterns": [],
            "problem_areas": [],
            "strengths": [],
            "recommendations": []
        }


def aggregate_patterns(all_patterns: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Aggregate patterns from multiple files."""
    aggregated = {
        "total_files": len(all_patterns),
        "total_errors": 0,
        "total_successes": 0,
        "error_types": {},
        "success_types": {},
        "tool_usage": {},
        "timeline": []
    }
    
    for p in all_patterns:
        aggregated["total_errors"] += len(p.get("errors", []))
        aggregated["total_successes"] += len(p.get("successes", []))
        
        # Count error types
        for e in p.get("errors", []):
            pattern = e.get("pattern", "unknown")
            aggregated["error_types"][pattern] = aggregated["error_types"].get(pattern, 0) + 1
        
        # Count success types
        for s in p.get("successes", []):
            pattern = s.get("pattern", "unknown")
            aggregated["success_types"][pattern] = aggregated["success_types"].get(pattern, 0) + 1
        
        # Aggregate tool usage
        for t in p.get("tools_used", []):
            tool = t.get("tool", "unknown")
            count = t.get("count", 0)
            aggregated["tool_usage"][tool] = aggregated["tool_usage"].get(tool, 0) + count
        
        # Timeline entry
        aggregated["timeline"].append({
            "date": p.get("metadata", {}).get("date"),
            "errors": len(p.get("errors", [])),
            "successes": len(p.get("successes", []))
        })
    
    return aggregated


def save_patterns(patterns: Dict[str, Any], output_path: Path) -> None:
    """Save patterns to JSON file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(patterns, f, indent=2, ensure_ascii=False)


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Analyze session logs for patterns")
    parser.add_argument("--days", type=int, default=7, help="Days of logs to analyze")
    parser.add_argument("--output", type=Path, default=Path("/tmp/karpathy_patterns.json"))
    parser.add_argument("--memory-dir", type=Path, default=None, help="Memory directory (defaults to config)")
    parser.add_argument("--no-llm", action="store_true", help="Skip LLM analysis")
    args = parser.parse_args()
    
    print(f"🔍 Analyzing last {args.days} days of session logs...")
    
    # Load config
    config = load_config()
    
    # Get memory dir from config or use default
    if args.memory_dir is None:
        config_paths = config.get("paths", {})
        memory_dir = Path(config_paths.get("memory_dir", "/data/obsidian/Claw/Memory"))
    else:
        memory_dir = args.memory_dir
    
    # Get memory files
    memory_files = get_memory_files(args.days, memory_dir)
    print(f"📁 Found {len(memory_files)} memory files")
    
    if not memory_files:
        print("❌ No memory files found")
        sys.exit(1)
    
    # Parse each file
    all_patterns = []
    for filepath in memory_files:
        print(f"  📄 Parsing {filepath.name}...")
        patterns = parse_memory_file(filepath)
        all_patterns.append(patterns)
    
    # Aggregate patterns
    print("📊 Aggregating patterns...")
    aggregated = aggregate_patterns(all_patterns)
    
    # LLM analysis
    if not args.no_llm:
        print("🤖 Running LLM analysis...")
        llm_analysis = analyze_with_llm(aggregated)
        aggregated["llm_analysis"] = llm_analysis
    
    # Save results
    save_patterns(aggregated, args.output)
    print(f"💾 Patterns saved to {args.output}")
    
    # Print summary
    print("\n📈 Summary:")
    print(f"  Total errors: {aggregated['total_errors']}")
    print(f"  Total successes: {aggregated['total_successes']}")
    print(f"  Error types: {len(aggregated['error_types'])}")
    print(f"  Tool types used: {len(aggregated['tool_usage'])}")
    
    if aggregated['error_types']:
        print("\n🔴 Top Error Patterns:")
        for pattern, count in sorted(aggregated['error_types'].items(), key=lambda x: -x[1])[:5]:
            print(f"  - {pattern}: {count}")
    
    if aggregated['tool_usage']:
        print("\n🔧 Tool Usage:")
        for tool, count in sorted(aggregated['tool_usage'].items(), key=lambda x: -x[1])[:5]:
            print(f"  - {tool}: {count}")


if __name__ == "__main__":
    main()
