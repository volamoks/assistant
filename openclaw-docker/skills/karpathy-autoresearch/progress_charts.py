#!/usr/bin/env python3
"""
karpathy-autoresearch/progress_charts.py — Progress Charts Generator

Generates visual progress charts for the Karpathy Autoresearch system:
- Success rate over time
- Latency trends
- Token usage
- Number of applied patches

Part of the Karpathy Autoresearch self-improvement cycle (P2).
"""

import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Try to import matplotlib - it's optional
try:
    import matplotlib
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    print("⚠️ matplotlib not available, charts will be disabled")

# ── Config ────────────────────────────────────────────────────────────────────

SKILL_DIR = Path("~/.openclaw/skills/karpathy-autoresearch").expanduser()
CONFIG_PATH = SKILL_DIR / "config.yaml"
METRICS_HISTORY_PATH = Path("/tmp/karpathy_metrics_history.json")
FEEDBACK_LOG_PATH = Path("/tmp/karpathy_feedback.log")
OUTPUT_DIR = SKILL_DIR / "output"
CHARTS_DIR = Path("/tmp/autoresearch_charts")

# ── Data Loading ───────────────────────────────────────────────────────────

def load_config() -> Dict[str, Any]:
    """Load configuration from YAML file."""
    import yaml
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH) as f:
            return yaml.safe_load(f)
    return {}


def load_metrics_history() -> List[Dict[str, Any]]:
    """Load metrics history from file."""
    if not METRICS_HISTORY_PATH.exists():
        return []
    
    try:
        return json.loads(METRICS_HISTORY_PATH.read_text())
    except (json.JSONDecodeError, FileNotFoundError):
        return []


def load_feedback_history() -> List[Dict[str, Any]]:
    """Load feedback history from log file."""
    if not FEEDBACK_LOG_PATH.exists():
        return []
    
    history = []
    try:
        with open(FEEDBACK_LOG_PATH) as f:
            for line in f:
                try:
                    entry = json.loads(line)
                    history.append(entry)
                except json.JSONDecodeError:
                    continue
    except FileNotFoundError:
        pass
    
    return history


def load_cycle_history() -> List[Dict[str, Any]]:
    """Load cycle history from output directory."""
    if not OUTPUT_DIR.exists():
        return []
    
    cycles = []
    for cycle_file in sorted(OUTPUT_DIR.glob("cycle_*.json")):
        try:
            with open(cycle_file) as f:
                cycles.append(json.load(f))
        except (json.JSONDecodeError, FileNotFoundError):
            continue
    
    return cycles


def load_applied_patches() -> List[Dict[str, Any]]:
    """Load applied patches from file."""
    applied_patches_path = Path("/tmp/karpathy_applied_patches.json")
    if not applied_patches_path.exists():
        return []
    
    try:
        return json.loads(applied_patches_path.read_text())
    except (json.JSONDecodeError, FileNotFoundError):
        return []


# ── Chart Generation ───────────────────────────────────────────────────────

def _setup_chart_style():
    """Setup chart styling for Telegram."""
    # Use a clean style suitable for dark/light themes
    plt.style.use('seaborn-v0_8-darkgrid')
    
    # Set defaults
    plt.rcParams.update({
        'font.size': 10,
        'axes.titlesize': 12,
        'axes.labelsize': 10,
        'xtick.labelsize': 8,
        'ytick.labelsize': 8,
        'legend.fontsize': 8,
        'figure.titlesize': 14,
        'figure.facecolor': '#1a1a2e',
        'axes.facecolor': '#16213e',
        'axes.edgecolor': '#0f3460',
        'axes.labelcolor': '#e0e0e0',
        'text.color': '#e0e0e0',
        'xtick.color': '#e0e0e0',
        'ytick.color': '#e0e0e0',
        'grid.color': '#0f3460',
        'grid.alpha': 0.5
    })


