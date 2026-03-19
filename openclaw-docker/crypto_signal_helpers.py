#!/usr/bin/env python3
"""
A2UI helpers for Python scripts.
Provides WebApp button support via direct Telegram Bot API calls.

Usage:
  from crypto_signal_helpers import send_telegram_message, create_webapp_button, create_inline_buttons

  # Send with WebApp button
  send_telegram_message(
      text="� сигнал!",
      buttons=[
          [create_webapp_button("report", {"type": "crypto_signal", "symbol": "BTC", "direction": "BUY"})],
          [create_inline_buttons([{"text": "📈 Buy", "callback_data": "buy_btc"}, {"text": "⏭ Skip", "callback_data": "skip_btc"}])[0]]
      ]
  )
"""

import json
import os
import uuid
import datetime as dt
from typing import Optional

import requests

# Config from environment
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
API_BASE = f"https://api.telegram.org/bot{BOT_TOKEN}"

FORMS_CACHE = "/tmp/a2ui_forms_shared.json"

# Use docker to write to a2ui-forms volume (accessible by vault-viewer)
def _write_form_docker(form_id: str, form_data: dict, created_at: str):
    """Write form to vault-viewer's a2ui-forms volume using docker run."""
    import subprocess, json
    
    # Read existing forms
    try:
        result = subprocess.run([
            "docker", "run", "--rm", "-v", "a2ui-forms:/data/a2ui",
            "python:3.12-slim", "sh", "-c",
            "cat /data/a2ui/a2ui_forms.json 2>/dev/null || echo '{}'"
        ], capture_output=True, text=True, timeout=15)
        try:
            forms = json.loads(result.stdout) if result.stdout.strip() else {}
        except:
            forms = {}
    except:
        forms = {}
    
    # Add new form
    forms[form_id] = {"formType": "crypto-signal", "formData": form_data, "createdAt": created_at}
    
    # Write back
    json_str = json.dumps(forms, ensure_ascii=False)
    write_cmd = f"python3 -c \"import json; f=open('/data/a2ui/a2ui_forms.json','w'); json.dump({json_str}, f); f.close()\""
    
    subprocess.run([
        "docker", "run", "--rm", "-v", "a2ui-forms:/data/a2ui",
        "python:3.12-slim", "sh", "-c", write_cmd
    ], capture_output=True, timeout=15)

WEBAPP_BASE = "https://vault.volamoks.store/a2ui"


def _load_forms():
    if os.path.exists(FORMS_CACHE):
        try:
            with open(FORMS_CACHE) as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def _save_forms(forms):
    """Save forms: write to Mac Mini /tmp (via docker cp from vault-viewer)"""
    try:
        import subprocess, os
        # Write to Mac Mini's /tmp via docker cp
        # vault-viewer runs on same docker host, so docker cp works
        # We write to Mac Mini's /tmp/a2ui_forms_shared.json then copy to vault-viewer
        import json as _json
        with open("/tmp/a2ui_forms_shared.json", "w") as f:
            _json.dump(forms, f, ensure_ascii=False)
        # Copy to vault-viewer container's /home/node/.openclaw
        subprocess.run(
            ["docker", "cp", "/tmp/a2ui_forms_shared.json",
             "vault-viewer:/home/node/.openclaw/a2ui_forms.json"],
            capture_output=True, timeout=10
        )
    except Exception as e:
        print(f"[crypto_signal_helpers] sync error: {e}", file=sys.stderr)


def create_webapp_button(form_type: str, form_data: dict, button_text: Optional[str] = None) -> dict:
    """
    Create a Telegram WebApp button that opens a form.

    Args:
        form_type: Form type (e.g. 'report', 'tasks', 'crypto-signal')
        form_data: Data to embed in the form
        button_text: Button label (default: 📊 {form_type})

    Returns:
        dict with {text, web_app: {url}}
    """
    form_id = str(uuid.uuid4())[:8]

    # Store form data
    forms = _load_forms()
    forms[form_id] = {
        "formType": form_type,
        "formData": form_data,
        "createdAt": dt.datetime.utcnow().isoformat() + "Z",
    }
    _save_forms(forms)

    url = f"{WEBAPP_BASE}/{form_type}?id={form_id}"
    text = button_text or f"📊 {form_type.replace('-', ' ').title()}"

    return {"text": text, "web_app": {"url": url}}


def create_inline_buttons(options: list, max_per_row: int = 2) -> list:
    """
    Create inline button rows.

    Args:
        options: List of {text, callback_data} dicts, or list of strings
        max_per_row: Max buttons per row (default 2)

    Returns:
        List of rows, each row is a list of {text, callback_data} dicts
    """
    rows = []
    row = []
    for opt in options:
        if isinstance(opt, str):
            opt = {"text": opt, "callback_data": opt.lower().replace(" ", "_")}
        row.append(opt)
        if len(row) >= max_per_row:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    return rows


