#!/usr/bin/env python3
"""Vault Viewer — renders Obsidian markdown files as HTML for Telegram WebApp."""

import os
import re
import html
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, unquote

try:
    import mistune
    HAVE_MISTUNE = True
except ImportError:
    HAVE_MISTUNE = False

VAULT_PATH = Path(os.environ.get("VAULT_PATH", "/data/obsidian/vault"))
REPORTS_DIR = VAULT_PATH / "Bot" / "DailyReports"
PORT = int(os.environ.get("PORT", "7080"))

CSS = """
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    background: var(--tg-theme-bg-color, #1a1a2e);
    color: var(--tg-theme-text-color, #e0e0e0);
    padding: 16px;
    max-width: 800px;
    margin: 0 auto;
    line-height: 1.6;
  }
  h1 { font-size: 1.4em; margin: 0.8em 0 0.4em; color: var(--tg-theme-hint-color, #a0a0c0); }
  h2 { font-size: 1.2em; margin: 0.8em 0 0.3em; border-bottom: 1px solid #333; padding-bottom: 4px; }
  h3 { font-size: 1.05em; margin: 0.6em 0 0.2em; }
  p { margin: 0.5em 0; }
  ul, ol { margin: 0.4em 0 0.4em 1.4em; }
  li { margin: 0.2em 0; }
  code {
    background: rgba(255,255,255,0.1);
    padding: 1px 5px;
    border-radius: 3px;
    font-size: 0.88em;
    font-family: 'SF Mono', Consolas, monospace;
  }
  pre {
    background: rgba(0,0,0,0.3);
    border-radius: 6px;
    padding: 10px;
    overflow-x: auto;
    margin: 0.6em 0;
  }
  pre code { background: none; padding: 0; }
  blockquote {
    border-left: 3px solid #555;
    padding-left: 10px;
    color: #aaa;
    margin: 0.5em 0;
  }
  table { border-collapse: collapse; width: 100%; margin: 0.6em 0; font-size: 0.9em; }
  th, td { border: 1px solid #444; padding: 5px 8px; text-align: left; }
  th { background: rgba(255,255,255,0.08); }
  a { color: var(--tg-theme-link-color, #6ea8fe); text-decoration: none; }
  .nav { margin-bottom: 16px; }
  .nav a { color: #888; font-size: 0.85em; }
  .report-list { list-style: none; margin: 0; padding: 0; }
  .report-list li { margin: 8px 0; }
  .report-list a {
    display: block;
    background: rgba(255,255,255,0.05);
    border: 1px solid #333;
    border-radius: 8px;
    padding: 10px 14px;
    color: var(--tg-theme-text-color, #e0e0e0);
    font-size: 0.95em;
  }
  .report-list a:hover { background: rgba(255,255,255,0.1); }
  .mtime { font-size: 0.78em; color: #666; margin-top: 2px; }
  .callout {
    border-left: 4px solid #5b8;
    background: rgba(80,180,120,0.08);
    border-radius: 0 6px 6px 0;
    padding: 8px 12px;
    margin: 0.5em 0;
  }
  .callout-warning { border-color: #e8a; background: rgba(220,80,120,0.08); }
  .callout-info { border-color: #58e; background: rgba(80,120,220,0.08); }
  hr { border: none; border-top: 1px solid #333; margin: 1em 0; }
  .ts { font-size: 0.8em; color: #555; float: right; }
</style>
"""

TELEGRAM_INIT = """
<script>
  window.Telegram && window.Telegram.WebApp && window.Telegram.WebApp.ready();
  // Apply Telegram theme if available
  if (window.Telegram && window.Telegram.WebApp.colorScheme === 'light') {
    document.body.style.background = '#ffffff';
    document.body.style.color = '#000000';
  }
</script>
"""

