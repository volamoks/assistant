---
name: email
description: "Read and send emails across multiple accounts (Gmail, Outlook, iCloud, Mail.ru, Yahoo, Yandex) using IMAP/SMTP with App Passwords. No OAuth — works forever without token expiry."
triggers:
  - email
  - inbox
  - письмо
  - почта
  - отправь письмо
  - check email
  - send email
  - read email
  - unread
  - непрочитанные
  - mail
  - gmail
  - outlook
  - icloud
---

# Email (IMAP/SMTP)

Multi-account email via standard IMAP/SMTP. Accounts configured in `/home/node/.openclaw/shared/email_accounts.json`.

**Script:** `/data/bot/openclaw-docker/scripts/email_imap.py`

## Commands

### List configured accounts
```bash
python3 /data/bot/openclaw-docker/scripts/email_imap.py accounts
```

### Check unread inbox (all accounts)
```bash
python3 /data/bot/openclaw-docker/scripts/email_imap.py inbox
```

### Check specific account, limit results
```bash
python3 /data/bot/openclaw-docker/scripts/email_imap.py inbox --account "Gmail Personal" --max 5
python3 /data/bot/openclaw-docker/scripts/email_imap.py inbox --account "user@gmail.com" --max 20
```

### Read a specific message (UID from inbox output)
```bash
python3 /data/bot/openclaw-docker/scripts/email_imap.py read 1234 --account "Gmail Personal"
```

### Search messages
```bash
# Free text search
python3 /data/bot/openclaw-docker/scripts/email_imap.py search "invoice" --account "Gmail Personal"

# Search by subject
python3 /data/bot/openclaw-docker/scripts/email_imap.py search "subject:payment" --max 5

# Search by sender
python3 /data/bot/openclaw-docker/scripts/email_imap.py search "from:bank@example.com"

# Unread only
python3 /data/bot/openclaw-docker/scripts/email_imap.py search "is:unread" --account "Gmail Personal"
```

### Send an email
```bash
python3 /data/bot/openclaw-docker/scripts/email_imap.py send \
  --account "Gmail Personal" \
  --to "recipient@example.com" \
  --subject "Hello" \
  --body "Message text here"
```

## Accounts config format

File: `/home/node/.openclaw/shared/email_accounts.json`
(on host: `openclaw-docker/core/shared/email_accounts.json`)

```json
[
  {
    "name": "Gmail Personal",
    "email": "you@gmail.com",
    "password": "xxxx xxxx xxxx xxxx"
  },
  {
    "name": "Outlook Work",
    "email": "you@outlook.com",
    "password": "xxxx xxxx xxxx xxxx"
  },
  {
    "name": "iCloud",
    "email": "you@icloud.com",
    "password": "xxxx-xxxx-xxxx-xxxx",
    "imap_host": "imap.mail.me.com",
    "smtp_host": "smtp.mail.me.com"
  }
]
```

`imap_host` / `smtp_host` are optional — auto-detected from domain for Gmail, Outlook, iCloud, Mail.ru, Yahoo, Yandex.

## Where to get App Passwords

| Provider | URL |
|----------|-----|
| Gmail | myaccount.google.com → Security → App Passwords |
| Outlook | account.microsoft.com → Security → App passwords |
| iCloud | appleid.apple.com → Sign-In & Security → App-Specific Passwords |
| Mail.ru | account.mail.ru → Security → External app passwords |
| Yahoo | account.yahoo.com → Security → App passwords |
| Yandex | id.yandex.ru → Security → App passwords |

**Requires 2FA enabled** on the account first.
