#!/usr/bin/env python3
"""
google_auth_code.py — Complete OAuth2 flow with authorization code.

Usage:
  python3 google_auth_code.py <authorization_code>
"""

import os
import sys

DEFAULT_SHARED_PATH = "/home/node/.openclaw/shared"
CREDENTIALS_FILE = os.environ.get("GOOGLE_CREDENTIALS", f"{DEFAULT_SHARED_PATH}/google_credentials.json")
TOKEN_FILE = os.environ.get("GOOGLE_TOKEN", f"{DEFAULT_SHARED_PATH}/google_token.json")
SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/calendar.events",
]

if len(sys.argv) != 2:
    print("Usage: python3 google_auth_code.py <authorization_code>")
    print("\nFirst run: python3 google_auth_url.py")
    print("Then copy the code from the redirect URL and run this script.")
    sys.exit(1)

AUTH_CODE = sys.argv[1]

from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials

if not os.path.exists(CREDENTIALS_FILE):
    print(f"❌ credentials.json not found at: {CREDENTIALS_FILE}")
    sys.exit(1)

flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)

try:
    flow.fetch_token(code=AUTH_CODE)
    creds = flow.credentials
    
    # Save token
    os.makedirs(os.path.dirname(TOKEN_FILE), exist_ok=True)
    with open(TOKEN_FILE, "w") as f:
        f.write(creds.to_json())
    
    # Get email address
    from googleapiclient.discovery import build
    service = build('gmail', 'v1', credentials=creds)
    profile = service.users().getProfile(userId='me').execute()
    email = profile.get('emailAddress', 'unknown')
    
    print("✅ Google authorization successful!")
    print(f"   Account: {email}")
    print(f"   Token: {TOKEN_FILE}")
    print("   Scopes: Gmail (read/send) + Calendar (read/write)")
    print("\nYou can now use:")
    print("   bash /data/bot/openclaw-docker/scripts/gmail.sh inbox")
    print("   bash /data/bot/openclaw-docker/scripts/gcal.sh today")
    
except Exception as e:
    print(f"❌ Authorization failed: {e}")
    print("   Make sure you copied the code correctly.")
    sys.exit(1)
