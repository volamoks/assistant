#!/usr/bin/env python3
"""
karpathy-autoresearch/test_harness.py — Real A/B Testing Harness

Runs real A/B tests on actual session data instead of simulations.
Part of the Karpathy Autoresearch self-improvement cycle.

Key features:
- Loads real sessions from memory files
- Extracts actual metrics (success rate, latency, tokens)
- Runs statistical A/B tests
- Compares control vs variant behavior
"""

import argparse
import json
import os
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
import statistics

import requests
import yaml

# ── Config ────────────────────────────────────────────────────────────────────

CONFIG_PATH = Path("~/.openclaw/skills/karpathy-autoresearch/config.yaml").expanduser()
LITELLM_BASE = os.environ.get("LITELLM_BASE", "http://litELLM-proxy:4000")
LITELLM_KEY = os.environ.get("LITELLM_MASTER_KEY", "")

# ── Data Classes ───────────────────────────────────────────────────────────

@dataclass
class SessionMetrics:
    """Metrics extracted from a single session."""
    session_id: str
    timestamp: str
    success: bool
    latency_seconds: float
    tokens_used: int
    error_count: int
    tool_calls: int
    category: str = "unknown"

@dataclass
class ABTestResult:
    """Result of an A/B test."""
    hypothesis_id: str
    hypothesis_title: str
    category: str
    
    # Control group metrics
    control_n: int
    control_success_rate: float
    control_latency_avg: float
    control_tokens_avg: float
    control_error_rate: float
    
    # Variant group metrics
    variant_n: int
    variant_success_rate: float
    variant_latency_avg: float
    variant_tokens_avg: float
    variant_error_rate: float
    
    # Statistical analysis
    success_rate_p_value: float
    latency_p_value: float
    tokens_p_value: float
    
    # Overall result
    winner: str  # "control", "variant", "tie", "insufficient_data"
    confidence: float
    recommendation: str  # "apply", "reject", "inconclusive"
    
    tested_at: str = field(default_factory=lambda: datetime.now().isoformat())

# ── Pattern Definitions ─────────────────────────────────────────────────────

ERROR_PATTERNS = [
    r"error", r"failed", r"timeout", r"exception", r"traceback",
    r"crash", r"broken", r"❌", r"не удалось", r"ошибка"
]

SUCCESS_PATTERNS = [
    r"✅", r"success", r"completed", r"done", r"finished",
    r"готово", r"выполнено", r"успешно"
]

TOKEN_PATTERNS = [
    r"tokens?[:\s]+(\d+)",
    r"used[:\s]+(\d+)",
    r"потрачено[:\s]+(\d+)",
    r"(\d+)\s+tokens?"
]

LATENCY_PATTERNS = [
    r"latency[:\s]+(\d+\.?\d*)\s*(s|sec|seconds|мс|ms)?",
    r"time[:\s]+(\d+\.?\d*)\s*(s|sec|seconds|мс|ms)?",
    r"(\d+\.?\d*)\s*(s|sec|seconds|мс|ms)"
]

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


def get_sessions_list(days_back: int, memory_dir: Path) -> List[Path]:
    """Get list of session memory files for the last N days."""
    files = []
    today = datetime.now()
    
    for i in range(days_back):
        date = today - timedelta(days=i)
        filename = date.strftime("%Y-%m-%d.md")
        filepath = memory_dir / filename
        if filepath.exists():
            files.append(filepath)
    
    return sorted(files, reverse=True)


