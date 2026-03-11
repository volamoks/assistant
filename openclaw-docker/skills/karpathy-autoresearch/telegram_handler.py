#!/usr/bin/env python3
"""
karpathy-autoresearch/telegram_handler.py — Telegram Handler

Handles Telegram commands for the Karpathy Autoresearch system.
Supports:
- /autoresearch - Run full autoresearch cycle manually
- /autostatus - Show current status
- /autographs - Send progress charts

Part of the Karpathy Autoresearch self-improvement cycle (P2).
"""

import argparse
import json
import os
import subprocess
import sys
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests
import yaml

# Add parent to path for imports
SKILL_DIR = Path(__file__).parent
sys.path.insert(0, str(SKILL_DIR))

from progress_charts import generate_all_charts, load_metrics_history

# ── Config ────────────────────────────────────────────────────────────────────

CONFIG_PATH = Path("~/.openclaw/skills/karpathy-autoresearch/config.yaml").expanduser()
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

# ── Global State ─────────────────────────────────────────────────────────────

# Track running autoresearch processes
running_processes: Dict[str, Dict[str, Any]] = {}


# ── Core Functions ───────────────────────────────────────────────────────────

def load_config() -> Dict[str, Any]:
    """Load configuration from YAML file."""
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH) as f:
            return yaml.safe_load(f)
    return {}


def send_telegram_message(
    message: str,
    chat_id: str,
    token: str,
    parse_mode: str = "Markdown"
) -> bool:
    """Send message to Telegram."""
    if not token or not chat_id:
        print("❌ Telegram credentials not configured")
        return False
    
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": parse_mode,
        "disable_web_page_preview": True
    }
    
    try:
        resp = requests.post(url, json=payload, timeout=30)
        return resp.status_code == 200
    except Exception as e:
        print(f"❌ Failed to send Telegram message: {e}")
        return False


def send_telegram_photo(
    photo_path: str,
    chat_id: str,
    token: str,
    caption: str = ""
) -> bool:
    """Send photo to Telegram."""
    if not token or not chat_id:
        print("❌ Telegram credentials not configured")
        return False
    
    url = f"https://api.telegram.org/bot{token}/sendPhoto"
    
    try:
        with open(photo_path, 'rb') as photo:
            files = {'photo': photo}
            data = {
                'chat_id': chat_id,
                'caption': caption
            }
            resp = requests.post(url, files=files, data=data, timeout=60)
            return resp.status_code == 200
    except Exception as e:
        print(f"❌ Failed to send Telegram photo: {e}")
        return False


def edit_telegram_message(
    message: str,
    chat_id: str,
    token: str,
    message_id: int,
    parse_mode: str = "Markdown"
) -> bool:
    """Edit existing Telegram message."""
    if not token or not chat_id:
        return False
    
    url = f"https://api.telegram.org/bot{token}/editMessageText"
    
    payload = {
        "chat_id": chat_id,
        "message_id": message_id,
        "text": message,
        "parse_mode": parse_mode
    }
    
    try:
        resp = requests.post(url, json=payload, timeout=30)
        return resp.status_code == 200
    except Exception:
        return False


