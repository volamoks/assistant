#!/usr/bin/env python3
"""
Telegram Callback Handler with Pluggable Action Handlers

A reusable module for handling Telegram inline keyboard button presses.
Supports custom action handlers that can be registered dynamically.

Features:
    - Pluggable action handlers (register custom handlers)
    - Polling and webhook modes
    - State persistence (offset tracking)
    - Pre-built handlers for common actions
    - Works with notify.py module

Usage:
    # As CLI (polling mode)
    python3 callback_handler.py

    # With custom handler
    from telegram.callback_handler import CallbackHandler
    
    def my_handler(target, chat_id, msg_id, user):
        return f"Custom: {target}", False
    
    handler = CallbackHandler()
    handler.register("custom", my_handler)
    handler.run_polling()

Callback Data Format:
    "action:target" or "action:target:extra"
    Examples:
        "apply:5" - Apply task #5
        "show:3" - Show details for task #3
        "vikunja:done:12" - Mark Vikunja task #12 as done
        "vikunja:delete:12" - Delete Vikunja task #12

Environment Variables:
    TELEGRAM_BOT_TOKEN: Bot token (required)
    TELEGRAM_POLL_INTERVAL: Polling interval in seconds (default: 2)
    TELEGRAM_STATE_FILE: State file path (default: /tmp/telegram_offset.txt)
"""

import os
import sys
import json
import time
import argparse
import urllib.request
import urllib.error
import http.server
import socketserver
from typing import Optional, Dict, Callable, Tuple, Any, List
from urllib.error import URLError, HTTPError

# Import the unified notifier
try:
    from .notify import TelegramNotifier
except ImportError:
    from notify import TelegramNotifier


# Default configuration
DEFAULT_STATE_FILE = "/tmp/telegram_callback_offset.txt"
DEFAULT_POLL_INTERVAL = 2
DEFAULT_WEBHOOK_PORT = 8080
DEFAULT_WEBHOOK_PATH = "/telegram/callback"


class WebhookHandler(http.server.BaseHTTPRequestHandler):
    """HTTP handler for Telegram webhooks."""

    def do_POST(self):
        """Handle POST request from Telegram."""
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)

        try:
            update = json.loads(post_data.decode('utf-8'))
            # Access the CallbackHandler instance attached to the server
            if hasattr(self.server, 'callback_handler'):
                self.server.callback_handler._process_update(update)
            
            # Respond with 200 OK as required by Telegram
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(b'{"ok": true}')
        except Exception as e:
            print(f"Webhook error: {e}", file=sys.stderr)
            self.send_response(500)
            self.end_headers()

    def log_message(self, format, *args):
        """Mute automatic logging to keep terminal clean."""
        # print("Webhook request:", *args)
        pass


