#!/usr/bin/env python3
"""
Multi-account IMAP/SMTP email tool for OpenClaw.

Accounts config: /home/node/.openclaw/shared/email_accounts.json
  [
    {
      "name": "Gmail Personal",
      "email": "you@gmail.com",
      "password": "app_password_here",
      "imap_host": "imap.gmail.com",   -- optional, auto-detected from domain
      "smtp_host": "smtp.gmail.com"    -- optional, auto-detected from domain
    }
  ]

Usage:
  python3 email_imap.py accounts
  python3 email_imap.py inbox [--account NAME] [--max 10]
  python3 email_imap.py read <uid> --account NAME
  python3 email_imap.py search "<query>" [--account NAME] [--max 10]
  python3 email_imap.py send --to addr --subject "..." --body "..." [--account NAME]
"""

import imaplib
import smtplib
import json
import os
import sys
import argparse
import email
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import decode_header
import ssl
from datetime import datetime

# ── Config ────────────────────────────────────────────────────────────────────

CONFIG_PATH = os.environ.get("EMAIL_ACCOUNTS_FILE")
if not CONFIG_PATH:
    raise ValueError("EMAIL_ACCOUNTS_FILE environment variable is required (e.g., /path/to/email_accounts.json)")

# Known IMAP/SMTP servers by domain
KNOWN_SERVERS = {
    "gmail.com":     {"imap": "imap.gmail.com",           "smtp": "smtp.gmail.com"},
    "googlemail.com":{"imap": "imap.gmail.com",           "smtp": "smtp.gmail.com"},
    "outlook.com":   {"imap": "imap-mail.outlook.com",    "smtp": "smtp-mail.outlook.com"},
    "hotmail.com":   {"imap": "imap-mail.outlook.com",    "smtp": "smtp-mail.outlook.com"},
    "live.com":      {"imap": "imap-mail.outlook.com",    "smtp": "smtp-mail.outlook.com"},
    "icloud.com":    {"imap": "imap.mail.me.com",         "smtp": "smtp.mail.me.com"},
    "me.com":        {"imap": "imap.mail.me.com",         "smtp": "smtp.mail.me.com"},
    "mail.ru":       {"imap": "imap.mail.ru",             "smtp": "smtp.mail.ru"},
    "yandex.ru":     {"imap": "imap.yandex.ru",           "smtp": "smtp.yandex.ru"},
    "yahoo.com":     {"imap": "imap.mail.yahoo.com",      "smtp": "smtp.mail.yahoo.com"},
}


def load_accounts():
    if not os.path.exists(CONFIG_PATH):
        print(f"❌ Config not found: {CONFIG_PATH}", file=sys.stderr)
        print("Create it with your email accounts. See skill README.", file=sys.stderr)
        sys.exit(1)
    with open(CONFIG_PATH) as f:
        accounts = json.load(f)
    # Skip disabled (template) entries
    accounts = [a for a in accounts if not a.get("disabled")]
    # Resolve env: references (e.g. "env:MY_VAR" → os.environ["MY_VAR"])
    for acc in accounts:
        pw = acc.get("password", "")
        if pw.startswith("env:"):
            var = pw[4:]
            acc["password"] = os.environ.get(var, "")
            if not acc["password"]:
                print(f"❌ Env var {var} not set for account '{acc['name']}'", file=sys.stderr)
                sys.exit(1)
    # Auto-fill imap/smtp hosts from domain if not specified
    for acc in accounts:
        domain = acc["email"].split("@")[-1].lower()
        if "imap_host" not in acc:
            acc["imap_host"] = KNOWN_SERVERS.get(domain, {}).get("imap", f"imap.{domain}")
        if "smtp_host" not in acc:
            acc["smtp_host"] = KNOWN_SERVERS.get(domain, {}).get("smtp", f"smtp.{domain}")
    return accounts


