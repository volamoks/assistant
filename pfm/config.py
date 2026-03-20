import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Try multiple locations for .env file
ENV_PATHS = [
    Path(__file__).parent / ".env",
    Path(__file__).parent.parent / "openclaw-docker" / ".env",
    Path.home() / ".env",
    Path("/data/bot/.env"),
]
for env_path in ENV_PATHS:
    if env_path.exists():
        load_dotenv(env_path)
        break

DB_PATHS = [
    Path.home() / "Library/Mobile Documents/iCloud~md~obsidian/Documents/My Docs/Attachments/finance.db",
    Path.home() / "Library/Mobile Documents/com~apple~CloudDocs/abror/Attachments/finance.db",
    Path("/data/obsidian/Attachments/finance.db"),
    Path(__file__).parent / "finance.db",  # Fallback
]

def find_db() -> Path:
    for p in DB_PATHS:
        if p.exists():
            return p
    sys.exit("❌ Error: finance.db not found")
