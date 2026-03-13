#!/usr/bin/env python3
"""
Morning Digest Skill

Generates and displays morning digest reports via A2UI.
Creates full report in Obsidian + short Telegram summary.

Usage:
    python3 morning_digest.py           # Generate today's digest
    python3 morning_digest.py --webapp # Show in A2UI WebApp
    python3 morning_digest.py --latest # Show latest report
"""

import os
import sys
import json
import argparse
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional

# Paths
VAULT_PATH = os.environ.get("USER_VAULT_PATH", "/data/obsidian/vault")
DATA_DIR = "/data/bot/openclaw-docker/data"
MORNING_REPORTS_DIR = f"{VAULT_PATH}/Bot/morning-reports"


def get_today_report() -> Optional[Dict[str, Any]]:
    """Get today's report data"""
    today = datetime.now().strftime("%Y-%m-%d")
    report_path = Path(MORNING_REPORTS_DIR) / f"{today}.md"
    
    if report_path.exists():
        return {
            "date": today,
            "path": str(report_path),
            "exists": True
        }
    return None


def get_latest_report() -> Optional[Dict[str, Any]]:
    """Get the most recent report"""
    reports_dir = Path(MORNING_REPORTS_DIR)
    if not reports_dir.exists():
        return None
    
    md_files = list(reports_dir.glob("*.md"))
    if not md_files:
        return None
    
    latest = max(md_files, key=lambda p: p.stat().st_mtime)
    date_str = latest.stem
    
    return {
        "date": date_str,
        "path": str(latest),
        "exists": True
    }


def build_webapp_payload(report: Dict[str, Any]) -> Dict[str, Any]:
    """Build A2UI payload for morning digest WebApp"""
    
    report_path = report["path"]
    report_date = report["date"]
    
    # Read report content
    try:
        with open(report_path, 'r') as f:
            content = f.read()
    except Exception as e:
        content = f"Error reading report: {e}"
    
    # Truncate content for display (first 2000 chars)
    display_content = content[:2000]
    if len(content) > 2000:
        display_content += "\n\n... (truncated)"
    
    # Build Obsidian URL (using obsidian.md viewer or file link)
    obsidian_url = f"obsidian://open?vault=Bot&file=morning-reports%2F{report_date}.md"
    
    # A2UI Payload
    payload = {
        "type": "beginRendering",
        "rootComponentId": "root",
        "components": [
            {
                "id": "root",
                "type": "Column",
                "properties": {
                    "children": {"explicitList": ["header", "content", "button"]}
                }
            },
            {
                "id": "header",
                "type": "Text",
                "properties": {
                    "text": f"🌅 Morning Report — {report_date}",
                    "variant": "h1"
                }
            },
            {
                "id": "content",
                "type": "Text",
                "properties": {
                    "text": display_content,
                    "variant": "body"
                }
            },
            {
                "id": "button",
                "type": "Button",
                "properties": {
                    "text": "📖 Подробнее в Obsidian",
                    "variant": "secondary",
                    "url": obsidian_url
                }
            }
        ],
        "dataModel": {
            "reportDate": report_date,
            "reportPath": report_path
        }
    }
    
    return payload


def build_telegram_message(report: Dict[str, Any]) -> str:
    """Build short Telegram message (max 5 lines)"""
    
    report_date = report["date"]
    
    # Read crypto data
    crypto_info = ""
    try:
        crypto_file = f"{DATA_DIR}/crypto_radar.json"
        if os.path.exists(crypto_file):
            with open(crypto_file) as f:
                data = json.load(f)
            if data.get("status") == "ok":
                p = data.get("portfolio", {})
                m = data.get("market", {})
                total = p.get("total_equity", "N/A")[:8]
                btc = m.get("btc", {}).get("price", "N/A")[:8]
                btc_chg = m.get("btc", {}).get("change_24h", "0")
                signal = data.get("signal", "-")
                crypto_info = f"💰 {total} USDT | BTC {btc} ({btc_chg}%)\n🎯 {signal}"
    except:
        pass
    
    if not crypto_info:
        crypto_info = "💰 Crypto: No data"
    
    # Check for alerts
    alerts = "✅ All systems OK"
    try:
        jobs_file = "/data/bot/openclaw-docker/cron/jobs.json"
        if os.path.exists(jobs_file):
            with open(jobs_file) as f:
                jobs = json.load(f).get("jobs", [])
            errors = [j for j in jobs if j.get("state", {}).get("consecutiveErrors", 0) > 0]
            if errors:
                alerts = f"⚠️ {len(errors)} cron error(s)"
    except:
        pass
    
    # Build message
    lines = [
        f"🌅 Morning Digest — {report_date}",
        crypto_info,
        alerts,
        "📖 /morning для подробностей"
    ]
    
    return "\n".join(lines)


def send_webapp_button(chat_id: str, report: Dict[str, Any]) -> Dict[str, Any]:
    """Send Telegram message with WebApp button"""
    
    # Build inline keyboard with WebApp
    report_date = report["date"]
    obsidian_url = f"obsidian://open?vault=Bot&file=morning-reports%2F{report_date}.md"
    
    # Encode for web view
    import urllib.parse
    webapp_base = os.environ.get("A2UI_WEBAPP_URL", "https://openclaw.example.com/a2ui")
    webapp_url = f"{webapp_base}?page=morning-digest&date={report_date}"
    
    message_text = build_telegram_message(report)
    
    # Add WebApp button
    buttons = [
        [{"text": "🌅 Утренний дайджест", "web_app": {"url": webapp_url}}]
    ]
    
    return {
        "method": "sendMessage",
        "text": message_text,
        "reply_markup": {"inline_keyboard": buttons}
    }


def main():
    parser = argparse.ArgumentParser(description="Morning Digest Skill")
    parser.add_argument("--webapp", action="store_true", help="Show in A2UI WebApp")
    parser.add_argument("--latest", action="store_true", help="Show latest report")
    parser.add_argument("--date", help="Specific date (YYYY-MM-DD)")
    parser.add_argument("--telegram", action="store_true", help="Send to Telegram")
    parser.add_argument("--chat-id", help="Telegram chat ID")
    args = parser.parse_args()
    
    # Get report
    if args.date:
        report = {
            "date": args.date,
            "path": f"{MORNING_REPORTS_DIR}/{args.date}.md",
            "exists": os.path.exists(f"{MORNING_REPORTS_DIR}/{args.date}.md")
        }
    elif args.latest:
        report = get_latest_report()
    else:
        report = get_today_report()
    
    if not report or not report.get("exists"):
        print(json.dumps({
            "error": "No report found",
            "message": "Run the morning digest cron or generate manually"
        }))
        sys.exit(1)
    
    if args.webapp:
        # Output A2UI payload
        payload = build_webapp_payload(report)
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    elif args.telegram:
        # Send to Telegram
        result = send_webapp_button(args.chat_id or "6053956251", report)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        # Default: show report path
        print(json.dumps({
            "date": report["date"],
            "path": report["path"],
            "webapp": build_webapp_payload(report),
            "telegram": build_telegram_message(report)
        }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