class CallbackHandler:
    """Telegram callback query handler with pluggable actions."""

    def __init__(
        self,
        bot_token: Optional[str] = None,
        state_file: Optional[str] = None,
        poll_interval: int = DEFAULT_POLL_INTERVAL
    ):
        """
        Initialize callback handler.

        Args:
            bot_token: Telegram bot token. Falls back to env.
            state_file: File to store offset state.
            poll_interval: Polling interval in seconds.
        """
        self.bot_token = bot_token or os.environ.get("TELEGRAM_BOT_TOKEN")
        self.state_file = state_file or os.environ.get("TELEGRAM_STATE_FILE", DEFAULT_STATE_FILE)
        self.poll_interval = int(os.environ.get("TELEGRAM_POLL_INTERVAL", poll_interval))

        if not self.bot_token:
            raise ValueError("TELEGRAM_BOT_TOKEN must be set")

        self.notifier = TelegramNotifier(bot_token=self.bot_token)
        self.handlers: Dict[str, Callable] = {}
        self.running = False

        # Register default handlers
        self._register_default_handlers()

    def _register_default_handlers(self):
        """Register built-in action handlers."""

        def handle_apply(target: str, chat_id: int, msg_id: int, user: Dict) -> Tuple[str, bool]:
            """Handle 'apply' action - user wants to apply/implement something."""
            return f"🔄 Применяю: {target}", False

        def handle_show(target: str, chat_id: int, msg_id: int, user: Dict) -> Tuple[str, bool]:
            """Handle 'show' action - user wants to see details."""
            return f"📋 Загружаю детали: {target}", False

        def handle_skip(target: str, chat_id: int, msg_id: int, user: Dict) -> Tuple[str, bool]:
            """Handle 'skip' action - user wants to skip."""
            return f"⏭️ Пропускаю: {target}", False

        def handle_vikunja(target: str, chat_id: int, msg_id: int, user: Dict) -> Tuple[str, bool]:
            """Handle 'vikunja' actions - task management."""
            parts = target.split(":", 1)
            if len(parts) < 2:
                return f"⚠️ Неверный формат: {target}", True

            action, task_id = parts
            if action == "done":
                # Mark task as done via Vikunja CLI
                result = self._vikunja_done(task_id)
                if result:
                    # Update message to show completion
                    self.notifier.edit_reply_markup(chat_id, msg_id, None)
                    return f"✅ Задача #{task_id} выполнена!", False
                return f"⚠️ Ошибка обновления задачи #{task_id}", True
            elif action == "delete":
                result = self._vikunja_delete(task_id)
                if result:
                    self.notifier.delete(chat_id, msg_id)
                    return f"🗑️ Задача #{task_id} удалена", False
                return f"⚠️ Ошибка удаления задачи #{task_id}", True
            else:
                return f"⚠️ Неизвестное действие Vikunja: {action}", True

        self.register("apply", handle_apply)
        self.register("show", handle_show)
        self.register("skip", handle_skip)
        self.register("vikunja", handle_vikunja)

    def _vikunja_done(self, task_id: str) -> bool:
        """Mark Vikunja task as done."""
        vikunja_url = os.environ.get("VIKUNJA_URL", "http://localhost:3456/api/v1")
        vikunja_token = os.environ.get("VIKUNJA_TOKEN")
        if not vikunja_token:
            return False

        # Update task status to done
        url = f"{vikunja_url}/tasks/{task_id}"
        data = json.dumps({"done": True}).encode('utf-8')
        req = urllib.request.Request(
            url,
            data=data,
            headers={
                "Authorization": f"Bearer {vikunja_token}",
                "Content-Type": "application/json"
            },
            method="PUT"
        )
        try:
            with urllib.request.urlopen(req) as response:
                return response.status == 200
        except Exception:
            return False

    def _vikunja_delete(self, task_id: str) -> bool:
        """Delete Vikunja task."""
        vikunja_url = os.environ.get("VIKUNJA_URL", "http://localhost:3456/api/v1")
        vikunja_token = os.environ.get("VIKUNJA_TOKEN")
        if not vikunja_token:
            return False

        url = f"{vikunja_url}/tasks/{task_id}"
        req = urllib.request.Request(
            url,
            headers={
                "Authorization": f"Bearer {vikunja_token}"
            },
            method="DELETE"
        )
        try:
            with urllib.request.urlopen(req) as response:
                return response.status == 200
        except Exception:
            return False

    def register(self, action: str, handler: Callable[[str, int, int, Dict], Tuple[str, bool]]):
        """
        Register a custom action handler.

        Args:
            action: Action name (e.g., "apply", "vikunja").
            handler: Function that takes (target, chat_id, msg_id, user)
                     and returns (response_text, show_alert).
        """
        self.handlers[action] = handler
        print(f"Registered handler: {action}")

    def unregister(self, action: str):
        """Unregister an action handler."""
        if action in self.handlers:
            del self.handlers[action]

    def _load_offset(self) -> Optional[int]:
        """Load last update offset from file."""
        try:
            if os.path.exists(self.state_file):
                with open(self.state_file, "r") as f:
                    return int(f.read().strip())
        except (ValueError, IOError):
            pass
        return None

    def _save_offset(self, offset: int):
        """Save last update offset to file."""
        with open(self.state_file, "w") as f:
            f.write(str(offset))

    def _get_updates(self, offset: Optional[int] = None, timeout: int = 30) -> Optional[Dict]:
        """Get updates from Telegram."""
        payload = {"timeout": timeout}
        if offset:
            payload["offset"] = offset
        return self.notifier._request("getUpdates", payload)

    def _handle_callback(
        self,
        callback_data: str,
        callback_query_id: str,
        chat_id: int,
        msg_id: int,
        user: Dict
    ):
        """Process a callback query."""
        # Parse callback data: "action:target" or "action:target:extra"
        parts = callback_data.split(":", 1)
        if len(parts) < 2:
            self.notifier.answer_callback(
                callback_query_id,
                text=f"⚠️ Неизвестный формат: {callback_data}",
                show_alert=True
            )
            return
        
        action, target = parts[0], parts[1]

        # Find handler
        handler = self.handlers.get(action)
        if not handler:
            self.notifier.answer_callback(
                callback_query_id,
                text=f"⚠️ Неизвестное действие: {action}",
                show_alert=True
            )
            return

        # Call handler
        try:
            response_text, show_alert = handler(target, chat_id, msg_id, user)
            self.notifier.answer_callback(
                callback_query_id,
                text=response_text,
                show_alert=show_alert
            )
        except Exception as e:
            print(f"Handler error for {action}: {e}", file=sys.stderr)
            self.notifier.answer_callback(
                callback_query_id,
                text=f"⚠️ Ошибка: {str(e)}",
                show_alert=True
            )

    def _process_update(self, update: Dict) -> bool:
        """Process a single update. Returns True if callback was handled."""
        if "callback_query" in update:
            cb_query = update["callback_query"]
            callback_query_id = cb_query.get("id")
            callback_data = cb_query.get("data", "")
            chat_id = cb_query.get("message", {}).get("chat", {}).get("id")
            msg_id = cb_query.get("message", {}).get("message_id")
            from_user = cb_query.get("from", {})

            print(f"Callback from @{from_user.get('username', 'unknown')}: {callback_data}")

            if chat_id and msg_id:
                self._handle_callback(
                    callback_data,
                    callback_query_id,
                    chat_id,
                    msg_id,
                    from_user
                )
            return True

        return False

    def set_webhook(self, url: str) -> bool:
        """
        Set Telegram webhook URL.
        
        Args:
            url: Publicly accessible URL for the webhook.
                 Pass an empty string to remove the webhook.
        """
        if url:
            print(f"Setting webhook to: {url}")
            payload = {"url": url}
            result = self.notifier._request("setWebhook", payload)
        else:
            print("Removing webhook...")
            result = self.notifier._request("deleteWebhook", {"drop_pending_updates": True})
        
        if result and result.get("ok"):
            print("Successfully updated webhook status")
            return True
        else:
            print(f"Failed to update webhook: {result}", file=sys.stderr)
            return False

    def run_webhook(self, port: int = DEFAULT_WEBHOOK_PORT):
        """Run the callback handler in webhook mode."""
        print(f"Starting Telegram callback handler (webhook mode) on port {port}...")
        
        socketserver.TCPServer.allow_reuse_address = True
        with socketserver.TCPServer(("", port), WebhookHandler) as httpd:
            # Attach this instance to the server so the handler can access it
            httpd.callback_handler = self
            try:
                self.running = True
                httpd.serve_forever()
            except KeyboardInterrupt:
                print("\nShutting down...")
                self.running = False

    def run_polling(self):
        """Run the callback handler in polling mode."""
        print("Starting Telegram callback handler (polling mode)...")
        print(f"Poll interval: {self.poll_interval}s")
        print(f"State file: {self.state_file}")

        offset = self._load_offset()
        if offset:
            print(f"Resuming from offset: {offset}")

        self.running = True
        try:
            while self.running:
                updates_resp = self._get_updates(
                    offset=offset + 1 if offset else None,
                    timeout=30
                )

                if updates_resp and updates_resp.get("ok"):
                    updates = updates_resp.get("result", [])
                    for update in updates:
                        self._process_update(update)
                        offset = update.get("update_id")
                        self._save_offset(offset)
                
                time.sleep(self.poll_interval)

        except KeyboardInterrupt:
            print("\nShutting down...")
            self.running = False
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

    def stop(self):
        """Stop the polling loop."""
        self.running = False


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Telegram Callback Handler with Pluggable Actions",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Run in polling mode (default)
    python3 callback_handler.py

    # Run in webhook mode
    python3 callback_handler.py --webhook --port 8080

    # Set webhook URL
    python3 callback_handler.py --set-webhook https://your-domain.com/telegram/callback
    
    # Delete webhook (switch back to polling)
    python3 callback_handler.py --set-webhook ""
        """
    )
    parser.add_argument(
        "--interval", "-i",
        type=int,
        default=DEFAULT_POLL_INTERVAL,
        help="Polling interval in seconds"
    )
    parser.add_argument(
        "--state-file",
        type=str,
        help="State file path for offset persistence"
    )
    parser.add_argument(
        "--webhook",
        action="store_true",
        help="Run in webhook mode instead of polling"
    )
    parser.add_argument(
        "--port", "-p",
        type=int,
        default=DEFAULT_WEBHOOK_PORT,
        help=f"Port for webhook server (default: {DEFAULT_WEBHOOK_PORT})"
    )
    parser.add_argument(
        "--set-webhook",
        type=str,
        metavar="URL",
        help="Set Telegram webhook URL and exit"
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="Test mode - just print configuration and exit"
    )

    args = parser.parse_args()

    try:
        handler = CallbackHandler(
            poll_interval=args.interval,
            state_file=args.state_file
        )
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    if args.set_webhook is not None:
        handler.set_webhook(args.set_webhook)
        return

    if args.test:
        print("Configuration OK")
        print(f"Mode: {'Webhook' if args.webhook else 'Polling'}")
        if args.webhook:
            print(f"Port: {args.port}")
        else:
            print(f"Poll interval: {handler.poll_interval}s")
            print(f"State file: {handler.state_file}")
        print(f"Registered handlers: {list(handler.handlers.keys())}")
        return

    if args.webhook:
        handler.run_webhook(port=args.port)
    else:
        handler.run_polling()


if __name__ == "__main__":
    main()