def run_autoresearch_cycle(
    chat_id: str,
    token: str,
    dry_run: bool = False
) -> Tuple[str, int]:
    """
    Run the full autoresearch cycle in a background thread.
    Returns (final_message, status_message_id)
    """
    
    process_id = f"autoresearch_{int(time.time())}"
    
    # Send initial status
    initial_message = "🔄 *Запуск Autoresearch Cycle*\n\n⏳ Инициализация..."
    status_msg_id = None
    
    # Send initial message
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        resp = requests.post(url, json={
            "chat_id": chat_id,
            "text": initial_message,
            "parse_mode": "Markdown"
        }, timeout=30)
        if resp.status_code == 200:
            status_msg_id = resp.json().get("result", {}).get("message_id")
    except Exception:
        pass
    
    running_processes[process_id] = {
        "status": "running",
        "started_at": datetime.now().isoformat(),
        "chat_id": chat_id,
        "status_message_id": status_msg_id,
        "dry_run": dry_run
    }
    
    def update_status(message: str):
        """Update status message."""
        if status_msg_id:
            edit_telegram_message(message, chat_id, token, status_msg_id)
    
    def run_cycle():
        """Background task to run the cycle."""
        # Pass environment variables to subprocess
        env = os.environ.copy()
        
        try:
            # Step 1: Analysis
            update_status("🔄 *Autoresearch Cycle*\n\n📊 Шаг 1/6: Анализ логов...")
            
            result = subprocess.run(
                [sys.executable, str(SKILL_DIR / "analyzer.py"), 
                 "--days", "7", "--output", "/tmp/karpathy_patterns.json"],
                capture_output=True,
                text=True,
                timeout=300,
                env=env
            )
            
            if result.returncode != 0:
                update_status("❌ *Autoresearch Cycle*\n\nОшибка на этапе анализа логов")
                running_processes[process_id]["status"] = "failed"
                return
            
            # Step 2: Hypothesis
            update_status("🔄 *Autoresearch Cycle*\n\n🧠 Шаг 2/6: Генерация гипотез...")
            
            result = subprocess.run(
                [sys.executable, str(SKILL_DIR / "hypothesis.py"),
                 "--patterns-file", "/tmp/karpathy_patterns.json",
                 "--output", "/tmp/karpathy_hypotheses.json"],
                capture_output=True,
                text=True,
                timeout=300,
                env=env
            )
            
            if result.returncode != 0:
                update_status("❌ *Autoresearch Cycle*\n\nОшибка на этапе генерации гипотез")
                running_processes[process_id]["status"] = "failed"
                return
            
            # Step 3: Testing
            update_status("🔄 *Autoresearch Cycle*\n\n🧪 Шаг 3/6: A/B тестирование...")
            
            result = subprocess.run(
                [sys.executable, str(SKILL_DIR / "test_harness.py"),
                 "--hypotheses-file", "/tmp/karpathy_hypotheses.json",
                 "--output", "/tmp/karpathy_test_results.json"],
                capture_output=True,
                text=True,
                timeout=600,
                env=env
            )
            
            if result.returncode != 0:
                update_status("❌ *Autoresearch Cycle*\n\nОшибка на этапе тестирования")
                running_processes[process_id]["status"] = "failed"
                return
            
            # Step 4: Prompt Patch (if not dry run)
            if not dry_run:
                update_status("🔄 *Autoresearch Cycle*\n\n📝 Шаг 4/6: Применение патчей...")
                
                result = subprocess.run(
                    [sys.executable, str(SKILL_DIR / "prompt_patch.py"),
                     "--test-results", "/tmp/karpathy_test_results.json"],
                    capture_output=True,
                    text=True,
                    timeout=300,
                    env=env
                )
            
            # Step 5: Feedback Loop
            update_status("🔄 *Autoresearch Cycle*\n\n🔄 Шаг 5/6: Анализ эффективности...")
            
            # Load test results for summary
            test_results = {}
            try:
                with open("/tmp/karpathy_test_results.json") as f:
                    test_results = json.load(f)
            except:
                pass
            
            results = test_results.get("results", [])
            passed = sum(1 for r in results if r.get("passed", False))
            total = len(results)
            
            # Step 6: Report
            update_status("🔄 *Autoresearch Cycle*\n\n📤 Шаг 6/6: Отправка отчета...")
            
            # Generate charts
            charts = generate_all_charts()
            
            # Send final summary
            final_message = f"""✅ *Autoresearch Cycle Завершён!*

📊 *Результаты:*
  • Гипотез проверено: `{total}`
  • Успешных улучшений: `{passed}`
  • Процент успеха: `{passed/total*100:.0f}%` если total > 0 else `0%`

⏱️ Время выполнения: ~{datetime.now() - datetime.fromisoformat(running_processes[process_id]['started_at']):.0f} минут

{"🔒 Режим: Dry Run (изменения не применены)" if dry_run else "✅ Изменения применены"}"""
            
            # Send final message
            send_telegram_message(final_message, chat_id, token)
            
            # Send charts
            for chart_name, chart_path in charts.items():
                if chart_path and Path(chart_path).exists():
                    caption = f"📈 График: {chart_name.replace('_', ' ').title()}"
                    send_telegram_photo(chart_path, chat_id, token, caption)
            
            # Update status
            running_processes[process_id]["status"] = "completed"
            running_processes[process_id]["completed_at"] = datetime.now().isoformat()
            
        except Exception as e:
            update_status(f"❌ *Autoresearch Cycle*\n\nКритическая ошибка: {str(e)[:100]}")
            running_processes[process_id]["status"] = "failed"
            running_processes[process_id]["error"] = str(e)
    
    # Start background thread
    thread = threading.Thread(target=run_cycle, daemon=True)
    thread.start()
    
    # Return initial status message
    return "🔄 Autoresearch запущен! Следите за обновлениями...", status_msg_id