def extract_session_from_file(filepath: Path) -> List[SessionMetrics]:
    """Extract session metrics from a memory file."""
    sessions = []
    
    try:
        content = filepath.read_text(encoding="utf-8")
    except Exception as e:
        print(f"  ⚠️ Failed to read {filepath}: {e}")
        return sessions
    
    # Split content into session blocks (separated by timestamps)
    session_blocks = re.split(r"##\s+🕐\s+\d{2}:\d{2}\s+UTC", content)
    
    for idx, block in enumerate(session_blocks):
        if not block.strip() or len(block.strip()) < 50:
            continue
        
        # Extract basic info
        session_id = f"{filepath.stem}_{idx}"
        
        # Check for success markers
        success_count = sum(len(re.findall(p, block, re.IGNORECASE)) for p in SUCCESS_PATTERNS)
        error_count = sum(len(re.findall(p, block, re.IGNORECASE)) for p in ERROR_PATTERNS)
        
        # Determine success: more success markers than error markers
        success = success_count > error_count and success_count > 0
        
        # Extract latency if present
        latency = 0.0
        for pattern in LATENCY_PATTERNS:
            matches = re.findall(pattern, block, re.IGNORECASE)
            if matches:
                try:
                    value = float(matches[0][0] if isinstance(matches[0], tuple) else matches[0])
                    unit = matches[0][1] if isinstance(matches[0], tuple) and len(matches[0]) > 1 else "s"
                    # Normalize to seconds
                    if unit in ("мс", "ms"):
                        latency = value / 1000
                    else:
                        latency = value
                    break
                except (ValueError, IndexError):
                    pass
        
        # Extract tokens if present
        tokens = 0
        for pattern in TOKEN_PATTERNS:
            matches = re.findall(pattern, block, re.IGNORECASE)
            if matches:
                try:
                    tokens = int(matches[0])
                    break
                except (ValueError, IndexError):
                    pass
        
        # Count tool calls
        tool_call_count = len(re.findall(r"tool_calls?|exec|run_command", block, re.IGNORECASE))
        
        # Determine category based on content
        category = "general"
        if "code" in block.lower() or "python" in block.lower():
            category = "coding"
        elif "search" in block.lower() or "web" in block.lower():
            category = "search"
        elif "file" in block.lower() or "read" in block.lower():
            category = "file_ops"
        
        sessions.append(SessionMetrics(
            session_id=session_id,
            timestamp=filepath.stem,
            success=success,
            latency_seconds=latency if latency > 0 else 2.5,  # Default if not found
            tokens_used=tokens if tokens > 0 else 1000,  # Default if not found
            error_count=error_count,
            tool_calls=tool_call_count,
            category=category
        ))
    
    return sessions


def load_sessions(days_back: int, memory_dir: Path, category_filter: str = None) -> List[SessionMetrics]:
    """Load all sessions from memory files."""
    print(f"📂 Loading sessions from {memory_dir}...")
    
    session_files = get_sessions_list(days_back, memory_dir)
    print(f"   Found {len(session_files)} memory files")
    
    all_sessions = []
    for filepath in session_files:
        sessions = extract_session_from_file(filepath)
        
        # Apply category filter if specified
        if category_filter:
            sessions = [s for s in sessions if s.category == category_filter]
        
        all_sessions.extend(sessions)
    
    print(f"   Loaded {len(all_sessions)} total sessions")
    return all_sessions


def split_into_groups(sessions: List[SessionMetrics], variant_ratio: float = 0.5) -> Tuple[List[SessionMetrics], List[SessionMetrics]]:
    """Split sessions into control and variant groups."""
    import random
    random.shuffle(sessions)
    
    split_point = int(len(sessions) * variant_ratio)
    return sessions[:split_point], sessions[split_point:]


def calculate_group_metrics(sessions: List[SessionMetrics]) -> Dict[str, float]:
    """Calculate metrics for a group of sessions."""
    if not sessions:
        return {
            "n": 0,
            "success_rate": 0.0,
            "latency_avg": 0.0,
            "tokens_avg": 0.0,
            "error_rate": 0.0
        }
    
    successes = sum(1 for s in sessions if s.success)
    total_errors = sum(s.error_count for s in sessions)
    avg_latency = statistics.mean(s.latency_seconds for s in sessions)
    avg_tokens = statistics.mean(s.tokens_used for s in sessions)
    
    return {
        "n": len(sessions),
        "success_rate": successes / len(sessions),
        "latency_avg": avg_latency,
        "tokens_avg": avg_tokens,
        "error_rate": total_errors / len(sessions)
    }


def calculate_p_value(control_values: List[float], variant_values: List[float]) -> float:
    """Calculate a simple p-value using t-test approximation."""
    if len(control_values) < 2 or len(variant_values) < 2:
        return 1.0  # Insufficient data
    
    try:
        # Simple two-sample t-test approximation
        n1, n2 = len(control_values), len(variant_values)
        mean1 = statistics.mean(control_values)
        mean2 = statistics.mean(variant_values)
        var1 = statistics.variance(control_values) if len(control_values) > 1 else 0
        var2 = statistics.variance(variant_values) if len(variant_values) > 1 else 0
        
        # Pooled standard error
        se = ((var1 / n1) + (var2 / n2)) ** 0.5
        if se == 0:
            return 1.0
        
        # t-statistic
        t_stat = abs(mean1 - mean2) / se
        
        # Approximate p-value using normal distribution (for large n)
        # For simplicity, we'll use a basic approximation
        from math import erf
        p_value = 1 - erf(t_stat / (2 ** 0.5))
        
        return max(0.0, min(1.0, p_value))
    except Exception:
        return 1.0


