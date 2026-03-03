#!/usr/bin/env python3
"""
google_auth_url.py — Print OAuth2 authorization URL for Gmail + Calendar.

Usage:
  1. Run: python3 google_auth_url.py
  2. Open the URL in browser
  3. Login and grant access
  4. Copy the code from redirect URL
  5. Run: python3 google_auth_code.py <code>
"""

import os
import sys

DEFAULT_SHARED_PATH = "/home/node/.openclaw/shared"
CREDENTIALS_FILE = os.environ.get("GOOGLE_CREDENTIALS", f"{DEFAULT_SHARED_PATH}/google_credentials.json")
SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/calendar.events",
]

from google_auth_oauthlib.flow import InstalledAppFlow

if not os.path.exists(CREDENTIALS_FILE):
    print(f"❌ credentials.json not found at: {CREDENTIALS_FILE}")
    sys.exit(1)

flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
auth_url, _ = flow.authorization_url(prompt='consent', access_type='offline')

print("=" * 70)
print("🔗 OPEN THIS URL IN YOUR BROWSER:")
print("=" * 70)
print(auth_url)
print("=" * 70)
print("\nAfter granting access, you'll be redirected to a URL like:")
print("  http://localhost:8080/?code=4/0AeanS0a...")
print("\nCopy the code (after 'code=') and run:")
print("  python3 google_auth_code.py <YOUR_CODE>")