def find_account(accounts, name=None):
    if name is None:
        return accounts[0]
    for acc in accounts:
        if acc["name"].lower() == name.lower() or acc["email"].lower() == name.lower():
            return acc
    print(f"❌ Account '{name}' not found.", file=sys.stderr)
    sys.exit(1)


def decode_str(s):
    if s is None:
        return ""
    parts = decode_header(s)
    result = []
    for part, enc in parts:
        if isinstance(part, bytes):
            result.append(part.decode(enc or "utf-8", errors="replace"))
        else:
            result.append(str(part))
    return "".join(result)


def imap_connect(acc):
    ctx = ssl.create_default_context()
    conn = imaplib.IMAP4_SSL(acc["imap_host"], 993, ssl_context=ctx)
    conn.login(acc["email"], acc["password"])
    return conn


def fetch_message(conn, uid):
    _, data = conn.uid("fetch", uid, "(RFC822)")
    if not data or data[0] is None:
        return None
    return email.message_from_bytes(data[0][1])


def get_text_body(msg):
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            ct = part.get_content_type()
            cd = str(part.get("Content-Disposition", ""))
            if ct == "text/plain" and "attachment" not in cd:
                payload = part.get_payload(decode=True)
                if payload:
                    body += payload.decode(part.get_content_charset() or "utf-8", errors="replace")
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            body = payload.decode(msg.get_content_charset() or "utf-8", errors="replace")
    return body.strip()


# ── Commands ──────────────────────────────────────────────────────────────────

def cmd_accounts(args):
    accounts = load_accounts()
    print(f"📬 Configured accounts ({len(accounts)}):\n")
    for i, acc in enumerate(accounts, 1):
        print(f"  {i}. {acc['name']} <{acc['email']}>")
        print(f"     IMAP: {acc['imap_host']}  SMTP: {acc['smtp_host']}")
    print()


def cmd_inbox(args):
    accounts = load_accounts()
    targets = [find_account(accounts, args.account)] if args.account else accounts
    max_msgs = args.max or 10

    for acc in targets:
        print(f"\n📬 [{acc['name']}] {acc['email']}")
        print("─" * 50)
        try:
            conn = imap_connect(acc)
            conn.select("INBOX")
            _, uids = conn.uid("search", None, "UNSEEN")
            uid_list = uids[0].split() if uids[0] else []

            if not uid_list:
                print("  (no unread messages)")
                conn.logout()
                continue

            uid_list = uid_list[-max_msgs:]  # most recent N
            print(f"  {len(uid_list)} unread (showing last {len(uid_list)}):\n")

            for uid in reversed(uid_list):
                _, data = conn.uid("fetch", uid, "(BODY.PEEK[HEADER.FIELDS (FROM SUBJECT DATE)])")
                if not data or data[0] is None:
                    continue
                msg = email.message_from_bytes(data[0][1])
                subject = decode_str(msg.get("Subject", "(no subject)"))[:70]
                sender  = decode_str(msg.get("From", ""))[:50]
                date    = msg.get("Date", "")[:25]
                print(f"  UID: {uid.decode()}")
                print(f"  From: {sender}")
                print(f"  Subject: {subject}")
                print(f"  Date: {date}")
                print()

            conn.logout()
        except Exception as e:
            print(f"  ❌ Error: {e}")


def cmd_read(args):
    accounts = load_accounts()
    acc = find_account(accounts, args.account)

    try:
        conn = imap_connect(acc)
        conn.select("INBOX")
        msg = fetch_message(conn, args.uid.encode())
        conn.logout()
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

    if not msg:
        print("❌ Message not found")
        sys.exit(1)

    print(f"From: {decode_str(msg.get('From', ''))}")
    print(f"To: {decode_str(msg.get('To', ''))}")
    print(f"Date: {msg.get('Date', '')}")
    print(f"Subject: {decode_str(msg.get('Subject', ''))}")
    print("─" * 50)
    body = get_text_body(msg)
    print(body[:4000])
    if len(body) > 4000:
        print(f"\n... [truncated, {len(body)} chars total]")