def send_telegram_message(
    text: str,
    buttons: Optional[list] = None,
    chat_id: Optional[str] = None,
    parse_mode: Optional[str] = "Markdown",
    disable_web_page_preview: bool = True,
    reply_to_message_id: Optional[int] = None,
) -> Optional[dict]:
    """
    Send a Telegram message with buttons using direct Bot API.

    Args:
        text: Message text
        buttons: 2D array of button dicts [{text, callback_data}] or [{text, web_app: {url}}]
        chat_id: Target chat ID (default: TELEGRAM_CHAT_ID env)
        parse_mode: Parse mode (Markdown, HTML, None)
        disable_web_page_preview: Disable link previews
        reply_to_message_id: Reply to specific message

    Returns:
        Telegram API response dict or None on error
    """
    if not BOT_TOKEN:
        print("[crypto_signal_helpers] TELEGRAM_BOT_TOKEN not set")
        return None

    target = chat_id or CHAT_ID
    if not target:
        print("[crypto_signal_helpers] TELEGRAM_CHAT_ID not set")
        return None

    payload = {
        "chat_id": target,
        "text": text,
        "parse_mode": parse_mode if parse_mode else None,
        "disable_web_page_preview": disable_web_page_preview,
    }
    if reply_to_message_id:
        payload["reply_to_message_id"] = reply_to_message_id

    # Build reply_markup
    if buttons:
        inline_keyboard = []
        for row in buttons:
            button_row = []
            for btn in row:
                b = {"text": btn["text"]}
                if "callback_data" in btn:
                    b["callback_data"] = btn["callback_data"]
                if "web_app" in btn:
                    b["web_app"] = btn["web_app"]
                if "url" in btn:
                    b["url"] = btn["url"]
                button_row.append(b)
            inline_keyboard.append(button_row)
        payload["reply_markup"] = json.dumps({"inline_keyboard": inline_keyboard})

    try:
        resp = requests.post(f"{API_BASE}/sendMessage", json=payload, timeout=15)
        result = resp.json()
        if result.get("ok"):
            return result.get("result")
        else:
            print(f"[crypto_signal_helpers] API error: {result}")
            return None
    except Exception as e:
        print(f"[crypto_signal_helpers] Request failed: {e}")
        return None


def send_telegram_photo(
    photo_url: str,
    caption: Optional[str] = None,
    buttons: Optional[list] = None,
    chat_id: Optional[str] = None,
    parse_mode: Optional[str] = "Markdown",
) -> Optional[dict]:
    """Send photo with optional buttons."""
    if not BOT_TOKEN:
        return None

    target = chat_id or CHAT_ID
    payload = {
        "chat_id": target,
        "photo": photo_url,
        "caption": caption or "",
        "parse_mode": parse_mode if caption and parse_mode else None,
    }

    if buttons:
        inline_keyboard = []
        for row in buttons:
            button_row = []
            for btn in row:
                b = {"text": btn["text"]}
                if "callback_data" in btn:
                    b["callback_data"] = btn["callback_data"]
                if "web_app" in btn:
                    b["web_app"] = btn["web_app"]
                if "url" in btn:
                    b["url"] = btn["url"]
                button_row.append(b)
            inline_keyboard.append(button_row)
        payload["reply_markup"] = json.dumps({"inline_keyboard": inline_keyboard})

    try:
        resp = requests.post(f"{API_BASE}/sendPhoto", json=payload, timeout=15)
        result = resp.json()
        if result.get("ok"):
            return result.get("result")
        else:
            print(f"[crypto_signal_helpers] sendPhoto error: {result}")
            return None
    except Exception as e:
        print(f"[crypto_signal_helpers] sendPhoto failed: {e}")
        return None


def edit_telegram_message(
    text: str,
    message_id: int,
    buttons: Optional[list] = None,
    chat_id: Optional[str] = None,
    parse_mode: Optional[str] = "Markdown",
) -> Optional[dict]:
    """
    Edit an existing Telegram message using Bot API editMessageText.
    This enables the 'streaming' pattern: send initial message, then edit as data comes in.

    Args:
        text: New message text
        message_id: ID of message to edit
        buttons: Optional 2D array of inline keyboard buttons
        chat_id: Target chat ID (default: TELEGRAM_CHAT_ID env)
        parse_mode: Parse mode (Markdown, HTML, None)

    Returns:
        Telegram API response dict or None on error
    """
    import os, urllib.request, json

    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat = chat_id or os.environ.get("TELEGRAM_CHAT_ID", "6053956251")

    url = f"https://api.telegram.org/bot{token}/editMessageText"
    payload = {
        "chat_id": chat,
        "message_id": message_id,
        "text": text,
    }
    if parse_mode:
        payload["parse_mode"] = parse_mode
    if buttons:
        payload["reply_markup"] = json.dumps({
            "inline_keyboard": buttons
        })

    try:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read())
    except Exception as e:
        print(f"[edit_telegram_message] Error: {e}")
        return None
