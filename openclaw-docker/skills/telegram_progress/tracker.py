import os
import sys
import json
import urllib.request
import urllib.parse
from urllib.error import URLError, HTTPError

# Telegram credentials
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
WORKSPACE_DIR = "/home/node/.openclaw/workspace"
STATE_FILE = os.path.join(WORKSPACE_DIR, "telegram_status_msg_id.txt")

def send_request(method, payload):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/{method}"
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req) as response:
            return json.loads(response.read().decode('utf-8'))
    except HTTPError as e:
        print(f"HTTPError: {e.code} - {e.reason}")
        print(e.read().decode('utf-8'))
        return None
    except URLError as e:
        print(f"URLError: {e.reason}")
        return None

def main():
    if not BOT_TOKEN or not CHAT_ID:
        print("Error: TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID must be set.")
        sys.exit(1)

    if len(sys.argv) < 2:
        print("Usage: python3 tracker.py '<status message>' [--clear]")
        sys.exit(1)

    if sys.argv[1] == "--clear":
        if os.path.exists(STATE_FILE):
            os.remove(STATE_FILE)
            print("Status state cleared.")
        sys.exit(0)

    status_text = sys.argv[1]
    formatted_text = f"🛠 **Статус задачи:**\n{status_text}"
    
    msg_id = None
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            content = f.read().strip()
            if content.isdigit():
                msg_id = int(content)

    if msg_id:
        # Edit existing message
        payload = {
            "chat_id": CHAT_ID,
            "message_id": msg_id,
            "text": formatted_text,
            "parse_mode": "Markdown"
        }
        resp = send_request("editMessageText", payload)
        if resp and resp.get("ok"):
            print(f"Status updated (edited msg {msg_id})")
        else:
            # If editing failed (e.g. message deleted), fallback to sending new
            print("Failed to edit, sending new message instead.")
            msg_id = None

    if not msg_id:
        # Send new message
        payload = {
            "chat_id": CHAT_ID,
            "text": formatted_text,
            "parse_mode": "Markdown"
        }
        resp = send_request("sendMessage", payload)
        if resp and resp.get("ok"):
            new_msg_id = resp["result"]["message_id"]
            with open(STATE_FILE, "w") as f:
                f.write(str(new_msg_id))
            print(f"Status updated (new msg {new_msg_id})")
        else:
            print("Failed to send status update.")

if __name__ == "__main__":
    main()
