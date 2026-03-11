#!/usr/bin/env python3
"""
karpathy-autoresearch/run.py — Main Orchestrator

Runs the complete Karpathy Autoresearch cycle:
1. Analyze logs → 2. Feature Discovery → 3. Generate hypotheses → 4. Test → 5. Apply → 6. Report

v2: Night mode + Feature Discovery + 2-stage validation
"""

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

# ── Config ────────────────────────────────────────────────────────────────────

SKILL_DIR = Path("~/.openclaw/skills/karpathy-autoresearch").expanduser()
CONFIG_PATH = SKILL_DIR / "config.yaml"

# ── Core Functions ────────────────────────────────────────────────────────────

def load_config() -> Dict[str, Any]:
    """Load configuration from YAML file."""
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH) as f:
            return yaml.safe_load(f)
    return {}


def run_step(script_name: str, args: List[str], description: str) -> bool:
    """Run a single step of the autoresearch cycle."""
    script_path = SKILL_DIR / script_name
    
    print(f"\n{'='*60}")
    print(f"🔄 {description}")
    print(f"{'='*60}")
    
    cmd = [sys.executable, str(script_path)] + args
    
    # Pass environment variables to subprocess
    env = os.environ.copy()
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=False,
            text=True,
            check=True,
            env=env
        )
        print(f"✅ {description} completed")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed: {e}")
        return False


def is_night_mode(config: Dict[str, Any]) -> bool:
    """Check if current time is within night mode window."""
    night_config = config.get("night_mode", {})
    if not night_config.get("enabled", False):
        return False
    
    now = datetime.now()
    current_hour = now.hour
    start_hour = night_config.get("start_hour", 2)
    end_hour = night_config.get("end_hour", 6)
    
    return start_hour <= current_hour < end_hour


def get_iterations_for_mode(config: Dict[str, Any]) -> int:
    """Get iteration count based on night/day mode."""
    night_config = config.get("night_mode", {})
    testing_config = config.get("testing", {})
    
    if is_night_mode(config) and night_config.get("extended_iterations", False):
        return 50  # Night mode: 50 iterations
    return testing_config.get("iterations", 5)  # Day mode: default 5


def get_parallel_workers(config: Dict[str, Any]) -> int:
    """Get parallel workers based on night/day mode."""
    night_config = config.get("night_mode", {})
    testing_config = config.get("testing", {})
    
    if is_night_mode(config):
        return night_config.get("parallel_workers", 5)  # Night: 5 workers
    return testing_config.get("parallel_tests", 2)  # Day: 2 workers


def run_full_cycle(config: Dict[str, Any], dry_run: bool = False, use_real_harness: bool = None, use_simulation: bool = False) -> Dict[str, Any]:
    """Run the complete autoresearch cycle with Feature Discovery."""
    
    results = {
        "started_at": datetime.now().isoformat(),
        "mode": "night" if is_night_mode(config) else "day",
        "steps": {},
        "success": False
    }
    
    analysis_config = config.get("analysis", {})
    testing_config = config.get("testing", {})
    application_config = config.get("application", {})
    feature_discovery_config = config.get("feature_discovery", {})
    
    days_back = analysis_config.get("days_back", 7)
    max_tests = testing_config.get("max_hypotheses", 5)
    
    # Adjust iterations and workers based on mode
    iterations = get_iterations_for_mode(config)
    parallel_workers = get_parallel_workers(config)
    
    print(f"\n🌙 Night mode: {is_night_mode(config)}")
    print(f"   Iterations: {iterations}")
    print(f"   Parallel workers: {parallel_workers}")
    
    # Step 1: Analyze logs
    print("\n📊 STEP 1: Analyze session logs...")
    if run_step(
        "analyzer.py",
        ["--days", str(days_back), "--output", "/tmp/karpathy_patterns.json"],
        "Log Analysis"
    ):
        results["steps"]["analysis"] = {"status": "success", "output": "/tmp/karpathy_patterns.json"}
    else:
        results["steps"]["analysis"] = {"status": "failed"}
        return results
    
    # Step 2: Feature Discovery (NEW in v2)
    if feature_discovery_config.get("enabled", False):
        print("\n🔍 STEP 2: Feature Discovery...")
        if run_step(
            "feature_discovery.py",
            ["--days", str(days_back), "--output", "/tmp/karpathy_features.json"],
            "Feature Discovery"
        ):
            results["steps"]["feature_discovery"] = {"status": "success", "output": "/tmp/karpathy_features.json"}
        else:
            results["steps"]["feature_discovery"] = {"status": "failed"}
            # Don't fail the whole cycle if feature discovery fails
    else:
        print("\n🔍 STEP 2: Feature Discovery (SKIPPED - disabled)")
        results["steps"]["feature_discovery"] = {"status": "skipped", "reason": "disabled"}
    
    # Step 3: Generate hypotheses
    print("\n💡 STEP 3: Generate improvement hypotheses...")
    if run_step(
        "hypothesis.py",
        ["--patterns-file", "/tmp/karpathy_patterns.json", "--output", "/tmp/karpathy_hypotheses.json"],
        "Hypothesis Generation"
    ):
        results["steps"]["hypothesis"] = {"status": "success", "output": "/tmp/karpathy_hypotheses.json"}
    else:
        results["steps"]["hypothesis"] = {"status": "failed"}
        return results
    
    # Step 4: Test hypotheses (with 2-stage validation)
    if use_real_harness is None:
        # Default from config
        use_real_harness = testing_config.get("use_real_harness", True)

    if use_simulation:
        use_real_harness = False
    
    test_script = "test_harness.py" if use_real_harness else "tester.py"
    print(f"\n🧪 STEP 4: A/B test hypotheses ({'real harness' if use_real_harness else 'simulation'})...")
    if run_step(
        test_script,
        [
            "--hypotheses-file", "/tmp/karpathy_hypotheses.json",
            "--output", "/tmp/karpathy_test_results.json",
            "--max-tests", str(max_tests)
        ],
        "A/B Testing"
    ):
        results["steps"]["testing"] = {"status": "success", "output": "/tmp/karpathy_test_results.json"}
    else:
        results["steps"]["testing"] = {"status": "failed"}
        return results
    
    # Step 5: Apply changes (if not dry run)
    if not dry_run:
        print("\n📝 STEP 5: Apply successful changes...")
        force_flag = ["--force"] if application_config.get("auto_apply", False) else []
        if run_step(
            "applier.py",
            ["--test-results", "/tmp/karpathy_test_results.json"] + force_flag,
            "Change Application"
        ):
            results["steps"]["application"] = {"status": "success"}
        else:
            results["steps"]["application"] = {"status": "failed"}
            # Don't fail the whole cycle if application fails
    else:
        print("\n📝 STEP 5: Apply changes (SKIPPED - dry run)")
        results["steps"]["application"] = {"status": "skipped", "reason": "dry_run"}
    
    # Step 6: Report results
    print("\n📤 STEP 6: Send Telegram report...")
    if run_step(
        "reporter.py",
        [
            "--patterns-file", "/tmp/karpathy_patterns.json",
            "--hypotheses-file", "/tmp/karpathy_hypotheses.json",
            "--test-results-file", "/tmp/karpathy_test_results.json",
            "--compact"
        ],
        "Telegram Reporting"
    ):
        results["steps"]["reporting"] = {"status": "success"}
    else:
        results["steps"]["reporting"] = {"status": "failed"}
    
    results["completed_at"] = datetime.now().isoformat()
    results["success"] = True
    
    return results