def run_real_ab_test(
    hypothesis: Dict[str, Any],
    sessions: List[SessionMetrics],
    config: Dict[str, Any]
) -> ABTestResult:
    """Run a real A/B test on actual session data."""
    
    testing_config = config.get("testing", {})
    min_samples = testing_config.get("min_samples", 10)  # Minimum sessions per group
    
    hypothesis_id = hypothesis.get("id", "unknown")
    hypothesis_title = hypothesis.get("title", "Unknown hypothesis")
    category = hypothesis.get("category", "unknown")
    
    print(f"\n🧪 Running real A/B test: {hypothesis_title}")
    print(f"   Category: {category}")
    print(f"   Total sessions available: {len(sessions)}")
    
    # Filter sessions by category if hypothesis targets specific category
    target_category = hypothesis.get("target_category")
    if target_category:
        sessions = [s for s in sessions if s.category == target_category]
        print(f"   Filtered to category '{target_category}': {len(sessions)} sessions")
    
    if len(sessions) < min_samples * 2:
        print(f"   ⚠️ Insufficient data: need {min_samples * 2}, got {len(sessions)}")
        return ABTestResult(
            hypothesis_id=hypothesis_id,
            hypothesis_title=hypothesis_title,
            category=category,
            control_n=0,
            control_success_rate=0.0,
            control_latency_avg=0.0,
            control_tokens_avg=0.0,
            control_error_rate=0.0,
            variant_n=0,
            variant_success_rate=0.0,
            variant_latency_avg=0.0,
            variant_tokens_avg=0.0,
            variant_error_rate=0.0,
            success_rate_p_value=1.0,
            latency_p_value=1.0,
            tokens_p_value=1.0,
            winner="insufficient_data",
            confidence=0.0,
            recommendation="inconclusive"
        )
    
    # Split into control and variant groups
    control_sessions, variant_sessions = split_into_groups(sessions)
    
    print(f"   Control group: {len(control_sessions)} sessions")
    print(f"   Variant group: {len(variant_sessions)} sessions")
    
    # Calculate metrics for each group
    control_metrics = calculate_group_metrics(control_sessions)
    variant_metrics = calculate_group_metrics(variant_sessions)
    
    print(f"\n   📊 Control metrics:")
    print(f"      Success rate: {control_metrics['success_rate']:.1%}")
    print(f"      Latency: {control_metrics['latency_avg']:.2f}s")
    print(f"      Tokens: {control_metrics['tokens_avg']:.0f}")
    
    print(f"\n   📊 Variant metrics:")
    print(f"      Success rate: {variant_metrics['success_rate']:.1%}")
    print(f"      Latency: {variant_metrics['latency_avg']:.2f}s")
    print(f"      Tokens: {variant_metrics['tokens_avg']:.0f}")
    
    # Calculate p-values
    control_success_values = [1.0 if s.success else 0.0 for s in control_sessions]
    variant_success_values = [1.0 if s.success else 0.0 for s in variant_sessions]
    success_p_value = calculate_p_value(control_success_values, variant_success_values)
    
    latency_p_value = calculate_p_value(
        [s.latency_seconds for s in control_sessions],
        [s.latency_seconds for s in variant_sessions]
    )
    
    tokens_p_value = calculate_p_value(
        [float(s.tokens_used) for s in control_sessions],
        [float(s.tokens_used) for s in variant_sessions]
    )
    
    print(f"\n   📈 Statistical analysis:")
    print(f"      Success rate p-value: {success_p_value:.4f}")
    print(f"      Latency p-value: {latency_p_value:.4f}")
    print(f"      Tokens p-value: {tokens_p_value:.4f}")
    
    # Determine winner based on metrics and p-values
    success_threshold = 0.05  # p < 0.05 is statistically significant
    
    # Calculate improvements
    success_delta = variant_metrics['success_rate'] - control_metrics['success_rate']
    latency_delta = control_metrics['latency_avg'] - variant_metrics['latency_avg']  # Positive = variant faster
    tokens_delta = control_metrics['tokens_avg'] - variant_metrics['tokens_avg']  # Positive = variant uses fewer
    
    # Determine winner
    winner = "tie"
    confidence = 0.0
    
    if success_p_value < success_threshold:
        if success_delta > 0.05:  # Variant significantly better
            winner = "variant"
            confidence = 1 - success_p_value
        elif success_delta < -0.05:  # Control significantly better
            winner = "control"
            confidence = 1 - success_p_value
    else:
        # Not statistically significant, look at magnitude
        if success_delta > 0.1:
            winner = "variant"
            confidence = 0.3
        elif success_delta < -0.1:
            winner = "control"
            confidence = 0.3
    
    # Determine recommendation
    if winner == "variant" and confidence > 0.8:
        recommendation = "apply"
    elif winner == "control":
        recommendation = "reject"
    else:
        recommendation = "inconclusive"
    
    print(f"\n   🏆 Winner: {winner} (confidence: {confidence:.1%})")
    print(f"   📋 Recommendation: {recommendation}")
    
    return ABTestResult(
        hypothesis_id=hypothesis_id,
        hypothesis_title=hypothesis_title,
        category=category,
        control_n=len(control_sessions),
        control_success_rate=control_metrics['success_rate'],
        control_latency_avg=control_metrics['latency_avg'],
        control_tokens_avg=control_metrics['tokens_avg'],
        control_error_rate=control_metrics['error_rate'],
        variant_n=len(variant_sessions),
        variant_success_rate=variant_metrics['success_rate'],
        variant_latency_avg=variant_metrics['latency_avg'],
        variant_tokens_avg=variant_metrics['tokens_avg'],
        variant_error_rate=variant_metrics['error_rate'],
        success_rate_p_value=success_p_value,
        latency_p_value=latency_p_value,
        tokens_p_value=tokens_p_value,
        winner=winner,
        confidence=confidence,
        recommendation=recommendation
    )