def get_autoresearch_status() -> str:
    """Get current autoresearch status."""
    
    # Check for running processes
    running = [p for p in running_processes.values() if p.get("status") == "running"]
    
    if running:
        proc = running[0]
        started = proc.get("started_at", "")
        try:
            duration = datetime.now() - datetime.fromisoformat(started)
            return f"🔄 *Autoresearch Status*\n\n⏳ Цикл выполняется...\n\nНачат: {started[:16]}\nДлительность: {duration.seconds // 60} мин"
        except:
            return "🔄 *Autoresearch Status*\n\n⏳ Цикл выполняется..."
    
    # Load last results
    output_dir = SKILL_DIR / "output"
    if output_dir.exists():
        cycles = sorted(output_dir.glob("cycle_*.json"), reverse=True)
        if cycles:
            try:
                with open(cycles[0]) as f:
                    last = json.load(f)
                
                status_icon = "✅" if last.get("success") else "⚠️"
                completed = last.get("completed_at", "Unknown")[:16]
                
                steps = last.get("steps", {})
                step_summary = []
                for step_name, step_result in steps.items():
                    icon = "✅" if step_result.get("status") == "success" else "❌"
                    step_summary.append(f"{icon} {step_name}")
                
                return f"""📊 *Последний цикл:* {status_icon}

Завершён: {completed}

Шаги:
{chr(10).join(f"  {s}" for s in step_summary)}"""
            except:
                pass
    
    return """📊 *Autoresearch Status*

ℹ️ Нет активных циклов

Команды:
/autoresearch - Запустить цикл
/autographs - Показать графики
/autostatus - Этот статус"""


def handle_autoresearch_command(chat_id: str, token: str, args: str = "") -> str:
    """Handle /autoresearch command."""
    
    # Check for dry-run flag
    dry_run = "--dry-run" in args or "-d" in args
    
    # Check if already running
    running = [p for p in running_processes.values() if p.get("status") == "running"]
    if running:
        return "⚠️ Autoresearch уже выполняется! Дождитесь завершения."
    
    # Start the cycle
    return run_autoresearch_cycle(chat_id, token, dry_run)[0]


def handle_autographs_command(chat_id: str, token: str) -> str:
    """Handle /autographs command - send progress charts."""
    
    charts = generate_all_charts()
    
    if not charts:
        return "📊 Нет данных для графиков. Запустите /autoresearch сначала."
    
    # Send each chart
    for chart_name, chart_path in charts.items():
        if chart_path and Path(chart_path).exists():
            caption = f"📈 {chart_name.replace('_', ' ').title()}"
            send_telegram_photo(chart_path, chat_id, token, caption)
    
    return f"📊 Отправлено {len(charts)} графиков прогресса"


def handle_autostatus_command(chat_id: str, token: str) -> str:
    """Handle /autostatus command."""
    return get_autoresearch_status()


def process_telegram_update(update: Dict[str, Any]) -> Optional[str]:
    """Process a Telegram update and return response."""
    
    config = load_config()
    reporting_config = config.get("reporting", {})
    
    # Get credentials
    token = TELEGRAM_BOT_TOKEN or reporting_config.get("token", "")
    chat_id = TELEGRAM_CHAT_ID or reporting_config.get("chat_id", "")
    
    if not token or not chat_id:
        return "❌ Telegram credentials not configured"
    
    # Check for commands
    if "message" in update:
        message = update["message"]
        text = message.get("text", "")
        chat_id = str(message.get("chat", {}).get("id", chat_id))
        
        # Handle commands
        if text.startswith("/autoresearch"):
            args = text.replace("/autoresearch", "").strip()
            return handle_autoresearch_command(chat_id, token, args)
        
        elif text.startswith("/autographs"):
            return handle_autographs_command(chat_id, token)
        
        elif text.startswith("/autostatus"):
            return handle_autostatus_command(chat_id, token)
        
        elif text.startswith("/autohelp"):
            return """🤖 *Autoresearch Commands*

/autoresearch - Запустить полный цикл
/autoresearch --dry-run - Запуск без применения изменений
/autographs - Показать графики прогресса
/autostatus - Показать текущий статус
/autohelp - Показать эту справку"""
    
    return None