def save_cycle_results(results: Dict[str, Any]) -> None:
    """Save cycle results to history."""
    output_dir = SKILL_DIR / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = output_dir / f"cycle_{timestamp}.json"
    
    with open(results_file, "w") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 Cycle results saved to {results_file}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Run Karpathy Autoresearch cycle",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run full cycle
  python3 run.py
  
  # Dry run (no changes applied)
  python3 run.py --dry-run
  
  # Run specific steps only
  python3 run.py --steps analyze,hypothesis
  
  # Force apply changes (override auto_apply setting)
  python3 run.py --force-apply
        """
    )
    parser.add_argument("--dry-run", action="store_true", help="Run without applying changes")
    parser.add_argument("--steps", type=str, help="Comma-separated steps to run (analyze,hypothesis,test,apply,report)")
    parser.add_argument("--force-apply", action="store_true", help="Force apply changes")
    parser.add_argument("--days", type=int, help="Override days_back in config")
    parser.add_argument("--use-real-harness", action="store_true", default=None, 
                       help="Use real A/B test harness (instead of simulation)")
    parser.add_argument("--use-simulation", action="store_true",
                       help="Use simulation-based tester (legacy)")
    args = parser.parse_args()
    
    print("🔄 Karpathy Autoresearch")
    print("=" * 60)
    print("Autonomous self-improvement cycle for OpenClaw agents")
    print("=" * 60)
    
    # Load config
    config = load_config()
    
    # Override config with CLI args
    if args.days:
        config["analysis"] = config.get("analysis", {})
        config["analysis"]["days_back"] = args.days
    
    if args.force_apply:
        config["application"] = config.get("application", {})
        config["application"]["auto_apply"] = True
    
    # Run cycle
    results = run_full_cycle(config, dry_run=args.dry_run, use_real_harness=args.use_real_harness, use_simulation=args.use_simulation)
    
    # Save results
    save_cycle_results(results)
    
    # Print summary
    print("\n" + "=" * 60)
    print("📋 CYCLE SUMMARY")
    print("=" * 60)
    
    for step_name, step_result in results["steps"].items():
        status = step_result.get("status", "unknown")
        icon = "✅" if status == "success" else "❌" if status == "failed" else "⏭️"
        print(f"{icon} {step_name.capitalize()}: {status}")
    
    print("\n" + "=" * 60)
    
    if results["success"]:
        print("🎉 Autoresearch cycle completed successfully!")
        return 0
    else:
        print("⚠️ Autoresearch cycle completed with some failures")
        return 1


if __name__ == "__main__":
    sys.exit(main())
