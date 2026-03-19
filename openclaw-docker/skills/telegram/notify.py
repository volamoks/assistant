#!/usr/bin/env python3
"""
Unified Telegram Notification Module

A reusable, isolated module for sending Telegram notifications with inline keyboard buttons.
Can be used by any tool, agent, or script in the OpenClaw ecosystem.

Features:
    - Send text messages with Markdown formatting
    - Inline keyboard buttons with callback data
    - Edit existing messages
    - Delete messages
    - Thread support (message_thread_id for topics)
    - Environment-based configuration

Usage:
    # Basic notification
    python3 notify.py "Hello, World!"

    # With buttons
    python3 notify.py "Task #5: Fix bug" \
        --buttons "✅ Apply:apply:5,📋 Show:show:5,⏭️ Skip:skip:5"

    # To specific chat
    python3 notify.py "Alert!" --chat-id "-1001234567890"

    # In a topic/thread
    python3 notify.py "Update" --thread-id "123"

    # Edit existing message
    python3 notify.py "Updated text" --edit-chat "-1001234567890" --edit-msg "456"

    # As Python module
    from telegram.notify import TelegramNotifier
    notifier = TelegramNotifier()
    notifier.send("Hello!", buttons=[("Apply", "apply:1"), ("Skip", "skip:1")])

Environment Variables:
    TELEGRAM_BOT_TOKEN: Bot token (required)
    TELEGRAM_CHAT_ID: Default chat ID (optional)
    TELEGRAM_THREAD_ID: Default thread/topic ID (optional)
"""

import os
import sys
import json
import argparse
import urllib.request
import urllib.error
from typing import Optional, List, Tuple, Dict, Any
from urllib.error import URLError, HTTPError


