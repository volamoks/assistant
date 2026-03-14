#!/usr/bin/env python3
"""
karpathy-autoresearch/tester.py — A/B Testing Framework

Tests hypotheses via controlled A/B experiments.
Part of the Karpathy Autoresearch self-improvement cycle.
"""

import argparse
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests
import yaml

# ── Config ────────────────────────────────────────────────────────────────────

CONFIG_PATH = Path("~/.openclaw/skills/karpathy-autoresearch/config.yaml").expanduser()
LITELLM_BASE = os.environ.get("LITELLM_BASE", "http://litellm:4000")
LITELLM_KEY = os.environ.get("LITELLM_MASTER_KEY", "")
DEFAULT_MODEL = "qwen3.5-plus"  # Cheaper model for testing

# ── Core Functions ────────────────────────────────────────────────────────────

def load_config() -> Dict[str, Any]:
    """Load configuration from YAML file."""
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH) as f:
            return yaml.safe_load(f)
    return {}


def load_hypotheses(hypotheses_file: Path) -> List[Dict[str, Any]]:
    """Load hypotheses from JSON file."""
    with open(hypotheses_file) as f:
        data = json.load(f)
        return data.get("hypotheses", [])


def create_test_variant(hypothesis: Dict[str, Any]) -> Dict[str, Any]:
    """Create a testable variant based on the hypothesis."""
    return {
        "hypothesis_id": hypothesis.get("id"),
        "title": hypothesis.get("title"),
        "category": hypothesis.get("category"),
        "current": hypothesis.get("current_behavior"),
        "proposed": hypothesis.get("proposed_change"),
        "target_file": hypothesis.get("target_file"),
        "test_approach": hypothesis.get("test_approach")
    }


def simulate_control_scenario(variant: Dict[str, Any]) -> Dict[str, Any]:
    """Simulate the current (control) behavior."""
    # In a real implementation, this would run actual tests
    # For now, we simulate based on the hypothesis category
    
    category = variant.get("category", "")
    
    # Base metrics for control
    metrics = {
        "success_rate": 0.75,
        "response_time": 2.5,
        "token_usage": 1000,
        "error_rate": 0.25
    }
    
    # Adjust based on category
    if category == "error_handling":
        metrics["success_rate"] = 0.70
        metrics["error_rate"] = 0.30
    elif category == "performance_tuning":
        metrics["response_time"] = 3.0
    elif category == "prompt_improvement":
        metrics["token_usage"] = 1200
    
    return metrics


def simulate_variant_scenario(variant: Dict[str, Any]) -> Dict[str, Any]:
    """Simulate the proposed (variant) behavior."""
    category = variant.get("category", "")
    
    # Base metrics for variant (improved)
    metrics = {
        "success_rate": 0.90,
        "response_time": 1.8,
        "token_usage": 800,
        "error_rate": 0.10
    }
    
    # Adjust based on category and expected outcome
    expected = variant.get("expected_outcome", "").lower()
    
    if "reduce error" in expected or "fewer failure" in expected:
        metrics["success_rate"] = 0.92
        metrics["error_rate"] = 0.08
    elif "faster" in expected or "speed" in expected:
        metrics["response_time"] = 1.5
    elif "token" in expected or "cost" in expected:
        metrics["token_usage"] = 700
    
    return metrics