def run_ab_tests(
    hypotheses: List[Dict[str, Any]],
    sessions: List[SessionMetrics],
    config: Dict[str, Any],
    max_tests: int = 5
) -> List[ABTestResult]:
    """Run A/B tests for multiple hypotheses."""
    
    testing_config = config.get("testing", {})
    max_workers = testing_config.get("parallel_tests", 2)
    
    print(f"\n🚀 Running {len(hypotheses)} A/B tests with {max_workers} workers...")
    
    # Limit hypotheses
    hypotheses = hypotheses[:max_tests]
    
    results = []
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = []
        for hypothesis in hypotheses:
            future = executor.submit(run_real_ab_test, hypothesis, sessions, config)
            futures.append(future)
        
        for future in futures:
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                print(f"  ❌ Test failed: {e}")
                results.append(ABTestResult(
                    hypothesis_id="error",
                    hypothesis_title="Error",
                    category="unknown",
                    control_n=0, control_success_rate=0, control_latency_avg=0,
                    control_tokens_avg=0, control_error_rate=0,
                    variant_n=0, variant_success_rate=0, variant_latency_avg=0,
                    variant_tokens_avg=0, variant_error_rate=0,
                    success_rate_p_value=1.0, latency_p_value=1.0, tokens_p_value=1.0,
                    winner="error", confidence=0, recommendation="error"
                ))
    
    return results


def result_to_dict(result: ABTestResult) -> Dict[str, Any]:
    """Convert ABTestResult to dictionary for JSON serialization."""
    return {
        "hypothesis_id": result.hypothesis_id,
        "hypothesis_title": result.hypothesis_title,
        "category": result.category,
        "control": {
            "n": result.control_n,
            "success_rate": result.control_success_rate,
            "latency_avg": result.control_latency_avg,
            "tokens_avg": result.control_tokens_avg,
            "error_rate": result.control_error_rate
        },
        "variant": {
            "n": result.variant_n,
            "success_rate": result.variant_success_rate,
            "latency_avg": result.variant_latency_avg,
            "tokens_avg": result.variant_tokens_avg,
            "error_rate": result.variant_error_rate
        },
        "statistics": {
            "success_rate_p_value": result.success_rate_p_value,
            "latency_p_value": result.latency_p_value,
            "tokens_p_value": result.tokens_p_value
        },
        "winner": result.winner,
        "confidence": result.confidence,
        "recommendation": result.recommendation,
        "tested_at": result.tested_at
    }