# ── Polling Loop ─────────────────────────────────────────────────────────────

def polling_loop(token: str, offset_file: str = "/tmp/autoresearch_offset.txt"):
    """Poll Telegram for commands."""
    
    offset = 0
    offset_path = Path(offset_file)
    
    # Load last offset
    if offset_path.exists():
        try:
            offset = int(offset_path.read_text().strip())
        except:
            pass
    
    print(f"🔄 Autoresearch Telegram Handler started")
    print(f"   Polling for commands...")
    
    while True:
        try:
            # Get updates
            url = f"https://api.telegram.org/bot{token}/getUpdates"
            params = {"offset": offset, "timeout": 30}
            
            resp = requests.get(url, params=params, timeout=35)
            if resp.status_code != 200:
                time.sleep(5)
                continue
            
            data = resp.json()
            if not data.get("ok"):
                time.sleep(5)
                continue
            
            updates = data.get("result", [])
            
            for update in updates:
                offset = update.get("update_id", offset) + 1
                
                # Process update
                response = process_telegram_update(update)
                if response:
                    # Get chat_id from update
                    chat_id = None
                    if "message" in update:
                        chat_id = str(update["message"].get("chat", {}).get("id"))
                    
                    if chat_id:
                        send_telegram_message(response, chat_id, token)
            
            # Save offset
            if offset > 0:
                offset_path.write_text(str(offset))
        
        except Exception as e:
            print(f"⚠️ Polling error: {e}")
            time.sleep(5)


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Telegram Handler for Karpathy Autoresearch",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run as bot (polling for commands)
  python3 telegram_handler.py --poll
  
  # Process a single update (for webhooks)
  python3 telegram_handler.py --process-update '{"message": {"text": "/autoresearch", "chat": {"id": "123"}}}'
  
  # Send status manually
  python3 telegram_handler.py --status
  
  # Send charts
  python3 telegram_handler.py --charts
        """
    )
    parser.add_argument("--poll", action="store_true", help="Run polling loop for commands")
    parser.add_argument("--process-update", type=str, help="Process a single update (JSON)")
    parser.add_argument("--status", action="store_true", help="Send status message")
    parser.add_argument("--charts", action="store_true", help="Send progress charts")
    parser.add_argument("--token", default=TELEGRAM_BOT_TOKEN, help="Telegram bot token")
    parser.add_argument("--chat-id", default=TELEGRAM_CHAT_ID, help="Telegram chat ID")
    parser.add_argument("--offset-file", default="/tmp/autoresearch_offset.txt")
    args = parser.parse_args()
    
    # Load config
    config = load_config()
    reporting_config = config.get("reporting", {})
    
    # Determine credentials
    token = args.token or reporting_config.get("token", TELEGRAM_BOT_TOKEN)
    chat_id = args.chat_id or reporting_config.get("chat_id", TELEGRAM_CHAT_ID)
    
    if not token:
        print("❌ TELEGRAM_BOT_TOKEN not set")
        sys.exit(1)
    
    if not chat_id:
        print("❌ TELEGRAM_CHAT_ID not set")
        sys.exit(1)
    
    # Process single update
    if args.process_update:
        update = json.loads(args.process_update)
        response = process_telegram_update(update)
        if response:
            print(response)
        return
    
    # Send status
    if args.status:
        message = get_autoresearch_status()
        if send_telegram_message(message, chat_id, token):
            print("✅ Status sent")
        else:
            print("❌ Failed to send status")
        return
    
    # Send charts
    if args.charts:
        response = handle_autographs_command(chat_id, token)
        print(response)
        return
    
    # Polling mode
    if args.poll:
        polling_loop(token, args.offset_file)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