def generate_success_rate_chart(
    metrics_history: List[Dict[str, Any]],
    output_path: Optional[Path] = None
) -> Optional[str]:
    """Generate success rate over time chart."""
    
    if not metrics_history or len(metrics_history) < 2:
        return None
    
    if not MATPLOTLIB_AVAILABLE:
        return None
    
    # Extract data
    timestamps = []
    success_rates = []
    
    for entry in metrics_history:
        try:
            ts = datetime.fromisoformat(entry.get("timestamp", ""))
            sr = entry.get("success_rate", 0)
            timestamps.append(ts)
            success_rates.append(sr * 100)  # Convert to percentage
        except (ValueError, TypeError):
            continue
    
    if not timestamps:
        return None
    
    # Create chart
    _setup_chart_style()
    fig, ax = plt.subplots(figsize=(10, 5), dpi=100)
    
    ax.plot(timestamps, success_rates, marker='o', linewidth=2, 
            markersize=4, color='#00d4ff', label='Success Rate')
    
    # Add trend line
    if len(timestamps) >= 3:
        import numpy as np
        x_numeric = mdates.date2num(timestamps)
        z = np.polyfit(x_numeric, success_rates, 1)
        p = np.poly1d(z)
        ax.plot(timestamps, p(x_numeric), '--', color='#ff6b6b', 
                alpha=0.7, label='Trend')
    
    # Formatting
    ax.set_xlabel('Date')
    ax.set_ylabel('Success Rate (%)')
    ax.set_title('📈 Success Rate Over Time')
    ax.set_ylim(0, 100)
    ax.legend(loc='lower right')
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
    ax.xaxis.set_major_locator(mdates.AutoDateLocator())
    
    plt.tight_layout()
    
    # Save
    CHARTS_DIR.mkdir(parents=True, exist_ok=True)
    if output_path is None:
        output_path = CHARTS_DIR / "success_rate.png"
    
    plt.savefig(output_path, facecolor=fig.get_facecolor(), 
                edgecolor='none', dpi=100, bbox_inches='tight')
    plt.close()
    
    return str(output_path)


def generate_latency_chart(
    metrics_history: List[Dict[str, Any]],
    output_path: Optional[Path] = None
) -> Optional[str]:
    """Generate latency trends chart."""
    
    if not metrics_history or len(metrics_history) < 2:
        return None
    
    if not MATPLOTLIB_AVAILABLE:
        return None
    
    # Extract data
    timestamps = []
    latencies = []
    
    for entry in metrics_history:
        try:
            ts = datetime.fromisoformat(entry.get("timestamp", ""))
            lat = entry.get("latency_avg", 0)
            timestamps.append(ts)
            latencies.append(lat)
        except (ValueError, TypeError):
            continue
    
    if not timestamps:
        return None
    
    # Create chart
    _setup_chart_style()
    fig, ax = plt.subplots(figsize=(10, 5), dpi=100)
    
    ax.plot(timestamps, latencies, marker='s', linewidth=2,
            markersize=4, color='#4ade80', label='Latency (s)')
    
    # Add moving average
    if len(latencies) >= 5:
        import numpy as np
        ma = np.convolve(latencies, np.ones(3)/3, mode='valid')
        ax.plot(timestamps[1:-1], ma, '--', color='#fbbf24',
                alpha=0.7, label='3-period MA')
    
    # Formatting
    ax.set_xlabel('Date')
    ax.set_ylabel('Latency (seconds)')
    ax.set_title('⚡ Latency Trends')
    ax.legend(loc='upper right')
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
    ax.xaxis.set_major_locator(mdates.AutoDateLocator())
    
    plt.tight_layout()
    
    # Save
    CHARTS_DIR.mkdir(parents=True, exist_ok=True)
    if output_path is None:
        output_path = CHARTS_DIR / "latency.png"
    
    plt.savefig(output_path, facecolor=fig.get_facecolor(),
                edgecolor='none', dpi=100, bbox_inches='tight')
    plt.close()
    
    return str(output_path)


def generate_token_usage_chart(
    metrics_history: List[Dict[str, Any]],
    output_path: Optional[Path] = None
) -> Optional[str]:
    """Generate token usage chart."""
    
    if not metrics_history or len(metrics_history) < 2:
        return None
    
    if not MATPLOTLIB_AVAILABLE:
        return None
    
    # Extract data
    timestamps = []
    tokens = []
    
    for entry in metrics_history:
        try:
            ts = datetime.fromisoformat(entry.get("timestamp", ""))
            tok = entry.get("tokens_avg", 0)
            timestamps.append(ts)
            tokens.append(tok)
        except (ValueError, TypeError):
            continue
    
    if not timestamps:
        return None
    
    # Create chart
    _setup_chart_style()
    fig, ax = plt.subplots(figsize=(10, 5), dpi=100)
    
    ax.fill_between(timestamps, tokens, alpha=0.3, color='#a855f7')
    ax.plot(timestamps, tokens, marker='^', linewidth=2,
            markersize=4, color='#a855f7', label='Token Usage')
    
    # Formatting
    ax.set_xlabel('Date')
    ax.set_ylabel('Average Tokens')
    ax.set_title('💰 Token Usage Over Time')
    ax.legend(loc='upper right')
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
    ax.xaxis.set_major_locator(mdates.AutoDateLocator())
    
    plt.tight_layout()
    
    # Save
    CHARTS_DIR.mkdir(parents=True, exist_ok=True)
    if output_path is None:
        output_path = CHARTS_DIR / "token_usage.png"
    
    plt.savefig(output_path, facecolor=fig.get_facecolor(),
                edgecolor='none', dpi=100, bbox_inches='tight')
    plt.close()
    
    return str(output_path)


