#!/usr/bin/env python3
"""
karpathy-autoresearch/reporter.py — Telegram Reporter

Sends autoresearch results to Telegram.
Part of the Karpathy Autoresearch self-improvement cycle.
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests
import yaml

# ── Config ────────────────────────────────────────────────────────────────────

CONFIG_PATH = Path("~/.openclaw/skills/karpathy-autoresearch/config.yaml").expanduser()
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

# ── Core Functions ────────────────────────────────────────────────────────────

def load_config() -> Dict[str, Any]:
    """Load configuration from YAML file."""
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH) as f:
            return yaml.safe_load(f)
    return {}


def load_json_file(filepath: Path) -> Dict[str, Any]:
    """Load JSON file."""
    with open(filepath) as f:
        return json.load(f)


def format_patterns_report(patterns: Dict[str, Any]) -> str:
    """Format patterns analysis for Telegram."""
    lines = [
        "📊 *Pattern Analysis*",
        "",
        f"📁 Files analyzed: `{patterns.get('total_files', 0)}`",
        f"🔴 Total errors: `{patterns.get('total_errors', 0)}`",
        f"🟢 Total successes: `{patterns.get('total_successes', 0)}`",
    ]
    
    # Error types
    error_types = patterns.get('error_types', {})
    if error_types:
        lines.append("")
        lines.append("🔴 *Top Error Patterns:*")
        for pattern, count in sorted(error_types.items(), key=lambda x: -x[1])[:3]:
            lines.append(f"  • `{pattern}`: {count}")
    
    # Tool usage
    tool_usage = patterns.get('tool_usage', {})
    if tool_usage:
        lines.append("")
        lines.append("🔧 *Tool Usage:*")
        for tool, count in sorted(tool_usage.items(), key=lambda x: -x[1])[:3]:
            lines.append(f"  • `{tool}`: {count}")
    
    # LLM analysis summary
    llm_analysis = patterns.get('llm_analysis', {})
    if llm_analysis and 'error' not in llm_analysis:
        recommendations = llm_analysis.get('recommendations', [])
        if recommendations:
            lines.append("")
            lines.append("💡 *AI Recommendations:*")
            for rec in recommendations[:2]:
                lines.append(f"  • {rec}")
    
    return '\n'.join(lines)


def format_hypotheses_report(hypotheses_data: Dict[str, Any]) -> str:
    """Format hypotheses for Telegram."""
    hypotheses = hypotheses_data.get('hypotheses', [])
    
    lines = [
        "🧠 *Generated Hypotheses*",
        f"",
        f"💡 Total: `{len(hypotheses)}`",
    ]
    
    # Top hypotheses
    for h in hypotheses[:3]:
        lines.append("")
        lines.append(f"*{h.get('rank', '?')}. {h.get('title', 'Unknown')}*")
        lines.append(f"  Category: `{h.get('category', 'unknown')}`")
        lines.append(f"  Confidence: `{h.get('confidence', 0):.0%}`")
        lines.append(f"  Score: `{h.get('score', 0):.0f}/100`")
        expected = h.get('expected_outcome', '')
        if expected:
            lines.append(f"  Expected: _{expected[:60]}..._")
    
    return '\n'.join(lines)


def format_test_results_report(results_data: Dict[str, Any]) -> str:
    """Format test results for Telegram."""
    results = results_data.get('results', [])
    total = results_data.get('total_tests', len(results))
    passed = results_data.get('passed', sum(1 for r in results if r.get('passed', False)))
    
    lines = [
        "🧪 *A/B Test Results*",
        "",
        f"📊 Total tests: `{total}`",
        f"✅ Passed: `{passed}`",
        f"❌ Failed: `{total - passed}`",
    ]
    
    # Passed tests details
    passed_tests = [r for r in results if r.get('passed', False)]
    if passed_tests:
        lines.append("")
        lines.append("✅ *Successful Improvements:*")
        for r in passed_tests[:3]:
            lines.append("")
            lines.append(f"*{r.get('title', 'Unknown')[:40]}...*")
            
            improvements = r.get('improvements', {})
            if improvements:
                sr_delta = improvements.get('success_rate_delta', 0)
                if sr_delta > 0:
                    lines.append(f"  📈 Success rate: `+{sr_delta:.1%}`")
                
                rt_delta = improvements.get('response_time_delta', 0)
                if rt_delta > 0:
                    lines.append(f"  ⚡ Response time: `-{rt_delta:.1f}s`")
                
                tu_delta = improvements.get('token_usage_delta', 0)
                if tu_delta > 0:
                    lines.append(f"  💰 Token usage: `-{tu_delta:.0f}`")
            
            lines.append(f"  Overall score: `{r.get('success_score', 0):.1%}`")
    
    return '\n'.join(lines)


def format_full_report(
    patterns: Optional[Dict[str, Any]],
    hypotheses: Optional[Dict[str, Any]],
    test_results: Optional[Dict[str, Any]]
) -> str:
    """Format full report for Telegram."""
    
    lines = [
        "🔄 *Karpathy Autoresearch Report*",
        f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}",
        "",
        "─" * 30,
        ""
    ]
    
    if patterns:
        lines.append(format_patterns_report(patterns))
        lines.append("")
        lines.append("─" * 30)
        lines.append("")
    
    if hypotheses:
        lines.append(format_hypotheses_report(hypotheses))
        lines.append("")
        lines.append("─" * 30)
        lines.append("")
    
    if test_results:
        lines.append(format_test_results_report(test_results))
        lines.append("")
        lines.append("─" * 30)
        lines.append("")
    
    # Footer
    lines.append("🤖 *Autoresearch cycle complete*")
    lines.append("_Review and approve changes via /karpathy_approve_")
    
    return '\n'.join(lines)


def send_telegram_message(message: str, chat_id: str, token: str) -> bool:
    """Send message to Telegram."""
    if not token or not chat_id:
        print("❌ Telegram credentials not configured")
        return False
    
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    
    # Escape special characters for MarkdownV1
    # Characters that need escaping: _ * [ ] ( ) ~ ` > # + - = | { } . !
    import re
    escaped_message = re.sub(r'([_\*\[\]\(\)~`>#+=|{}\.!])', r'\\\1', message)
    
    payload = {
        "chat_id": chat_id,
        "text": escaped_message,
        "parse_mode": "MarkdownV2",
        "disable_web_page_preview": True
    }
    
    try:
        resp = requests.post(url, json=payload, timeout=30)
        if resp.status_code != 200:
            # Try without parse_mode if markdown fails
            payload_plain = {
                "chat_id": chat_id,
                "text": message,
                "disable_web_page_preview": True
            }
            resp = requests.post(url, json=payload_plain, timeout=30)
            resp.raise_for_status()
        return True
    except Exception as e:
        print(f"❌ Failed to send Telegram message: {e}")
        return False


def send_compact_summary(
    patterns: Optional[Dict[str, Any]],
    hypotheses: Optional[Dict[str, Any]],
    test_results: Optional[Dict[str, Any]],
    chat_id: str,
    token: str
) -> bool:
    """Send compact summary to Telegram."""
    
    # Count stats
    total_errors = patterns.get('total_errors', 0) if patterns else 0
    total_hypotheses = len(hypotheses.get('hypotheses', [])) if hypotheses else 0
    
    if test_results:
        results = test_results.get('results', [])
        passed = sum(1 for r in results if r.get('passed', False))
        total_tests = len(results)
    else:
        passed = 0
        total_tests = 0
    
    message = f"""🔄 *Autoresearch Complete*

