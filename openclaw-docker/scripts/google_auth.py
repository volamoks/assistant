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

# Auto-detect: use container paths if inside Docker, otherwise use local Mac paths
if os.path.exists("/.dockerenv") or os.path.exists("/home/node"):
    # Running inside Docker container
    DEFAULT_SHARED_PATH = "/home/node/.openclaw/shared"
else:
    # Running on local Mac
    DEFAULT_SHARED_PATH = "/Users/abror_mac_mini/Projects/bot/openclaw-docker/shared"

CREDENTIALS_FILE = os.environ.get(
    "GOOGLE_CREDENTIALS",
    f"{DEFAULT_SHARED_PATH}/google_credentials.json"
)
TOKEN_FILE = os.environ.get(
    "GOOGLE_TOKEN",
    f"{DEFAULT_SHARED_PATH}/google_token.json"
)

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/calendar.events",
]

def main():
    global CREDENTIALS_FILE
    
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
        # Try alternative local path
        alt_creds = "/Users/abror_mac_mini/Projects/bot/openclaw-docker/shared/google_credentials.json"
        if os.path.exists(alt_creds):
            CREDENTIALS_FILE = alt_creds
        else:
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
            # Works for both 'web' and 'installed' credential types
            # Try browser first, fallback to console for headless environments
            try:
                flow = InstalledAppFlow.from_client_secrets_file(
                    CREDENTIALS_FILE, 
                    SCOPES
                )
                creds = flow.run_local_server(
                    port=8080,
                    prompt="consent",
                    access_type="offline"
                )
            except Exception as e:
                # Fallback to console mode for headless/container environments
                print(f"⚠️ Browser not available ({e}), using manual authorization...")
                flow = InstalledAppFlow.from_client_secrets_file(
                    CREDENTIALS_FILE, 
                    SCOPES
                )
                # Manual authorization: print URL, user copies code
                auth_url, _ = flow.authorization_url(prompt='consent', access_type='offline')
                print(f"\n🔗 Open this URL in your browser:\n{auth_url}\n")
                code = input("Enter the authorization code from the redirect URL: ").strip()
                flow.fetch_token(code=code)
                creds = flow.credentials

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