def render_markdown(text: str) -> str:
    """Convert markdown to HTML."""
    # Strip Obsidian frontmatter
    text = re.sub(r'^---\n.*?\n---\n', '', text, flags=re.DOTALL)

    # Convert Obsidian callouts: > [!NOTE] → styled div
    def convert_callout(m):
        kind = m.group(1).lower()
        content = m.group(2).strip()
        css_class = "callout"
        if kind in ("warning", "caution", "danger"):
            css_class += " callout-warning"
        elif kind in ("info", "note", "tip"):
            css_class += " callout-info"
        return f'<div class="{css_class}"><strong>[{kind.upper()}]</strong> {html.escape(content)}</div>'

    text = re.sub(r'> \[!(\w+)\]\n> (.+)', convert_callout, text)

    # Strip Obsidian wikilinks [[page]] → page
    text = re.sub(r'\[\[([^\]|]+)\|?([^\]]*)\]\]', lambda m: m.group(2) or m.group(1), text)

    if HAVE_MISTUNE:
        md = mistune.create_markdown(
            plugins=['table', 'strikethrough'],
            escape=False,
        )
        return md(text)
    else:
        # Minimal fallback
        lines = []
        in_pre = False
        for line in text.split('\n'):
            if line.startswith('```'):
                if in_pre:
                    lines.append('</code></pre>')
                    in_pre = False
                else:
                    lines.append('<pre><code>')
                    in_pre = True
                continue
            if in_pre:
                lines.append(html.escape(line))
                continue
            # Headers
            m = re.match(r'^(#{1,3})\s+(.+)', line)
            if m:
                lvl = len(m.group(1))
                lines.append(f'<h{lvl}>{html.escape(m.group(2))}</h{lvl}>')
                continue
            # HR
            if re.match(r'^---+$', line):
                lines.append('<hr>')
                continue
            # List items
            m = re.match(r'^[-*]\s+(.+)', line)
            if m:
                lines.append(f'<li>{html.escape(m.group(1))}</li>')
                continue
            # Bold/italic inline
            line = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html.escape(line))
            line = re.sub(r'\*(.+?)\*', r'<em>\1</em>', line)
            line = re.sub(r'`(.+?)`', r'<code>\1</code>', line)
            if line.strip():
                lines.append(f'<p>{line}</p>')
            else:
                lines.append('')
        return '\n'.join(lines)


def page(title: str, body: str, back: str = None) -> str:
    nav = ""
    if back:
        nav = f'<div class="nav"><a href="{back}">← Back</a></div>'
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{html.escape(title)}</title>
{CSS}
</head>
<body>
{TELEGRAM_INIT}
{nav}
{body}
</body>
</html>"""


class VaultHandler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass  # suppress default logging

    def send_html(self, content: str, status=200):
        encoded = content.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(encoded)

    def do_GET(self):
        parsed = urlparse(self.path)
        path = unquote(parsed.path).lstrip("/")

        # Health check
        if path in ("health", "healthz"):
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"ok")
            return

        # Index — list all reports
        if path == "" or path == "index":
            self._serve_index()
            return

        # Report page — /report/<filename> (without .md)
        if path.startswith("report/"):
            name = path[len("report/"):]
            self._serve_report(name)
            return

        # 404
        self.send_html(page("Not Found", "<p>Page not found.</p>"), status=404)

    def _serve_index(self):
        items = []
        if REPORTS_DIR.exists():
            files = sorted(REPORTS_DIR.glob("*.md"), key=lambda f: f.stat().st_mtime, reverse=True)
            for f in files:
                name = f.stem
                mtime = f.stat().st_mtime
                import datetime
                dt = datetime.datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M")
                label = name.replace("-", " ").replace("_", " ").title()
                items.append(
                    f'<li><a href="/report/{name}">'
                    f'{html.escape(label)}'
                    f'<div class="mtime">{dt}</div>'
                    f'</a></li>'
                )

        if items:
            body = f'<h1>Daily Reports</h1><ul class="report-list">{"".join(items)}</ul>'
        else:
            body = '<h1>Daily Reports</h1><p>No reports yet.</p>'

        self.send_html(page("Bot Reports", body))

    def _serve_report(self, name: str):
        # Sanitize — no path traversal
        name = re.sub(r'[^a-zA-Z0-9_\-]', '', name)
        md_file = REPORTS_DIR / f"{name}.md"

        if not md_file.exists():
            self.send_html(page("Not Found", f"<p>Report <code>{html.escape(name)}</code> not found.</p>", back="/"), status=404)
            return

        content = md_file.read_text(encoding="utf-8")
        rendered = render_markdown(content)
        label = name.replace("-", " ").replace("_", " ").title()
        self.send_html(page(label, rendered, back="/"))


if __name__ == "__main__":
    if not HAVE_MISTUNE:
        print("[vault-viewer] mistune not available, using fallback renderer")
    server = HTTPServer(("0.0.0.0", PORT), VaultHandler)
    print(f"[vault-viewer] Serving vault at {VAULT_PATH} on port {PORT}")
    server.serve_forever()
