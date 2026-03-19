#!/usr/bin/env python3
"""
Confluence Push — Push Obsidian Markdown to Confluence
Uses: editor representation (Confluence Editor Format)

Usage:
    python3 conf_push_simple.py --file "/path/to/note.md" --page-id "123456789"
    python3 conf_push_simple.py --file "/path/to/note.md" --space "LP" --title "Title" [--create]
"""
import argparse, os, sys, re
from pathlib import Path

sys.path.insert(0, '/home/node/.openclaw/pypackages')
try:
    import markdown
except ImportError:
    print("ERROR: markdown not found")
    sys.exit(1)

ENV_FILE = '/data/bot/openclaw-docker/core/.env'
for line in open(ENV_FILE) if os.path.exists(ENV_FILE) else []:
    line = line.strip()
    if line and not line.startswith('#') and '=' in line:
        k, v = line.split('=', 1)
        os.environ[k.strip()] = v.strip().strip('"').strip("'")

URL    = os.environ.get('CONFLUENCE_URL','')
EMAIL  = os.environ.get('CONFLUENCE_EMAIL','')
TOKEN  = os.environ.get('CONFLUENCE_API_TOKEN','')

import base64, requests
AUTH   = base64.b64encode(f"{EMAIL}:{TOKEN}".encode()).decode()
HEADERS = {"Authorization": f"Basic {AUTH}", "Content-Type": "application/json", "Accept": "application/json"}


def md_to_html(text: str) -> str:
    md = markdown.Markdown(extensions=[
        'markdown.extensions.tables',
        'markdown.extensions.fenced_code',
        'markdown.extensions.codehilite',
    ], extension_configs={
        'markdown.extensions.codehilite': {'css_class': 'code-block', 'guess_lang': False}
    })
    html = md.convert(text)
    # Clean up
    html = re.sub(r'<p>\s*</p>', '', html)
    html = re.sub(r'<pre><code class="([^"]*)">', r'<pre class="code-block \1">', html)
    html = re.sub(r'<pre><code>', '<pre class="code-block">', html)
    html = re.sub(r'</code></pre>', '</pre>', html)
    html = re.sub(r'<div class="codehilite">', '', html)
    html = re.sub(r'</div>\s*$', '', html, flags=re.MULTILINE)
    html = re.sub(r'<pre class="code-block">\s+', '<pre class="code-block">', html)
    html = re.sub(r'\s+</pre>', '</pre>', html)
    return html


def get_page(page_id=None, space=None, title=None):
    if page_id:
        r = requests.get(f"{URL}/rest/api/content/{page_id}?expand=version", headers=HEADERS, timeout=15)
        return r.json() if r.status_code == 200 else None
    if space and title:
        r = requests.get(f"{URL}/rest/api/content", params={"spaceKey": space, "title": title, "expand": "version"}, headers=HEADERS, timeout=15)
        results = r.json().get('results', [])
        return results[0] if results else None
    return None


def push(page_id: str, html_content: str, title: str):
    page = get_page(page_id)
    if not page:
        print(f"ERROR: page {page_id} not found"); sys.exit(1)
    ver = page.get('version', {}).get('number', 1)
    payload = {
        "version": {"number": ver + 1},
        "title": title,
        "type": "page",
        "body": {
            "editor": {
                "value": html_content,
                "representation": "editor"
            }
        }
    }
    r = requests.put(f"{URL}/rest/api/content/{page_id}", headers=HEADERS, json=payload, timeout=30)
    if r.status_code in (200, 201):
        new_ver = r.json().get('version', {}).get('number', '?')
        print(f"✅ Written! Version: {new_ver}")
    else:
        print(f"❌ {r.status_code}: {r.text[:300]}"); sys.exit(1)


def create(space: str, title: str, html_content: str):
    payload = {
        "type": "page", "title": title, "space": {"key": space},
        "body": {
            "editor": {
                "value": html_content,
                "representation": "editor"
            }
        }
    }
    r = requests.post(f"{URL}/rest/api/content", headers=HEADERS, json=payload, timeout=30)
    if r.status_code in (200, 201):
        d = r.json()
        print(f"✅ Created! ID: {d.get('id','?')}, Ver: {d.get('version',{}).get('number','?')}")
    else:
        print(f"❌ {r.status_code}: {r.text[:300]}"); sys.exit(1)


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--file'); p.add_argument('--page-id'); p.add_argument('--space')
    p.add_argument('--title'); p.add_argument('--create', action='store_true')
    a = p.parse_args()

    if not os.path.exists(a.file): print(f"File not found: {a.file}"); sys.exit(1)
    if not a.page_id and not (a.space and a.title): print("Need --page-id OR (--space AND --title)"); sys.exit(1)
    if a.create and not (a.space and a.title): print("--create needs --space and --title"); sys.exit(1)

    with open(a.file, encoding='utf-8') as f: md_text = f.read()
    if not md_text.strip(): print("Empty file"); sys.exit(1)

    print(f"📄 {a.file} ({len(md_text)} chars)")
    title = a.title or (re.search(r'^#\s+(.+)$', md_text, re.MULTILINE) or re.match(r'(.+?)(?:\n|$)', md_text)).group(1).strip()
    html = md_to_html(md_text)
    print(f"🔄 HTML ({len(html)} chars)")

    page_id = a.page_id
    if not page_id and not a.create:
        pg = get_page(space=a.space, title=a.title)
        if pg:
            page_id = pg.get('id')
            print(f"🔍 Page: {page_id} (v{pg.get('version',{}).get('number','?')})")
        else:
            print("⚠️  Page not found. Use --create."); sys.exit(1)

    create(a.space, title, html) if a.create else push(page_id, html, title)