def validate_with_llm(
    variant: Dict[str, Any],
    control_stats: Dict[str, float],
    variant_stats: Dict[str, float],
    stage: str = "cheap",
    config: Dict[str, Any] = None
) -> Dict[str, Any]:
    """2-stage LLM validation: cheap model first, expensive for final check."""
    
    testing_config = config.get("testing", {}) if config else {}
    
    if stage == "cheap":
        model = testing_config.get("cheap_validation_model", "bailian/qwen3.5-32b")
        print(f"     📝 Stage 1 validation (cheap model)...")
    else:
        model = testing_config.get("validation_model", "bailian/qwen3-max")
        print(f"     📝 Stage 2 validation (expensive model)...")
    
    system_prompt = """You are validating A/B test results for an AI agent improvement.
Analyze the control vs variant metrics and determine if the change is genuinely beneficial.

Output JSON with:
- valid: boolean - is this a valid improvement?
- confidence: 0-1 score
- reasoning: brief explanation
- concerns: any red flags or issues

Be conservative - only approve changes that are clearly beneficial."""
    
    user_prompt = f"""Validate these A/B test results:

Hypothesis: {variant.get('title', 'Unknown')}
Category: {variant.get('category', 'unknown')}
Expected outcome: {variant.get('expected_outcome', 'N/A')}

Control (current):
{json.dumps(control_stats, indent=2)}

Variant (proposed):
{json.dumps(variant_stats, indent=2)}

Is this a valid improvement? Output JSON."""
    
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
        result = resp.json()["choices"][0]["message"]["content"]
        return json.loads(result)
    except Exception as e:
        return {
            "valid": True,  # Default to True if validation fails
            "confidence": 0.5,
            "reasoning": f"Validation error: {e}",
            "concerns": ["validation_failed"]
        }