class TelegramNotifier:
    """Unified Telegram notification client."""

    def __init__(
        self,
        bot_token: Optional[str] = None,
        chat_id: Optional[str] = None,
        thread_id: Optional[int] = None,
        parse_mode: str = "Markdown"
    ):
        """
        Initialize Telegram notifier.

        Args:
            bot_token: Telegram bot token. Falls back to TELEGRAM_BOT_TOKEN env.
            chat_id: Default chat ID (comma-separated for multiple). Falls back to TELEGRAM_CHAT_ID env.
            thread_id: Default thread/topic ID. Falls back to TELEGRAM_THREAD_ID env.
            parse_mode: Message parse mode (Markdown, HTML, or None).
        """
        self.bot_token = bot_token or os.environ.get("TELEGRAM_BOT_TOKEN")
        self.chat_id = chat_id or os.environ.get("TELEGRAM_CHAT_ID")
        self.thread_id = thread_id or int(os.environ.get("TELEGRAM_THREAD_ID") or 0)
        self.parse_mode = parse_mode

        if not self.bot_token:
            raise ValueError("TELEGRAM_BOT_TOKEN must be set")

        self.api_base = f"https://api.telegram.org/bot{self.bot_token}"
        
        # Parse comma-separated chat IDs for broadcasting
        self.chat_ids = []
        if self.chat_id:
            self.chat_ids = [cid.strip() for cid in self.chat_id.split(",") if cid.strip()]

    def _request(self, method: str, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Send request to Telegram API."""
        url = f"{self.api_base}/{method}"
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"}
        )
        try:
            with urllib.request.urlopen(req) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as e:
            print(f"HTTPError: {e.code} - {e.reason}", file=sys.stderr)
            return None
        except URLError as e:
            print(f"URLError: {e.reason}", file=sys.stderr)
            return None

    def _parse_buttons(self, buttons_str: str) -> List[List[Dict[str, str]]]:
        """
        Parse button string into inline keyboard format.

        Format: "Btn1:cb1,Btn2:cb2|Row2Btn1:cb3,Row2Btn2:cb4"
        - Comma separates buttons within a row
        - Pipe (|) separates rows

        Returns:
            Inline keyboard markup structure for Telegram API.
        """
        if not buttons_str:
            return []

        rows = buttons_str.split("|")
        keyboard = []

        for row in rows:
            row_buttons = []
            for btn in row.split(","):
                btn = btn.strip()
                if not btn:
                    continue
                # Format: "Text:callback_data" or "Text:callback_data:extra"
                parts = btn.split(":", 2)
                if len(parts) >= 2:
                    text = parts[0]
                    callback_data = parts[1]
                    # Telegram callback_data max length is 64 bytes
                    if len(callback_data.encode('utf-8')) > 64:
                        callback_data = callback_data.encode('utf-8')[:64].decode('utf-8', 'ignore')
                    row_buttons.append({
                        "text": text,
                        "callback_data": callback_data
                    })
            if row_buttons:
                keyboard.append(row_buttons)

        return keyboard

    def send(
        self,
        text: str,
        buttons: Optional[str] = None,
        chat_id: Optional[str] = None,
        thread_id: Optional[int] = None,
        silent: bool = False,
        broadcast: bool = False,
        webapp_url: Optional[str] = None,
        webapp_text: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Send a text message with optional inline keyboard or WebApp button.

        Args:
            text: Message text (Markdown supported).
            buttons: Button string in format "Btn1:cb1,Btn2:cb2|Row2:cb3".
            chat_id: Override default chat ID.
            thread_id: Override default thread/topic ID.
            silent: Send without notification (silent).
            broadcast: If True, send to all chat IDs in comma-separated list.
            webapp_url: URL for a WebApp button.
            webapp_text: Text for the WebApp button.
            **kwargs: Additional arguments for sendMessage API.

        Returns:
            Dict with 'ok' status and 'results' list of API responses for each chat.
        """
        # Determine target chat(s)
        if chat_id:
            target_chats = [cid.strip() for cid in chat_id.split(",") if cid.strip()]
        elif broadcast and self.chat_ids:
            target_chats = self.chat_ids
        elif self.chat_id:
            target_chats = [self.chat_id]
        else:
            raise ValueError("chat_id must be provided")

        if not target_chats:
            raise ValueError("No valid chat IDs to send to")

        # Build base payload
        payload_base = {
            "text": text,
            "parse_mode": self.parse_mode,
            "disable_web_page_preview": True,
            **kwargs
        }

        # Add thread/topic ID
        tid = thread_id or self.thread_id
        if tid:
            payload_base["message_thread_id"] = tid

        # Silent mode
        if silent:
            payload_base["disable_notification"] = True

        # Add inline keyboard if buttons provided
        if buttons:
            keyboard = self._parse_buttons(buttons)
            if keyboard:
                payload_base["reply_markup"] = {"inline_keyboard": keyboard}
        # Add WebApp button if URL provided (takes precedence over buttons)
        elif webapp_url:
            btn_text = webapp_text or "Open"
            payload_base["reply_markup"] = {
                "inline_keyboard": [[{"text": btn_text, "web_app": {"url": webapp_url}}]]
            }

        # Send to each chat
        results = []
        all_ok = True
        
        for target_chat in target_chats:
            payload = {**payload_base, "chat_id": target_chat}
            result = self._request("sendMessage", payload)
            results.append({
                "chat_id": target_chat,
                "ok": result.get("ok", False) if result else False,
                "result": result.get("result") if result else None,
                "error": None if result and result.get("ok") else str(result)
            })
            if not (result and result.get("ok")):
                all_ok = False

        return {"ok": all_ok, "results": results}

    def edit(
        self,
        chat_id: str,
        message_id: int,
        text: Optional[str] = None,
        buttons: Optional[str] = None,
        **kwargs
    ) -> Optional[Dict[str, Any]]:
        """
        Edit an existing message.

        Args:
            chat_id: Chat ID where message exists.
            message_id: Message ID to edit.
            text: New text (optional if only updating buttons).
            buttons: New button string (optional if only updating text).
            **kwargs: Additional arguments for editMessageText API.

        Returns:
            API response dict, or None on failure.
        """
        payload = {
            "chat_id": chat_id,
            "message_id": message_id,
            "parse_mode": self.parse_mode,
            **kwargs
        }

        if text:
            payload["text"] = text

        if buttons:
            keyboard = self._parse_buttons(buttons)
            if keyboard:
                payload["reply_markup"] = {"inline_keyboard": keyboard}
        else:
            # Remove keyboard if no buttons specified
            payload["reply_markup"] = {}

        return self._request("editMessageText", payload)

    def edit_reply_markup(
        self,
        chat_id: str,
        message_id: int,
        buttons: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Edit only the reply markup (buttons) of a message.

        Args:
            chat_id: Chat ID where message exists.
            message_id: Message ID to edit.
            buttons: New button string, or None to remove keyboard.

        Returns:
            API response dict, or None on failure.
        """
        payload = {
            "chat_id": chat_id,
            "message_id": message_id
        }

        if buttons:
            keyboard = self._parse_buttons(buttons)
            payload["reply_markup"] = {"inline_keyboard": keyboard}
        else:
            payload["reply_markup"] = {}

        return self._request("editMessageReplyMarkup", payload)

    def delete(
        self,
        chat_id: str,
        message_id: int
    ) -> Optional[Dict[str, Any]]:
        """
        Delete a message.

        Args:
            chat_id: Chat ID where message exists.
            message_id: Message ID to delete.

        Returns:
            API response dict, or None on failure.
        """
        return self._request("deleteMessage", {
            "chat_id": chat_id,
            "message_id": message_id
        })

    def answer_callback(
        self,
        callback_query_id: str,
        text: Optional[str] = None,
        show_alert: bool = False,
        url: Optional[str] = None,
        cache_time: int = 0
    ) -> Optional[Dict[str, Any]]:
        """
        Answer a callback query (button press).

        Args:
            callback_query_id: ID from callback_query update.
            text: Text to show in notification/alert.
            show_alert: If True, show as alert popup; else as toast notification.
            url: URL to open (optional).
            cache_time: Cache time for callback response.

        Returns:
            API response dict, or None on failure.
        """
        payload = {
            "callback_query_id": callback_query_id,
            "show_alert": show_alert,
            "cache_time": cache_time
        }
        if text:
            payload["text"] = text
        if url:
            payload["url"] = url

        return self._request("answerCallbackQuery", payload)


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Unified Telegram Notification Module",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Basic message
    python3 notify.py "Hello, World!"

    # With inline keyboard buttons
    python3 notify.py "Task #5" --buttons "✅ Apply:apply:5,⏭️ Skip:skip:5"

    # Send to specific chat
    python3 notify.py "Alert" --chat-id "-1001234567890"

    # Send in a topic/thread
    python3 notify.py "Update" --thread-id "123"

    # Edit existing message
    python3 notify.py "Updated" --edit-chat "-1001234567890" --edit-msg "456"

    # Delete message
    python3 notify.py "" --delete-chat "-1001234567890" --delete-msg "789"

Button Format:
    "Btn1:callback1,Btn2:callback2|Row2Btn1:cb3,Row2Btn2:cb4"
    - Comma separates buttons in a row
    - Pipe (|) separates rows
    - Callback data max 64 bytes
        """
    )

    parser.add_argument("text", nargs="?", default="", help="Message text")
    parser.add_argument("--buttons", "-b", help="Inline keyboard buttons (format: 'Btn1:cb1,Btn2:cb2|Row2:cb3')")
    parser.add_argument("--webapp-url", help="WebApp URL for a single button (format: 'URL')")
    parser.add_argument("--webapp-text", default="Open", help="Text for WebApp button")
    parser.add_argument("--chat-id", "-c", help="Chat ID (overrides env)")
    parser.add_argument("--thread-id", "-t", type=int, help="Thread/Topic ID (overrides env)")
    parser.add_argument("--silent", "-s", action="store_true", help="Send silently")
    parser.add_argument("--parse-mode", default="Markdown", choices=["Markdown", "HTML", "None"], help="Parse mode")
    parser.add_argument("--edit-chat", type=str, help="Chat ID for editing")
    parser.add_argument("--edit-msg", type=int, help="Message ID to edit")
    parser.add_argument("--delete-chat", type=str, help="Chat ID for deletion")
    parser.add_argument("--delete-msg", type=int, help="Message ID to delete")
    parser.add_argument("--callback-id", help="Callback query ID to answer")
    parser.add_argument("--callback-text", help="Text for callback answer")
    parser.add_argument("--callback-alert", action="store_true", help="Show callback as alert")

    args = parser.parse_args()

    try:
        notifier = TelegramNotifier(
            chat_id=args.chat_id,
            thread_id=args.thread_id,
            parse_mode=args.parse_mode if args.parse_mode != "None" else None
        )
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    # Answer callback query
    if args.callback_id:
        result = notifier.answer_callback(
            args.callback_id,
            text=args.callback_text,
            show_alert=args.callback_alert
        )
        if result and result.get("ok"):
            print("Callback answered successfully")
        else:
            print(f"Failed to answer callback: {result}")
            sys.exit(1)
        return

    # Delete message
    if args.delete_chat and args.delete_msg:
        result = notifier.delete(args.delete_chat, args.delete_msg)
        if result and result.get("ok"):
            print(f"Message {args.delete_msg} deleted")
        else:
            print(f"Failed to delete: {result}")
            sys.exit(1)
        return

    # Edit message
    if args.edit_chat and args.edit_msg:
        result = notifier.edit(
            args.edit_chat,
            args.edit_msg,
            text=args.text if args.text else None,
            buttons=args.buttons
        )
        if result and result.get("ok"):
            print(f"Message {args.edit_msg} edited")
            print(json.dumps(result.get("result", {}), indent=2))
        else:
            print(f"Failed to edit: {result}")
            sys.exit(1)
        return

    # Send message (default)
    if not args.text and not args.buttons:
        parser.print_help()
        sys.exit(1)

    result = notifier.send(
        args.text,
        buttons=args.buttons,
        silent=args.silent,
        broadcast=True,  # Enable broadcast to all chat IDs
        webapp_url=args.webapp_url,
        webapp_text=args.webapp_text,
    )

    if result and result.get("ok"):
        results = result.get("results", [])
        print(f"Message sent to {len(results)} chat(s):")
        for r in results:
            if r.get("ok"):
                msg = r.get("result", {})
                print(f"  ✅ Chat {r.get('chat_id')}: message_id={msg.get('message_id')}")
            else:
                print(f"  ❌ Chat {r.get('chat_id')}: {r.get('error')}")
    else:
        print(f"Failed to send to some chats: {result}")
        sys.exit(1)


if __name__ == "__main__":
    main()
