#!/usr/bin/env python3
"""
karpathy-autoresearch/feedback_loop.py — Feedback Loop System

Tracks effectiveness of applied changes by comparing metrics BEFORE and AFTER patches.
Logs results for analysis and continuous improvement.

Part of the Karpathy Autoresearch self-improvement cycle (P1).
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml

# ── Config ────────────────────────────────────────────────────────────────────

CONFIG_PATH = Path("~/.openclaw/skills/karpathy-autoresearch/config.yaml").expanduser()
FEEDBACK_LOG_PATH = Path("/tmp/karpathy_feedback.log")
METRICS_HISTORY_PATH = Path("/tmp/karpathy_metrics_history.json")

# ── Data Classes ────────────────────────────────────────────────────────────

@dataclass
class MetricsSnapshot:
    """A snapshot of metrics at a point in time."""
    timestamp: str
    success_rate: float
    latency_avg: float
    tokens_avg: float
    error_rate: float
    session_count: int
    category: str


@dataclass
class PatchEffectiveness:
    """Effectiveness analysis of an applied patch."""
    patch_id: str
    hypothesis_id: str
    file_path: str
    
    # Metrics before patch
    before_metrics: MetricsSnapshot
    
    # Metrics after patch
    after_metrics: MetricsSnapshot
    
    # Analysis
    success_rate_delta: float
    latency_delta: float
    tokens_delta: float
    error_rate_delta: float
    
    # Verdict
    effective: bool
    verdict: str  # "improved", "degraded", "neutral", "insufficient_data"
    confidence: float
    recommendation: str  # "keep", "rollback", "investigate"


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


# ── Metric Extraction ───────────────────────────────────────────────────────

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


def extract_session_metrics(filepath: Path) -> List[Dict[str, Any]]:
    """Extract metrics from a session file."""
    sessions = []
    
    try:
        content = filepath.read_text(encoding="utf-8")
    except Exception:
        return sessions
    
    # Split into session blocks
    session_blocks = re.split(r"##\s+🕐\s+\d{2}:\d{2}\s+UTC", content)
    
    for idx, block in enumerate(session_blocks):
        if not block.strip() or len(block.strip()) < 50:
            continue
        
        session_id = f"{filepath.stem}_{idx}"
        
        # Check success/error
        success_count = sum(len(re.findall(p, block, re.IGNORECASE)) for p in SUCCESS_PATTERNS)
        error_count = sum(len(re.findall(p, block, re.IGNORECASE)) for p in ERROR_PATTERNS)
        success = success_count > error_count and success_count > 0
        
        # Extract latency
        latency = 2.5  # Default
        for pattern in LATENCY_PATTERNS:
            matches = re.findall(pattern, block, re.IGNORECASE)
            if matches:
                try:
                    value = float(matches[0][0] if isinstance(matches[0], tuple) else matches[0])
                    unit = matches[0][1] if isinstance(matches[0], tuple) and len(matches[0]) > 1 else "s"
                    if unit in ("мс", "ms"):
                        latency = value / 1000
                    else:
                        latency = value
                    break
                except (ValueError, IndexError):
                    pass
        
        # Extract tokens
        tokens = 1000  # Default
        for pattern in TOKEN_PATTERNS:
            matches = re.findall(pattern, block, re.IGNORECASE)
            if matches:
                try:
                    tokens = int(matches[0])
                    break
                except (ValueError, IndexError):
                    pass
        
        # Determine category
        category = "general"
        if "code" in block.lower() or "python" in block.lower():
            category = "coding"
        elif "search" in block.lower() or "web" in block.lower():
            category = "search"
        elif "file" in block.lower():
            category = "file_ops"
        
        sessions.append({
            "session_id": session_id,
            "timestamp": filepath.stem,
            "success": success,
            "latency": latency,
            "tokens": tokens,
            "error_count": error_count,
            "category": category
        })
    
    return sessions


def calculate_metrics(sessions: List[Dict[str, Any]], category: str = None) -> MetricsSnapshot:
    """Calculate aggregated metrics from sessions."""
    if category:
        sessions = [s for s in sessions if s.get("category") == category]
    
    if not sessions:
        return MetricsSnapshot(
            timestamp=datetime.now().isoformat(),
            success_rate=0.0,
            latency_avg=0.0,
            tokens_avg=0.0,
            error_rate=0.0,
            session_count=0,
            category=category or "all"
        )
    
    successes = sum(1 for s in sessions if s.get("success"))
    total_errors = sum(s.get("error_count", 0) for s in sessions)
    
    return MetricsSnapshot(
        timestamp=datetime.now().isoformat(),
        success_rate=successes / len(sessions),
        latency_avg=sum(s.get("latency", 0) for s in sessions) / len(sessions),
        tokens_avg=sum(s.get("tokens", 0) for s in sessions) / len(sessions),
        error_rate=total_errors / len(sessions),
        session_count=len(sessions),
        category=category or "all"
    )


def get_metrics_for_period(
    days_back: int,
    memory_dir: Path,
    category: str = None,
    end_date: datetime = None
) -> MetricsSnapshot:
    """Get metrics for a specific time period."""
    if end_date is None:
        end_date = datetime.now()
    
    start_date = end_date - timedelta(days=days_back)
    
    all_sessions = []
    
    for i in range(days_back):
        date = start_date + timedelta(days=i)
        filename = date.strftime("%Y-%m-%d.md")
        filepath = memory_dir / filename
        
        if filepath.exists():
            sessions = extract_session_metrics(filepath)
            all_sessions.extend(sessions)
    
    return calculate_metrics(all_sessions, category)


# ── Feedback Loop Core ─────────────────────────────────────────────────────

def analyze_patch_effectiveness(
    patch_id: str,
    hypothesis_id: str,
    file_path: str,
    patch_timestamp: str,
    config: Dict[str, Any],
    before_days: int = 7,
    after_days: int = 3
) -> PatchEffectiveness:
    """Analyze effectiveness of an applied patch."""
    
    print(f"\n📊 Analyzing patch: {patch_id}")
    
    memory_dir = get_memory_dir(config)
    
    # Determine category from patch
    category = None
    if "python" in file_path.lower() or "coding" in file_path.lower():
        category = "coding"
    elif "search" in file_path.lower():
        category = "search"
    elif "file" in file_path.lower():
        category = "file_ops"
    
    # Get patch timestamp
    try:
        patch_time = datetime.fromisoformat(patch_timestamp.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        patch_time = datetime.now()
    
    # Get BEFORE metrics
    print(f"   Getting BEFORE metrics (last {before_days} days before patch)...")
    before_end = patch_time - timedelta(days=1)
    before_metrics = get_metrics_for_period(
        before_days, memory_dir, category, before_end
    )
    
    print(f"      Sessions: {before_metrics.session_count}")
    print(f"      Success rate: {before_metrics.success_rate:.1%}")
    print(f"      Latency: {before_metrics.latency_avg:.2f}s")
    print(f"      Error rate: {before_metrics.error_rate:.1%}")
    
    # Get AFTER metrics
    print(f"   Getting AFTER metrics (last {after_days} days after patch)...")
    after_metrics = get_metrics_for_period(
        after_days, memory_dir, category, datetime.now()
    )
    
    print(f"      Sessions: {after_metrics.session_count}")
    print(f"      Success rate: {after_metrics.success_rate:.1%}")
    print(f"      Latency: {after_metrics.latency_avg:.2f}s")
    print(f"      Error rate: {after_metrics.error_rate:.1%}")
    
    # Calculate deltas
    success_rate_delta = after_metrics.success_rate - before_metrics.success_rate
    latency_delta = before_metrics.latency_avg - after_metrics.latency_avg  # Positive = improvement
    tokens_delta = before_metrics.tokens_avg - after_metrics.tokens_avg  # Positive = improvement
    error_rate_delta = before_metrics.error_rate - after_metrics.error_rate  # Positive = improvement
    
    # Determine verdict
    verdict = "insufficient_data"
    effective = False
    
    min_sessions = 10  # Minimum sessions for meaningful comparison
    
    if before_metrics.session_count < min_sessions or after_metrics.session_count < min_sessions:
        verdict = "insufficient_data"
        confidence = 0.0
    else:
        # Calculate confidence based on sample size
        sample_confidence = min(1.0, (before_metrics.session_count + after_metrics.session_count) / 50)
        
        # Determine verdict based on deltas
        improvements = sum([
            success_rate_delta > 0.05,
            latency_delta > 0.1,
            error_rate_delta > 0.05,
            tokens_delta > 0
        ])
        
        degradations = sum([
            success_rate_delta < -0.05,
            latency_delta < -0.1,
            error_rate_delta < -0.05,
            tokens_delta < 0
        ])
        
        if improvements > degradations and improvements >= 2:
            verdict = "improved"
            effective = True
            confidence = sample_confidence * 0.8
        elif degradations > improvements and degradations >= 2:
            verdict = "degraded"
            effective = False
            confidence = sample_confidence * 0.8
        else:
            verdict = "neutral"
            effective = None
            confidence = sample_confidence * 0.5
    
    # Determine recommendation
    if verdict == "improved" and confidence > 0.6:
        recommendation = "keep"
    elif verdict == "degraded" and confidence > 0.6:
        recommendation = "rollback"
    elif verdict == "insufficient_data":
        recommendation = "investigate"
    else:
        recommendation = "investigate"
    
    return PatchEffectiveness(
        patch_id=patch_id,
        hypothesis_id=hypothesis_id,
        file_path=file_path,
        before_metrics=before_metrics,
        after_metrics=after_metrics,
        success_rate_delta=success_rate_delta,
        latency_delta=latency_delta,
        tokens_delta=tokens_delta,
        error_rate_delta=error_rate_delta,
        effective=effective,
        verdict=verdict,
        confidence=confidence,
        recommendation=recommendation
    )


def log_feedback(effectiveness: PatchEffectiveness) -> None:
    """Log feedback to file."""
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "patch_id": effectiveness.patch_id,
        "hypothesis_id": effectiveness.hypothesis_id,
        "verdict": effectiveness.verdict,
        "effective": effectiveness.effective,
        "confidence": effectiveness.confidence,
        "recommendation": effectiveness.recommendation,
        "metrics": {
            "before": {
                "success_rate": effectiveness.before_metrics.success_rate,
                "latency": effectiveness.before_metrics.latency_avg,
                "tokens": effectiveness.before_metrics.tokens_avg,
                "error_rate": effectiveness.before_metrics.error_rate,
                "sessions": effectiveness.before_metrics.session_count
            },
            "after": {
                "success_rate": effectiveness.after_metrics.success_rate,
                "latency": effectiveness.after_metrics.latency_avg,
                "tokens": effectiveness.after_metrics.tokens_avg,
                "error_rate": effectiveness.after_metrics.error_rate,
                "sessions": effectiveness.after_metrics.session_count
            },
            "delta": {
                "success_rate": effectiveness.success_rate_delta,
                "latency": effectiveness.latency_delta,
                "tokens": effectiveness.tokens_delta,
                "error_rate": effectiveness.error_rate_delta
            }
        }
    }
    
    # Append to log file
    FEEDBACK_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    with open(FEEDBACK_LOG_PATH, "a") as f:
        f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")


def get_metrics_history() -> List[Dict[str, Any]]:
    """Get history of metrics snapshots."""
    if not METRICS_HISTORY_PATH.exists():
        return []
    
    try:
        return json.loads(METRICS_HISTORY_PATH.read_text())
    except (json.JSONDecodeError, FileNotFoundError):
        return []


def save_metrics_snapshot(metrics: MetricsSnapshot) -> None:
    """Save a metrics snapshot to history."""
    history = get_metrics_history()
    
    snapshot = {
        "timestamp": metrics.timestamp,
        "success_rate": metrics.success_rate,
        "latency_avg": metrics.latency_avg,
        "tokens_avg": metrics.tokens_avg,
        "error_rate": metrics.error_rate,
        "session_count": metrics.session_count,
        "category": metrics.category
    }
    
    history.append(snapshot)
    
    # Keep only last 100 snapshots
    history = history[-100:]
    
    METRICS_HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(METRICS_HISTORY_PATH, "w") as f:
        json.dump(history, f, indent=2)


def format_effectiveness_report(effectiveness: PatchEffectiveness) -> str:
    """Format effectiveness analysis as a readable report."""
    
    lines = [
        f"\n{'='*60}",
        f"📊 PATCH EFFECTIVENESS REPORT",
        f"{'='*60}",
        f"Patch ID: {effectiveness.patch_id}",
        f"Hypothesis: {effectiveness.hypothesis_id}",
        f"File: {effectiveness.file_path}",
        "",
        f"📈 METRICS COMPARISON:",
        f"",
        f"  BEFORE (last 7 days before patch):",
        f"    Sessions: {effectiveness.before_metrics.session_count}",
        f"    Success Rate: {effectiveness.before_metrics.success_rate:.1%}",
        f"    Latency: {effectiveness.before_metrics.latency_avg:.2f}s",
        f"    Tokens: {effectiveness.before_metrics.tokens_avg:.0f}",
        f"    Error Rate: {effectiveness.before_metrics.error_rate:.1%}",
        "",
        f"  AFTER (last 3 days after patch):",
        f"    Sessions: {effectiveness.after_metrics.session_count}",
        f"    Success Rate: {effectiveness.after_metrics.success_rate:.1%}",
        f"    Latency: {effectiveness.after_metrics.latency_avg:.2f}s",
        f"    Tokens: {effectiveness.after_metrics.tokens_avg:.0f}",
        f"    Error Rate: {effectiveness.after_metrics.error_rate:.1%}",
        "",
        f"  DELTA (positive = improvement):",
        f"    Success Rate: {effectiveness.success_rate_delta:+.1%}",
        f"    Latency: {effectiveness.latency_delta:+.2f}s",
        f"    Tokens: {effectiveness.tokens_delta:+.0f}",
        f"    Error Rate: {effectiveness.error_rate_delta:+.1%}",
        "",
    ]
    
    # Verdict
    verdict_emoji = {
        "improved": "✅",
        "degraded": "❌",
        "neutral": "⚖️",
        "insufficient_data": "❓"
    }
    
    verdict_text = {
        "improved": "IMPROVED",
        "degraded": "DEGRADED",
        "neutral": "NEUTRAL",
        "insufficient_data": "INSUFFICIENT DATA"
    }
    
    lines.extend([
        f"🏆 VERDICT: {verdict_emoji.get(effectiveness.verdict, '?')} {verdict_text.get(effectiveness.verdict, 'UNKNOWN')}",
        f"   Confidence: {effectiveness.confidence:.0%}",
        f"   Recommendation: {effectiveness.recommendation.upper()}",
        f"{'='*60}\n"
    ])
    
    return "\n".join(lines)


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Feedback Loop for Karpathy Autoresearch",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze a specific patch
  python3 feedback_loop.py --patch-id patch_001 --hypothesis-id hyp_001 --file /path/to/SKILL.md --timestamp 2026-03-01T00:00:00
  
  # Get current metrics snapshot
  python3 feedback_loop.py --snapshot --days 7
  
  # View feedback history
  python3 feedback_loop.py --history
  
  # Analyze all recent patches
  python3 feedback_loop.py --analyze-all
        """
    )
    parser.add_argument("--patch-id", type=str, help="Patch ID to analyze")
    parser.add_argument("--hypothesis-id", type=str, help="Hypothesis ID")
    parser.add_argument("--file", type=Path, help="File that was patched")
    parser.add_argument("--timestamp", type=str, help="Patch timestamp (ISO format)")
    parser.add_argument("--snapshot", action="store_true", help="Take current metrics snapshot")
    parser.add_argument("--days", type=int, default=7, help="Days for snapshot")
    parser.add_argument("--category", type=str, help="Filter by category")
    parser.add_argument("--history", action="store_true", help="View feedback history")
    parser.add_argument("--analyze-all", action="store_true", help="Analyze all applied patches")
    parser.add_argument("--output", type=Path, default=Path("/tmp/karpathy_feedback.json"))
    args = parser.parse_args()
    
    print("🔄 Feedback Loop System")
    print("=" * 60)
    
    # Load config
    config = load_config()
    memory_dir = get_memory_dir(config)
    
    # History mode
    if args.history:
        if FEEDBACK_LOG_PATH.exists():
            print(f"\n📋 Feedback History:")
            with open(FEEDBACK_LOG_PATH) as f:
                for line in f:
                    try:
                        entry = json.loads(line)
                        emoji = "✅" if entry.get("effective") else "❌" if entry["effective"] is False else "⚖️"
                        print(f"  {emoji} [{entry['verdict']}] {entry['patch_id']}")
                        print(f"     {entry['timestamp']}")
                    except json.JSONDecodeError:
                        continue
        else:
            print("No feedback history found.")
        return 0
    
    # Snapshot mode
    if args.snapshot:
        print(f"\n📸 Taking metrics snapshot (last {args.days} days)...")
        
        metrics = get_metrics_for_period(args.days, memory_dir, args.category)
        
        print(f"   Sessions: {metrics.session_count}")
        print(f"   Success Rate: {metrics.success_rate:.1%}")
        print(f"   Latency: {metrics.latency_avg:.2f}s")
        print(f"   Tokens: {metrics.tokens_avg:.0f}")
        print(f"   Error Rate: {metrics.error_rate:.1%}")
        
        save_metrics_snapshot(metrics)
        print(f"   Saved to {METRICS_HISTORY_PATH}")
        
        return 0
    
    # Analyze all patches
    if args.analyze_all:
        import json as json_module
        
        applied_patches_path = Path("/tmp/karpathy_applied_patches.json")
        if not applied_patches_path.exists():
            print("No applied patches found.")
            return 1
        
        patches = json_module.loads(applied_patches_path.read_text())
        
        if not patches:
            print("No patches to analyze.")
            return 0
        
        print(f"\n🔄 Analyzing {len(patches)} applied patches...")
        
        for patch in patches:
            effectiveness = analyze_patch_effectiveness(
                patch_id=patch["id"],
                hypothesis_id=patch.get("hypothesis_id", "unknown"),
                file_path=patch["file_path"],
                patch_timestamp=patch["timestamp"],
                config=config
            )
            
            # Log feedback
            log_feedback(effectiveness)
            
            # Print report
            print(format_effectiveness_report(effectiveness))
        
        return 0
    
    # Analyze single patch
    if args.patch_id and args.file and args.timestamp:
        effectiveness = analyze_patch_effectiveness(
            patch_id=args.patch_id,
            hypothesis_id=args.hypothesis_id or "unknown",
            file_path=str(args.file),
            patch_timestamp=args.timestamp,
            config=config
        )
        
        # Log feedback
        log_feedback(effectiveness)
        
        # Print report
        report = format_effectiveness_report(effectiveness)
        print(report)
        
        # Save result
        result = {
            "patch_id": effectiveness.patch_id,
            "hypothesis_id": effectiveness.hypothesis_id,
            "file_path": effectiveness.file_path,
            "verdict": effectiveness.verdict,
            "effective": effectiveness.effective,
            "confidence": effectiveness.confidence,
            "recommendation": effectiveness.recommendation,
            "metrics": {
                "before": {
                    "success_rate": effectiveness.before_metrics.success_rate,
                    "latency": effectiveness.before_metrics.latency_avg,
                    "tokens": effectiveness.before_metrics.tokens_avg,
                    "error_rate": effectiveness.before_metrics.error_rate,
                    "sessions": effectiveness.before_metrics.session_count
                },
                "after": {
                    "success_rate": effectiveness.after_metrics.success_rate,
                    "latency": effectiveness.after_metrics.latency_avg,
                    "tokens": effectiveness.after_metrics.tokens_avg,
                    "error_rate": effectiveness.after_metrics.error_rate,
                    "sessions": effectiveness.after_metrics.session_count
                },
                "delta": {
                    "success_rate": effectiveness.success_rate_delta,
                    "latency": effectiveness.latency_delta,
                    "tokens": effectiveness.tokens_delta,
                    "error_rate": effectiveness.error_rate_delta
                }
            }
        }
        
        with open(args.output, "w") as f:
            json.dump(result, f, indent=2)
        
        print(f"\n💾 Results saved to {args.output}")
        
        return 0
    
    else:
        print("❌ Please specify --patch-id/--file/--timestamp or use --snapshot/--history/--analyze-all")
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