def generate_patches_chart(
    cycles: List[Dict[str, Any]],
    output_path: Optional[Path] = None
) -> Optional[str]:
    """Generate applied patches chart."""
    
    if not cycles:
        return None
    
    if not MATPLOTLIB_AVAILABLE:
        return None
    
    # Count applied patches per cycle
    cycle_dates = []
    applied_counts = []
    successful_counts = []
    
    for cycle in cycles:
        try:
            completed = cycle.get("completed_at", "")
            if not completed:
                continue
            
            ts = datetime.fromisoformat(completed)
            cycle_dates.append(ts)
            
            # Count from application step
            steps = cycle.get("steps", {})
            app_step = steps.get("application", {})
            
            if app_step.get("status") == "success":
                applied_counts.append(1)
            else:
                applied_counts.append(0)
            
            # Count successful tests
            test_step = steps.get("testing", {})
            if test_step.get("status") == "success":
                # Try to load results
                results_file = test_step.get("output")
                if results_file and Path(results_file).exists():
                    try:
                        with open(results_file) as f:
                            results = json.load(f)
                            passed = sum(1 for r in results.get("results", []) 
                                       if r.get("passed", False))
                            successful_counts.append(passed)
                    except:
                        successful_counts.append(0)
                else:
                    successful_counts.append(0)
            else:
                successful_counts.append(0)
                
        except (ValueError, TypeError, KeyError):
            continue
    
    if not cycle_dates:
        return None
    
    # Create chart
    _setup_chart_style()
    fig, ax = plt.subplots(figsize=(10, 5), dpi=100)
    
    x = range(len(cycle_dates))
    width = 0.35
    
    bars1 = ax.bar([i - width/2 for i in x], applied_counts, width, 
                   label='Applied', color='#22c55e')
    bars2 = ax.bar([i + width/2 for i in x], successful_counts, width,
                   label='Successful Tests', color='#3b82f6')
    
    # Add count labels
    for bar in bars1:
        height = bar.get_height()
        if height > 0:
            ax.annotate(f'{int(height)}',
                       xy=(bar.get_x() + bar.get_width() / 2, height),
                       ha='center', va='bottom', fontsize=8)
    
    # Formatting
    ax.set_xlabel('Cycle')
    ax.set_ylabel('Count')
    ax.set_title('🔧 Applied Patches Per Cycle')
    ax.set_xticks(x)
    ax.set_xticklabels([d.strftime('%m/%d') for d in cycle_dates], rotation=45)
    ax.legend()
    
    plt.tight_layout()
    
    # Save
    CHARTS_DIR.mkdir(parents=True, exist_ok=True)
    if output_path is None:
        output_path = CHARTS_DIR / "patches.png"
    
    plt.savefig(output_path, facecolor=fig.get_facecolor(),
                edgecolor='none', dpi=100, bbox_inches='tight')
    plt.close()
    
    return str(output_path)


def generate_feedback_effectiveness_chart(
    feedback_history: List[Dict[str, Any]],
    output_path: Optional[Path] = None
) -> Optional[str]:
    """Generate patch effectiveness chart."""
    
    if not feedback_history:
        return None
    
    if not MATPLOTLIB_AVAILABLE:
        return None
    
    # Count verdicts
    verdicts = {"improved": 0, "degraded": 0, "neutral": 0, "insufficient_data": 0}
    
    for entry in feedback_history:
        verdict = entry.get("verdict", "neutral")
        if verdict in verdicts:
            verdicts[verdict] += 1
    
    if sum(verdicts.values()) == 0:
        return None
    
    # Create chart
    _setup_chart_style()
    fig, ax = plt.subplots(figsize=(8, 5), dpi=100)
    
    colors = ['#22c55e', '#ef4444', '#fbbf24', '#6b7280']
    labels = ['✅ Improved', '❌ Degraded', '⚖️ Neutral', '❓ Insufficient']
    values = [verdicts["improved"], verdicts["degraded"], 
              verdicts["neutral"], verdicts["insufficient_data"]]
    
    # Filter out zero values
    filtered_labels = [l for l, v in zip(labels, values) if v > 0]
    filtered_values = [v for v in values if v > 0]
    filtered_colors = [c for c, v in zip(colors, values) if v > 0]
    
    if not filtered_values:
        return None
    
    wedges, texts, autotexts = ax.pie(
        filtered_values, 
        labels=filtered_labels,
        colors=filtered_colors,
        autopct='%1.1f%%',
        startangle=90,
        textprops={'color': '#e0e0e0'}
    )
    
    ax.set_title('🎯 Patch Effectiveness Distribution')
    
    plt.tight_layout()
    
    # Save
    CHARTS_DIR.mkdir(parents=True, exist_ok=True)
    if output_path is None:
        output_path = CHARTS_DIR / "effectiveness.png"
    
    plt.savefig(output_path, facecolor=fig.get_facecolor(),
                edgecolor='none', dpi=100, bbox_inches='tight')
    plt.close()
    
    return str(output_path)


