import os
import sys

# Import the unified Telegram notifier
from telegram.notify import TelegramNotifier

WORKSPACE_DIR = "/home/node/.openclaw/workspace"
STATE_FILE = os.path.join(WORKSPACE_DIR, "telegram_status_msg_id.txt")


def main():
    # Initialize notifier (reads TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID from env)
    try:
        notifier = TelegramNotifier()
    except ValueError as e:
        print(f"Error: {e}")
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
        resp = notifier.edit(
            chat_id=notifier.chat_id,
            message_id=msg_id,
            text=formatted_text
        )
        if resp and resp.get("ok"):
            print(f"Status updated (edited msg {msg_id})")
        else:
            # If editing failed (e.g. message deleted), fallback to sending new
            print("Failed to edit, sending new message instead.")
            msg_id = None

    if not msg_id:
        # Send new message
        resp = notifier.send(formatted_text)
        if resp and resp.get("ok"):
            new_msg_id = resp["result"]["message_id"]
            with open(STATE_FILE, "w") as f:
                f.write(str(new_msg_id))
            print(f"Status updated (new msg {new_msg_id})")
        else:
            print("Failed to send status update.")

if __name__ == "__main__":
    main()