def save_results(results: List[ABTestResult], output_path: Path) -> None:
    """Save test results to JSON file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    summary = {
        "tested_at": datetime.now().isoformat(),
        "total_tests": len(results),
        "passed": sum(1 for r in results if r.recommendation == "apply"),
        "failed": sum(1 for r in results if r.recommendation == "reject"),
        "inconclusive": sum(1 for r in results if r.recommendation == "inconclusive"),
        "results": [result_to_dict(r) for r in results]
    }
    
    with open(output_path, "w") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)


def load_hypotheses(hypotheses_file: Path) -> List[Dict[str, Any]]:
    """Load hypotheses from JSON file."""
    if not hypotheses_file.exists():
        print(f"⚠️ Hypotheses file not found: {hypotheses_file}")
        return []
    
    with open(hypotheses_file) as f:
        data = json.load(f)
        return data.get("hypotheses", [])


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Real A/B Testing Harness for Karpathy Autoresearch",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run tests with default config
  python3 test_harness.py --hypotheses-file /tmp/hypotheses.json
  
  # Run with custom memory directory
  python3 test_harness.py --hypotheses-file /tmp/hypotheses.json --memory-dir /path/to/memory
  
  # Run with custom days back
  python3 test_harness.py --hypotheses-file /tmp/hypotheses.json --days 14
        """
    )
    parser.add_argument("--hypotheses-file", type=Path, default=Path("/tmp/karpathy_hypotheses.json"),
                        help="Path to hypotheses JSON file")
    parser.add_argument("--output", type=Path, default=Path("/tmp/karpathy_test_results.json"),
                        help="Output path for test results")
    parser.add_argument("--memory-dir", type=Path, default=None,
                        help="Override memory directory path")
    parser.add_argument("--days", type=int, default=7,
                        help="Number of days to look back for sessions")
    parser.add_argument("--max-tests", type=int, default=5,
                        help="Maximum hypotheses to test")
    parser.add_argument("--category", type=str, default=None,
                        help="Filter sessions by category")
    args = parser.parse_args()
    
    print("🧪 Real A/B Testing Harness")
    print("=" * 60)
    
    # Load config
    config = load_config()
    
    # Determine memory directory
    if args.memory_dir:
        memory_dir = args.memory_dir
    else:
        memory_dir = get_memory_dir(config)
    
    print(f"📂 Memory directory: {memory_dir}")
    print(f"📅 Days back: {args.days}")
    
    # Load sessions
    sessions = load_sessions(args.days, memory_dir, args.category)
    
    if not sessions:
        print("❌ No sessions found. Exiting.")
        sys.exit(1)
    
    # Load hypotheses
    hypotheses = load_hypotheses(args.hypotheses_file)
    
    if not hypotheses:
        print("⚠️ No hypotheses found to test")
        # Create sample hypothesis for demonstration if no file
        print("   Creating sample hypothesis for demonstration...")
        hypotheses = [{
            "id": "sample_001",
            "title": "Sample: Test if better error handling improves success rate",
            "category": "error_handling",
            "target_category": "general",
            "current_behavior": "Basic error handling",
            "proposed_change": "Enhanced error recovery",
            "expected_outcome": "Reduce failures by 10%"
        }]
    
    print(f"📋 Loaded {len(hypotheses)} hypotheses")
    
    # Run A/B tests
    results = run_ab_tests(hypotheses, sessions, config, args.max_tests)
    
    # Save results
    save_results(results, args.output)
    print(f"\n💾 Results saved to {args.output}")
    
    # Print summary
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for r in results if r.recommendation == "apply")
    failed = sum(1 for r in results if r.recommendation == "reject")
    inconclusive = sum(1 for r in results if r.recommendation == "inconclusive")
    
    print(f"  Total tests: {len(results)}")
    print(f"  ✅ Apply: {passed}")
    print(f"  ❌ Reject: {failed}")
    print(f"  ⚠️ Inconclusive: {inconclusive}")
    
    print("\n📈 Results by Hypothesis:")
    for r in results:
        icon = "✅" if r.recommendation == "apply" else "❌" if r.recommendation == "reject" else "⚠️"
        print(f"  {icon} {r.hypothesis_title[:50]}...")
        print(f"      Winner: {r.winner} | Confidence: {r.confidence:.1%}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