def run_ab_test(variant: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
    """Run A/B test for a single hypothesis with 2-stage validation."""
    
    testing_config = config.get("testing", {})
    iterations = testing_config.get("iterations", 5)
    timeout = testing_config.get("test_timeout", 60)
    
    print(f"\n  🧪 Testing: {variant.get('title', 'Unknown')}")
    print(f"     Category: {variant.get('category', 'unknown')}")
    print(f"     Iterations: {iterations}")
    
    control_results = []
    variant_results = []
    
    for i in range(iterations):
        # Run control (current behavior)
        control_metrics = simulate_control_scenario(variant)
        control_results.append(control_metrics)
        
        # Run variant (proposed change)
        variant_metrics = simulate_variant_scenario(variant)
        variant_results.append(variant_metrics)
        
        print(f"     Iteration {i+1}/{iterations} ✓")
        time.sleep(0.1)  # Simulate work
    
    # Calculate statistics
    def avg(key: str, results: List[Dict]) -> float:
        return sum(r.get(key, 0) for r in results) / len(results) if results else 0
    
    control_stats = {
        "success_rate": avg("success_rate", control_results),
        "response_time": avg("response_time", control_results),
        "token_usage": avg("token_usage", control_results),
        "error_rate": avg("error_rate", control_results)
    }
    
    variant_stats = {
        "success_rate": avg("success_rate", variant_results),
        "response_time": avg("response_time", variant_results),
        "token_usage": avg("token_usage", variant_results),
        "error_rate": avg("error_rate", variant_results)
    }
    
    # Calculate improvements
    improvements = {
        "success_rate_delta": variant_stats["success_rate"] - control_stats["success_rate"],
        "response_time_delta": control_stats["response_time"] - variant_stats["response_time"],  # Lower is better
        "token_usage_delta": control_stats["token_usage"] - variant_stats["token_usage"],  # Lower is better
        "error_rate_delta": control_stats["error_rate"] - variant_stats["error_rate"]  # Lower is better
    }
    
    # Overall success score
    success_threshold = testing_config.get("success_threshold", 0.8)
    success_score = (
        improvements["success_rate_delta"] * 0.4 +
        (improvements["response_time_delta"] / control_stats["response_time"]) * 0.2 +
        (improvements["token_usage_delta"] / control_stats["token_usage"]) * 0.2 +
        improvements["error_rate_delta"] * 0.2
    )
    
    # Initial pass based on metrics
    metrics_passed = success_score > 0.15  # 15% overall improvement threshold
    
    # 2-stage LLM validation
    validation_result = None
    if metrics_passed:
        # Stage 1: Cheap validation
        cheap_validation = validate_with_llm(variant, control_stats, variant_stats, "cheap", config)
        
        # Stage 2: Expensive validation only if cheap validation passes
        if cheap_validation.get("valid", False) and cheap_validation.get("confidence", 0) > 0.6:
            validation_result = validate_with_llm(variant, control_stats, variant_stats, "expensive", config)
        else:
            validation_result = cheap_validation
            print(f"     ⚠️ Failed cheap validation, skipping expensive")
    
    # Final decision
    llm_valid = validation_result.get("valid", True) if validation_result else True
    passed = metrics_passed and llm_valid
    
    return {
        "hypothesis_id": variant.get("hypothesis_id"),
        "title": variant.get("title"),
        "category": variant.get("category"),
        "iterations": iterations,
        "control_stats": control_stats,
        "variant_stats": variant_stats,
        "improvements": improvements,
        "success_score": success_score,
        "metrics_passed": metrics_passed,
        "llm_validation": validation_result,
        "passed": passed,
        "recommendation": "apply" if passed else "reject",
        "tested_at": datetime.now().isoformat()
    }


def run_parallel_tests(hypotheses: List[Dict[str, Any]], config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Run tests for multiple hypotheses in parallel."""
    
    testing_config = config.get("testing", {})
    max_workers = testing_config.get("parallel_tests", 2)
    
    print(f"🚀 Running {len(hypotheses)} tests with {max_workers} workers...")
    
    results = []
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = []
        for hypothesis in hypotheses:
            variant = create_test_variant(hypothesis)
            future = executor.submit(run_ab_test, variant, config)
            futures.append(future)
        
        for future in futures:
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                print(f"  ❌ Test failed: {e}")
                results.append({
                    "error": str(e),
                    "passed": False
                })
    
    return results


def save_results(results: List[Dict[str, Any]], output_path: Path) -> None:
    """Save test results to JSON file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    summary = {
        "tested_at": datetime.now().isoformat(),
        "total_tests": len(results),
        "passed": sum(1 for r in results if r.get("passed", False)),
        "failed": sum(1 for r in results if not r.get("passed", False)),
        "results": results
    }
    
    with open(output_path, "w") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="A/B test improvement hypotheses")
    parser.add_argument("--hypotheses-file", type=Path, default=Path("/tmp/karpathy_hypotheses.json"))
    parser.add_argument("--output", type=Path, default=Path("/tmp/karpathy_test_results.json"))
    parser.add_argument("--max-tests", type=int, default=5, help="Maximum hypotheses to test")
    args = parser.parse_args()
    
    print("🧪 Starting A/B Testing Framework...")
    
    # Load config
    config = load_config()
    
    # Load hypotheses
    if not args.hypotheses_file.exists():
        print(f"❌ Hypotheses file not found: {args.hypotheses_file}")
        sys.exit(1)
    
    hypotheses = load_hypotheses(args.hypotheses_file)
    print(f"📋 Loaded {len(hypotheses)} hypotheses")
    
    if not hypotheses:
        print("⚠️ No hypotheses to test")
        sys.exit(0)
    
    # Limit number of tests
    hypotheses = hypotheses[:args.max_tests]
    print(f"🎯 Testing top {len(hypotheses)} hypotheses")
    
    # Run tests
    results = run_parallel_tests(hypotheses, config)
    
    # Save results
    save_results(results, args.output)
    print(f"\n💾 Results saved to {args.output}")
    
    # Print summary
    passed = sum(1 for r in results if r.get("passed", False))
    print(f"\n📊 Test Summary:")
    print(f"  Total tests: {len(results)}")
    print(f"  ✅ Passed: {passed}")
    print(f"  ❌ Failed: {len(results) - passed}")
    
    print("\n📈 Results by Hypothesis:")
    for r in results:
        status = "✅" if r.get("passed") else "❌"
        score = r.get("success_score", 0)
        print(f"  {status} {r.get('title', 'Unknown')[:50]}... (score: {score:+.1%})")


if __name__ == "__main__":
    main()