def generate_all_charts() -> Dict[str, Optional[str]]:
    """Generate all progress charts."""
    
    charts = {}
    
    if not MATPLOTLIB_AVAILABLE:
        print("⚠️ matplotlib not available, skipping chart generation")
        return charts
    
    # Load data
    metrics_history = load_metrics_history()
    feedback_history = load_feedback_history()
    cycles = load_cycle_history()
    
    print(f"📊 Generating charts...")
    print(f"   Metrics history: {len(metrics_history)} entries")
    print(f"   Feedback history: {len(feedback_history)} entries")
    print(f"   Cycles: {len(cycles)} entries")
    
    # Generate each chart
    charts["success_rate"] = generate_success_rate_chart(metrics_history)
    if charts["success_rate"]:
        print(f"   ✅ Success rate chart: {charts['success_rate']}")
    
    charts["latency"] = generate_latency_chart(metrics_history)
    if charts["latency"]:
        print(f"   ✅ Latency chart: {charts['latency']}")
    
    charts["token_usage"] = generate_token_usage_chart(metrics_history)
    if charts["token_usage"]:
        print(f"   ✅ Token usage chart: {charts['token_usage']}")
    
    charts["patches"] = generate_patches_chart(cycles)
    if charts["patches"]:
        print(f"   ✅ Patches chart: {charts['patches']}")
    
    charts["effectiveness"] = generate_feedback_effectiveness_chart(feedback_history)
    if charts["effectiveness"]:
        print(f"   ✅ Effectiveness chart: {charts['effectiveness']}")
    
    return charts


def generate_summary_text() -> str:
    """Generate a text summary of progress."""
    
    metrics_history = load_metrics_history()
    feedback_history = load_feedback_history()
    cycles = load_cycle_history()
    
    lines = ["📊 *Autoresearch Progress Summary*", ""]
    
    # Overall stats
    if metrics_history:
        latest = metrics_history[-1]
        lines.append(f"📈 *Latest Metrics:*")
        lines.append(f"  Success Rate: `{latest.get('success_rate', 0)*100:.1f}%`")
        lines.append(f"  Latency: `{latest.get('latency_avg', 0):.2f}s`")
        lines.append(f"  Tokens: `{latest.get('tokens_avg', 0):.0f}`")
        lines.append("")
    
    # Cycles
    lines.append(f"🔄 *Cycles:* `{len(cycles)}` completed")
    
    # Feedback
    if feedback_history:
        improved = sum(1 for e in feedback_history if e.get("verdict") == "improved")
        degraded = sum(1 for e in feedback_history if e.get("verdict") == "degraded")
        lines.append(f"")
        lines.append(f"🎯 *Patch Effectiveness:*")
        lines.append(f"  ✅ Improved: `{improved}`")
        lines.append(f"  ❌ Degraded: `{degraded}`")
    
    return "\n".join(lines)


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Generate progress charts for Autoresearch"
    )
    parser.add_argument("--output-dir", type=Path, help="Output directory for charts")
    parser.add_argument("--show", action="store_true", help="Show charts on screen")
    args = parser.parse_args()
    
    if not MATPLOTLIB_AVAILABLE:
        print("❌ matplotlib is required for chart generation")
        print("   Install with: pip install matplotlib")
        return 1
    
    # Generate charts
    charts = generate_all_charts()
    
    print(f"\n✅ Generated {len([c for c in charts.values() if c])} charts")
    
    # Show if requested
    if args.show:
        plt.show()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
