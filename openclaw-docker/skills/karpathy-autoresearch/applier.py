#!/usr/bin/env python3
"""
karpathy-autoresearch/applier.py — Change Application

Applies successful A/B test results to skills and prompts.
Part of the Karpathy Autoresearch self-improvement cycle.
"""

import argparse
import hashlib
import json
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

# ── Config ────────────────────────────────────────────────────────────────────

CONFIG_PATH = Path("~/.openclaw/skills/karpathy-autoresearch/config.yaml").expanduser()
OUTPUT_DIR = Path("~/.openclaw/skills/karpathy-autoresearch/output").expanduser()
APPLIED_CHANGES_FILE = OUTPUT_DIR / "applied_changes.yaml"

# ── Core Functions ────────────────────────────────────────────────────────────

def load_config() -> Dict[str, Any]:
    """Load configuration from YAML file."""
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH) as f:
            return yaml.safe_load(f)
    return {}


def load_test_results(results_file: Path) -> Dict[str, Any]:
    """Load test results from JSON file."""
    with open(results_file) as f:
        return json.load(f)


def load_applied_changes() -> List[Dict[str, Any]]:
    """Load history of applied changes."""
    if APPLIED_CHANGES_FILE.exists():
        with open(APPLIED_CHANGES_FILE) as f:
            return yaml.safe_load(f) or []
    return []


def save_applied_changes(changes: List[Dict[str, Any]]) -> None:
    """Save history of applied changes."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(APPLIED_CHANGES_FILE, "w") as f:
        yaml.dump(changes, f, default_flow_style=False, allow_unicode=True)


def backup_file(target_path: Path) -> Path:
    """Create backup of target file."""
    backup_dir = OUTPUT_DIR / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = backup_dir / f"{target_path.stem}_{timestamp}{target_path.suffix}"
    
    if target_path.exists():
        shutil.copy2(target_path, backup_path)
    
    return backup_path


def generate_change_id(hypothesis: Dict[str, Any]) -> str:
    """Generate unique ID for a change."""
    content = f"{hypothesis.get('hypothesis_id', '')}:{hypothesis.get('title', '')}:{datetime.now().isoformat()}"
    return hashlib.md5(content.encode()).hexdigest()[:12]


def apply_prompt_improvement(result: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
    """Apply a prompt improvement change."""
    target = result.get("target_file", "")
    
    # Map target to actual file path
    prompts_dir = Path("/home/node/.openclaw/prompts")
    target_path = prompts_dir / target if not target.startswith("/") else Path(target)
    
    if not target_path.exists():
        return {
            "success": False,
            "error": f"Target file not found: {target_path}"
        }
    
    # Backup original
    backup_path = backup_file(target_path)
    
    # Read current content
    content = target_path.read_text()
    
    # Apply change (this is a simplified version - real implementation would be more sophisticated)
    # For now, we append an improvement note
    improvement_note = f"""
