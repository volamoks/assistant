#!/usr/bin/env python3
"""
google_auth.py — One-time OAuth2 authorization for Gmail + Calendar.

Usage:
  1. Place credentials.json in the same directory (from Google Cloud Console)
  2. Run: python3 /data/bot/openclaw-docker/scripts/google_auth.py
  3. A browser will open → grant access → token.json is saved
  4. Done! gmail.sh and gcal.sh will use token.json automatically.

Credentials setup:
  https://console.cloud.google.com → APIs & Services → Credentials
  → Create OAuth client ID → Desktop app → Download JSON → rename to credentials.json
"""

import os
import sys

CREDENTIALS_FILE = os.environ.get(
    "GOOGLE_CREDENTIALS",
    "/home/node/.openclaw/shared/google_credentials.json"
)
TOKEN_FILE = os.environ.get(
    "GOOGLE_TOKEN",
    "/home/node/.openclaw/shared/google_token.json"
)

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/calendar.events",
]

def main():
    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        import json
    except ImportError:
        print("❌ Missing dependencies. Install them:")
        print("   pip3 install google-auth-oauthlib google-auth-httplib2 google-api-python-client --break-system-packages")
        sys.exit(1)

    if not os.path.exists(CREDENTIALS_FILE):
        print(f"❌ credentials.json not found at: {CREDENTIALS_FILE}")
        print("   Download from: https://console.cloud.google.com → APIs & Services → Credentials")
        print(f"   Then place it at: {CREDENTIALS_FILE}")
        sys.exit(1)

    creds = None

    # Load existing token if available
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    # Refresh or re-authorize
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            print("✅ Token refreshed.")
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            # Try local server first, fallback to console (for headless)
            try:
                creds = flow.run_local_server(port=0)
            except Exception:
                creds = flow.run_console()

        # Save token
        os.makedirs(os.path.dirname(TOKEN_FILE), exist_ok=True)
        with open(TOKEN_FILE, "w") as f:
            f.write(creds.to_json())
        print(f"✅ Token saved to: {TOKEN_FILE}")

    print("✅ Google authorization successful!")
    print(f"   Token: {TOKEN_FILE}")
    print("   Scopes: Gmail (read/send) + Calendar (read/write)")
    print("\nYou can now use:")
    print("   bash /data/bot/openclaw-docker/scripts/gmail.sh inbox")
    print("   bash /data/bot/openclaw-docker/scripts/gcal.sh today")

if __name__ == "__main__":
    main()
