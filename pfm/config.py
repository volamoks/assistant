import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Try multiple locations for .env file
ENV_PATHS = [
    Path(__file__).parent / ".env",
    Path.home() / ".env",
    Path("/data/bot/.env"),
]
for env_path in ENV_PATHS:
    if env_path.exists():
        load_dotenv(env_path)
        break

ACTUAL_URL      = os.environ.get("ACTUAL_URL") or os.getenv("ACTUAL_URL", "http://localhost:5006")
ACTUAL_PASSWORD = os.environ.get("ACTUAL_PASSWORD")
ACTUAL_FILE     = os.environ.get("ACTUAL_FILE")

# Validate required Actual Budget configuration
def validate_actual_config():
    if not ACTUAL_PASSWORD:
        sys.exit("❌ Error: ACTUAL_PASSWORD environment variable is required")
    if not ACTUAL_FILE:
        sys.exit("❌ Error: ACTUAL_FILE environment variable is required")

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

# Map our categories → Actual Budget category names
CATEGORY_MAP = {
    "FOOD":       "Food",
    "TRANSPORT":  "Transport",
    "SHOPPING":   "Shopping",
    "HEALTH":     "Health",
    "UTILITIES":  "Utilities",
    "TELECOM":    "Telecom",
    "ATM":        "ATM",
    "TRANSFER":   "Transfer",
    "OTHER":      "General",
}

CATEGORY_COLORS = {
    "FOOD": "#FF6B6B",
    "TRANSPORT": "#4ECDC4",
    "SHOPPING": "#45B7D1",
    "HEALTH": "#96CEB4",
    "UTILITIES": "#FECA57",
    "TELECOM": "#FF9FF3",
    "ATM": "#A29BFE",
    "TRANSFER": "#74B9FF",
    "OTHER": "#636E72",
}