def cmd_search(args):
    accounts = load_accounts()
    targets = [find_account(accounts, args.account)] if args.account else accounts
    max_msgs = args.max or 10
    query = args.query

    # Convert simple query to IMAP search criteria
    imap_criteria = "ALL"
    if "subject:" in query.lower():
        subj = query.lower().split("subject:")[-1].split()[0]
        imap_criteria = f'SUBJECT "{subj}"'
    elif "from:" in query.lower():
        frm = query.lower().split("from:")[-1].split()[0]
        imap_criteria = f'FROM "{frm}"'
    elif "is:unread" in query.lower():
        imap_criteria = "UNSEEN"
    else:
        imap_criteria = f'TEXT "{query}"'

    for acc in targets:
        print(f"\n🔍 [{acc['name']}] searching: {query}")
        print("─" * 50)
        try:
            conn = imap_connect(acc)
            conn.select("INBOX")
            _, uids = conn.uid("search", None, imap_criteria)
            uid_list = uids[0].split() if uids[0] else []

            if not uid_list:
                print("  (no results)")
                conn.logout()
                continue

            uid_list = uid_list[-max_msgs:]
            print(f"  {len(uid_list)} result(s):\n")

            for uid in reversed(uid_list):
                _, data = conn.uid("fetch", uid, "(BODY.PEEK[HEADER.FIELDS (FROM SUBJECT DATE)])")
                if not data or data[0] is None:
                    continue
                msg = email.message_from_bytes(data[0][1])
                subject = decode_str(msg.get("Subject", "(no subject)"))[:70]
                sender  = decode_str(msg.get("From", ""))[:50]
                date    = msg.get("Date", "")[:25]
                print(f"  UID: {uid.decode()}")
                print(f"  From: {sender}")
                print(f"  Subject: {subject}")
                print(f"  Date: {date}")
                print()

            conn.logout()
        except Exception as e:
            print(f"  ❌ Error: {e}")


def cmd_send(args):
    accounts = load_accounts()
    acc = find_account(accounts, args.account)

    msg = MIMEMultipart("alternative")
    msg["From"]    = acc["email"]
    msg["To"]      = args.to
    msg["Subject"] = args.subject
    msg.attach(MIMEText(args.body, "plain", "utf-8"))

    try:
        ctx = ssl.create_default_context()
        with smtplib.SMTP_SSL(acc["smtp_host"], 465, context=ctx) as server:
            server.login(acc["email"], acc["password"])
            server.sendmail(acc["email"], args.to, msg.as_string())
        print(f"✅ Sent from {acc['email']} to {args.to}")
    except Exception as e:
        print(f"❌ Send failed: {e}")
        sys.exit(1)


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Multi-account email tool")
    sub = parser.add_subparsers(dest="cmd")

    sub.add_parser("accounts", help="List configured accounts")

    p_inbox = sub.add_parser("inbox", help="Show unread messages")
    p_inbox.add_argument("--account", "-a", help="Account name or email")
    p_inbox.add_argument("--max", "-n", type=int, default=10)

    p_read = sub.add_parser("read", help="Read a message by UID")
    p_read.add_argument("uid")
    p_read.add_argument("--account", "-a", required=True)

    p_search = sub.add_parser("search", help="Search messages")
    p_search.add_argument("query")
    p_search.add_argument("--account", "-a")
    p_search.add_argument("--max", "-n", type=int, default=10)

    p_send = sub.add_parser("send", help="Send an email")
    p_send.add_argument("--to",      required=True)
    p_send.add_argument("--subject", required=True)
    p_send.add_argument("--body",    required=True)
    p_send.add_argument("--account", "-a")

    args = parser.parse_args()

    if args.cmd == "accounts": cmd_accounts(args)
    elif args.cmd == "inbox":  cmd_inbox(args)
    elif args.cmd == "read":   cmd_read(args)
    elif args.cmd == "search": cmd_search(args)
    elif args.cmd == "send":   cmd_send(args)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