📊 *Analysis:*
  Errors found: `{total_errors}`
  Hypotheses: `{total_hypotheses}`

🧪 *Tests:*
  Passed: `{passed}/{total_tests}`

💡 *Top Recommendation:*
"""
    
    # Add top recommendation
    if test_results and passed > 0:
        passed_tests = [r for r in results if r.get('passed', False)]
        if passed_tests:
            top = passed_tests[0]
            message += f"_{top.get('title', 'None')[:50]}..._"
            message += f"\n  Score: `{top.get('success_score', 0):.1%}`"
    elif hypotheses and total_hypotheses > 0:
        top = hypotheses['hypotheses'][0]
        message += f"_{top.get('title', 'None')[:50]}..._"
        message += f"\n  Confidence: `{top.get('confidence', 0):.0%}`"
    else:
        message += "_No significant improvements identified_"
    
    message += "\n\n_Review full report in logs_"
    
    return send_telegram_message(message, chat_id, token)


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Send autoresearch report to Telegram")
    parser.add_argument("--patterns-file", type=Path, default=Path("/tmp/karpathy_patterns.json"))
    parser.add_argument("--hypotheses-file", type=Path, default=Path("/tmp/karpathy_hypotheses.json"))
    parser.add_argument("--test-results-file", type=Path, default=Path("/tmp/karpathy_test_results.json"))
    parser.add_argument("--compact", action="store_true", help="Send compact summary")
    parser.add_argument("--chat-id", default=TELEGRAM_CHAT_ID)
    parser.add_argument("--token", default=TELEGRAM_BOT_TOKEN)
    args = parser.parse_args()
    
    print("📤 Preparing Telegram report...")
    
    # Load config
    config = load_config()
    reporting_config = config.get("reporting", {})
    
    # Determine chat_id and token
    chat_id = args.chat_id or reporting_config.get("chat_id", "")
    token = args.token or reporting_config.get("token", "")
    
    if not chat_id or not token:
        print("❌ Telegram credentials not configured")
        print("   Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID environment variables")
        sys.exit(1)
    
    # Load data files
    patterns = None
    hypotheses = None
    test_results = None
    
    if args.patterns_file.exists():
        patterns = load_json_file(args.patterns_file)
        print(f"✅ Loaded patterns: {patterns.get('total_files', 0)} files")
    
    if args.hypotheses_file.exists():
        hypotheses = load_json_file(args.hypotheses_file)
        print(f"✅ Loaded hypotheses: {len(hypotheses.get('hypotheses', []))}")
    
    if args.test_results_file.exists():
        test_results = load_json_file(args.test_results_file)
        print(f"✅ Loaded test results: {test_results.get('total_tests', 0)} tests")
    
    # Send report
    if args.compact:
        success = send_compact_summary(patterns, hypotheses, test_results, chat_id, token)
    else:
        message = format_full_report(patterns, hypotheses, test_results)
        success = send_telegram_message(message, chat_id, token)
    
    if success:
        print("✅ Report sent to Telegram")
    else:
        print("❌ Failed to send report")
        sys.exit(1)


if __name__ == "__main__":
    main()