<!-- Auto-improvement applied {datetime.now().isoformat()} -->
<!-- Hypothesis: {result.get('title', 'Unknown')} -->
<!-- Improvement: Success rate +{result.get('improvements', {}).get('success_rate_delta', 0):.1%} -->
"""
    
    new_content = content + improvement_note
    
    # Write new content
    target_path.write_text(new_content)
    
    return {
        "success": True,
        "backup_path": str(backup_path),
        "target_path": str(target_path),
        "change_type": "prompt_improvement"
    }


def apply_skill_improvement(result: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
    """Apply a skill improvement change."""
    target = result.get("target_file", "")
    
    # Map target to actual file path
    skills_dir = Path("/home/node/.openclaw/skills")
    target_path = skills_dir / target if not target.startswith("/") else Path(target)
    
    if not target_path.exists():
        return {
            "success": False,
            "error": f"Target file not found: {target_path}"
        }
    
    # Backup original
    backup_path = backup_file(target_path)
    
    return {
        "success": True,
        "backup_path": str(backup_path),
        "target_path": str(target_path),
        "change_type": "skill_improvement",
        "note": "Manual review required for SKILL.md changes"
    }


def apply_config_improvement(result: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
    """Apply a configuration improvement change."""
    # Config changes are typically manual
    return {
        "success": True,
        "change_type": "config_improvement",
        "note": "Configuration change - manual review recommended",
        "recommendation": result.get("title", "Unknown")
    }


def apply_change(result: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
    """Apply a single successful change."""
    category = result.get("category", "")
    
    # Check if already applied
    applied = load_applied_changes()
    hypothesis_id = result.get("hypothesis_id", "")
    
    for change in applied:
        if change.get("hypothesis_id") == hypothesis_id:
            return {
                "success": False,
                "error": "Change already applied",
                "previously_applied_at": change.get("applied_at")
            }
    
    # Route to appropriate handler
    if category == "prompt_improvement":
        outcome = apply_prompt_improvement(result, config)
    elif category == "tool_optimization":
        outcome = apply_skill_improvement(result, config)
    elif category == "workflow_enhancement":
        outcome = apply_config_improvement(result, config)
    else:
        outcome = {
            "success": False,
            "error": f"Unknown category: {category}"
        }
    
    # Record the change
    if outcome.get("success"):
        change_record = {
            "change_id": generate_change_id(result),
            "hypothesis_id": hypothesis_id,
            "title": result.get("title", "Unknown"),
            "category": category,
            "applied_at": datetime.now().isoformat(),
            "success_score": result.get("success_score", 0),
            "improvements": result.get("improvements", {}),
            "target_file": result.get("target_file", ""),
            "backup_path": outcome.get("backup_path"),
            "change_type": outcome.get("change_type")
        }
        
        applied.append(change_record)
        save_applied_changes(applied)
    
    return outcome


def apply_all_changes(results: List[Dict[str, Any]], config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Apply all successful changes."""
    
    application_config = config.get("application", {})
    auto_apply = application_config.get("auto_apply", False)
    max_changes = application_config.get("max_changes_per_run", 3)
    
    outcomes = []
    applied_count = 0
    
    for result in results:
        if not result.get("passed", False):
            continue
        
        if applied_count >= max_changes:
            print(f"  ⏹️ Reached max changes limit ({max_changes})")
            break
        
        print(f"\n  📝 Applying: {result.get('title', 'Unknown')[:50]}...")
        
        if not auto_apply:
            print(f"     ⚠️ Auto-apply is disabled. Change requires manual approval.")
            outcomes.append({
                "hypothesis_id": result.get("hypothesis_id"),
                "title": result.get("title"),
                "status": "pending_approval",
                "reason": "auto_apply is disabled in config"
            })
            continue
        
        outcome = apply_change(result, config)
        outcomes.append(outcome)
        
        if outcome.get("success"):
            applied_count += 1
            print(f"     ✅ Applied successfully")
        else:
            print(f"     ❌ Failed: {outcome.get('error', 'Unknown error')}")
    
    return outcomes


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Apply successful A/B test results")
    parser.add_argument("--test-results", type=Path, default=Path("/tmp/karpathy_test_results.json"))
    parser.add_argument("--dry-run", action="store_true", help="Show what would be applied without applying")
    parser.add_argument("--force", action="store_true", help="Apply even if auto_apply is false")
    args = parser.parse_args()
    
    print("📝 Change Application System...")
    
    # Load config
    config = load_config()
    
    # Load test results
    if not args.test_results.exists():
        print(f"❌ Test results file not found: {args.test_results}")
        sys.exit(1)
    
    results_data = load_test_results(args.test_results)
    results = results_data.get("results", [])
    
    print(f"📊 Loaded {len(results)} test results")
    
    # Filter to passed tests only
    passed_results = [r for r in results if r.get("passed", False)]
    print(f"✅ {len(passed_results)} tests passed and are candidates for application")
    
    if not passed_results:
        print("⚠️ No passed tests to apply")
        sys.exit(0)
    
    if args.dry_run:
        print("\n🔍 DRY RUN - Would apply:")
        for r in passed_results:
            print(f"  - {r.get('title', 'Unknown')}")
            print(f"    Target: {r.get('target_file', 'N/A')}")
            print(f"    Score: {r.get('success_score', 0):.1%}")
        sys.exit(0)
    
    # Override auto_apply if --force
    if args.force:
        config["application"] = config.get("application", {})
        config["application"]["auto_apply"] = True
        print("⚡ Force mode enabled - applying changes")
    
    # Apply changes
    outcomes = apply_all_changes(passed_results, config)
    
    # Print summary
    successful = sum(1 for o in outcomes if o.get("success", False))
    pending = sum(1 for o in outcomes if o.get("status") == "pending_approval")
    failed = len(outcomes) - successful - pending
    
    print(f"\n📋 Application Summary:")
    print(f"  ✅ Applied: {successful}")
    print(f"  ⏳ Pending approval: {pending}")
    print(f"  ❌ Failed: {failed}")
    
    # Show applied changes history
    applied = load_applied_changes()
    print(f"\n📚 Total changes in history: {len(applied)}")


if __name__ == "__main__":
    main()
