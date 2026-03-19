#!/usr/bin/env python3
"""vault-viewer — Obsidian vault viewer + A2UI WebApp form server."""

import os, re, json, html, uuid, datetime
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

try:
    import mistune
    HAVE_MISTUNE = True
except ImportError:
    HAVE_MISTUNE = False

# ── Paths ──────────────────────────────────────────────────────────────────
VAULT_PATH   = Path(os.environ.get("VAULT_PATH",   "/data/obsidian/vault"))
REPORTS_DIR  = VAULT_PATH / "Bot" / "DailyReports"
WEBAPP_DIR   = Path(__file__).parent / "webapp"
BOT_DATA_DIR = VAULT_PATH / "Bot"
BOT_DATA_DIR.mkdir(parents=True, exist_ok=True)
FORMS_CACHE  = "/home/node/.openclaw/a2ui_forms.json"
PORT         = int(os.environ.get("PORT", 7080))

# ── CSS ───────────────────────────────────────────────────────────────────
CSS = """
*{box-sizing:border-box;margin:0;padding:0}
body{background:#1a1a2e;color:#e0e0e0;font-family:-apple-system,system-ui,sans-serif;padding:16px;max-width:700px;margin:0 auto}
h1{color:#a0a0c0;margin-bottom:16px;font-size:1.4em}h2{color:#c0c0e0;margin:16px 0 8px}
a{color:#6af;font-weight:600}
hr{border:0;border-top:1px solid #333;margin:16px 0}
.nav{margin-bottom:16px}
.nav a{color:#6af;text-decoration:none;font-size:0.9em}
.report-item{display:block;background:#252545;padding:14px 16px;border-radius:8px;margin-bottom:10px;text-decoration:none;color:inherit}
.report-item:hover{background:#2d2d5a}
.report-item h3{color:#d0d0f0;font-size:1.05em;margin-bottom:4px}
.report-item p{color:#888;font-size:0.85em}
.empty{color:#555;text-align:center;padding:40px}
.back{color:#6af;font-size:0.9em;margin-bottom:12px;display:inline-block}
.loading{text-align:center;padding:40px;color:#555}
*{box-sizing:border-box;margin:0;padding:0}
body{background:#1a1a2e;color:#e0e0e0;font-family:-apple-system,system-ui,sans-serif;padding:16px;max-width:600px;margin:0 auto}
.signal-symbol{font-size:1.8em;font-weight:700;color:#fff;margin-bottom:4px}
.badge{padding:3px 8px;border-radius:4px;font-size:0.85em;font-weight:600}
.badge-buy{background:rgba(92,184,122,0.2);color:#5cb87a}
.badge-sell{background:rgba(220,80,100,0.2);color:#dc5064}
.badge-neutral{background:rgba(100,100,100,0.2);color:#888}
.divider{border:0;border-top:1px solid #333;margin:12px 0}
.row{display:flex;justify-content:space-between;padding:6px 0;border-bottom:1px solid #2a2a3e}
.label{color:#888;font-size:0.9em}
.value{font-weight:600;font-size:1em}
.positive{color:#5cb87a}
.negative{color:#dc5064}
.actions{margin-top:20px;display:flex;gap:10px}
.btn{flex:1;padding:12px;border-radius:8px;border:none;cursor:pointer;font-weight:600;font-size:0.95em}
.btn-buy{background:rgba(92,184,122,0.2);color:#5cb87a}
.btn-skip{background:rgba(100,100,100,0.15);color:#888}
.meta{margin-top:12px;color:#555;font-size:0.8em;text-align:center}
"""

TELEGRAM_INIT = """
<script src="https://telegram.org/js/telegram-web-app.js"></script>
<script>
  const tg = window.Telegram && Telegram.WebApp;
  if (tg) { tg.ready(); tg.expand(); }
</script>
"""

def page(title, body, back=None):
    nav = (f'<div class="nav"><a href="{back}">&#8592; Back</a></div>' if back else "")
    return f"<!DOCTYPE html><html><head><meta charset='UTF-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>{html.escape(title)}</title><style>{CSS}</style></head><body>{TELEGRAM_INIT}{nav}{body}</body></html>"

def render_md(text):
    if HAVE_MISTUNE:
        return mistune.create_markdown(plugins=["table","strikethrough"], escape=False)(text)
    # Fallback
    lines = []
    for line in text.split("\n"):
        line = html.escape(line)
        line = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", line)
        line = re.sub(r"\*(.+?)\*", r"<em>\1</em>", line)
        line = re.sub(r"`(.+?)`", r"<code>\1</code>", line)
        m = re.match(r"^(#{1,3})\s+(.+)", line)
        if m: line = f"<h{len(m.group(1))}>{m.group(2)}</h{len(m.group(1))}>"
        elif re.match(r"^---+$", line): line = "<hr>"
        elif line.strip(): lines.append(f"<p>{line}</p>")
        else: lines.append("")
    return "<br>".join(lines)

def _fmt_num(n):
    if n is None: return "—"
    try:
        n = float(n)
        if n >= 1e12: return f"${n/1e12:.2f}T"
        if n >= 1e9: return f"${n/1e9:.2f}B"
        if n >= 1e6: return f"${n/1e6:.2f}M"
        return f"${n:.0f}"
    except: return str(n)

def _fmt_ts(ts):
    if not ts: return ""
    try:
        ts = ts.replace("Z","")
        dt = datetime.datetime.fromisoformat(ts)
        return (dt + datetime.timedelta(hours=5)).strftime("%Y-%m-%d %H:%M") + " (Tashkent)"
    except: return ts

class VH(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args): pass

    def send_html(self, content, status=200):
        content = content.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type","text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Cache-Control","no-store, no-cache, must-revalidate, proxy-revalidate, max-age=0")
        self.end_headers()
        self.wfile.write(content)

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path.lstrip("/")
        qs = parsed.query

        try:
            if path in ("", "index", "index.html"):
                self._serve_index()
            elif path == "tasks":
                self._serve_tasks()
            elif path.startswith("report/"):
                name = path[7:].rstrip("/")
                self._serve_report(name)
            elif path.startswith("a2ui/"):
                form_type = path[5:].split("?")[0]
                self._serve_a2ui(form_type, qs)
            elif path == "health":
                self.send_html("ok")
            else:
                self.send_html(page("Not Found", "<p>404 — Page not found.</p>"), status=404)
        except Exception as e:
            import traceback
            self.send_html(f"<pre>Error: {html.escape(str(e))}\n{html.escape(traceback.format_exc())}</pre>", status=500)

    def _serve_index(self):
        reports = []
        if REPORTS_DIR.exists():
            for f in sorted(REPORTS_DIR.glob("*.md"), reverse=True)[:20]:
                date = f.stem.replace("_"," ")
                content = f.read_text(encoding="utf-8", errors="ignore")[:120].replace("\n"," ")
                reports.append(
                    f"<a class='report-item' href='/report/{f.stem}'>"
                    f"<h3>{html.escape(date)}</h3><p>{html.escape(content)}…</p></a>"
                )
        body = "\n".join(reports) if reports else "<p class='empty'>No reports yet.</p>"
        self.send_html(page("Bot Reports", f"<h1>Bot Reports</h1><hr>" + body))

    def _serve_tasks(self):
        """Serve tasks from Bot/Tasks/ with tag-based filtering."""
        TASKS_DIR = Path(VAULT_PATH) / "Bot" / "Tasks"
        CSS = """
        *{box-sizing:border-box;margin:0;padding:0}
        body{font-family:ui-rounded,'Segoe UI',sans-serif;background:#0f0f1a;color:#d0d0e0;min-height:100vh;padding:20px}
        h1{color:#a0a0c0;margin-bottom:16px;font-size:1.4em}
        .filters{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:20px}
        .fbtn{padding:7px 16px;border-radius:8px;border:1px solid #3a3a5a;background:#1e1e38;color:#8888b0;cursor:pointer;font-size:0.9em;transition:all .2s}
        .fbtn.active,.fbtn:hover{background:#2a2a4a;color:#d0d0e0;border-color:#6a6aaa}
        .fbtn.all{background:#2a2a4a;color:#c8c8e0}
        .section{margin-bottom:24px;background:#1a1a32;border-radius:12px;overflow:hidden}
        .sec-title{padding:10px 16px;font-size:0.85em;font-weight:600;letter-spacing:.05em;background:#22223a;color:#7a7aaa}
        .sec-title.bot{background:#1e2a3a;color:#6a8aaa}
        .sec-title.work{background:#2a1e3a;color:#8a6aaa}
        .sec-title.personal{background:#1e3a2a;color:#6aaa8a}
        .task{padding:10px 16px;border-bottom:1px solid #252540;display:flex;align-items:flex-start;gap:10px;transition:background .15s}
        .task:last-child{border-bottom:none}
        .task:hover{background:#22223a}
        .cb{flex-shrink:0;margin-top:3px;width:16px;height:16px;border-radius:4px;border:2px solid #4a4a6a;cursor:pointer}
        .cb.done{border-color:#4a8a5a;background:#3a6a4a}
        .cb.done::after{content:'✓';color:#7aba8a;font-size:12px;display:flex;align-items:center;justify-content:center;height:100%}
        .cb.pending{border-color:#4a4a6a}
        .title{flex:1;font-size:0.95em;color:#c0c0d8;line-height:1.4}
        .task.done .title{text-decoration:line-through;color:#5a5a7a}
        .meta{display:flex;gap:8px;align-items:center;flex-wrap:wrap}
        .tag{font-size:0.75em;padding:2px 7px;border-radius:4px;background:#2a2a4a;color:#7070a0}
        .tag.bot{background:#1e2a3a;color:#6a8aaa}
        .tag.work{background:#2a1e3a;color:#8a6aaa}
        .tag.personal{background:#1e3a2a;color:#6aaa8a}
        .priority{font-size:0.75em}
        .priority.high{color:#e05060}
        .priority.medium{color:#e0a030}
        .priority.low{color:#50a050}
        .due{font-size:0.78em;color:#5a5a7a}
        .due.overdue{color:#e05050}
        .empty-sec{padding:16px;color:#4a4a6a;font-size:0.9em;font-style:italic}
        .back{color:#5a5a8a;font-size:0.85em;margin-bottom:16px}
        .back a{color:#7a7aaa;text-decoration:none}
        .back a:hover{text-decoration:underline}
        """
        TASKS_CSS = CSS

        # Parse tasks from all task files
        task_files = {
            "bot": TASKS_DIR / "bot-tasks.md",
            "work": TASKS_DIR / "work-tasks.md",
            "personal": TASKS_DIR / "personal-tasks.md",
        }

        all_tasks = []
        for kind, fpath in task_files.items():
            if not fpath.exists():
                continue
            try:
                content = fpath.read_text(encoding="utf-8", errors="ignore")
                for line in content.splitlines():
                    stripped = line.strip()
                    if not stripped.startswith("- ["):
                        continue
                    # Parse: - [ ] Title 🔴 📅 YYYY-MM-DD #tag1 #tag2
                    # or: - [x] Title #tag
                    done = "[x]" in stripped[:4]
                    title = stripped[stripped.index("]")+1:].strip()
                    # Remove priority emoji + due date
                    import re
                    title = re.sub(r'[\U0001F534-\U0001F53A]', '', title)  # colored circles
                    title = re.sub(r'\U0001F7E2|\U0001F7E1|\U0001F7E0', '', title)  # more circles
                    due_match = re.search(r'📅 (\d{4}-\d{2}-\d{2})', title)
                    due = due_match.group(1) if due_match else None
                    title = re.sub(r'📅 \d{4}-\d{2}-\d{2}', '', title).strip()
                    tags = re.findall(r'#([\w/-]+)', title)
                    title = re.sub(r'#[\w/-]+', '', title).strip()
                    # Determine kind
                    if "task/bot" in tags or kind == "bot":
                        t_kind = "bot"
                    elif "task/work" in tags or kind == "work":
                        t_kind = "work"
                    elif "task/personal" in tags or kind == "personal":
                        t_kind = "personal"
                    else:
                        t_kind = kind
                    # Priority
                    if "🔴" in stripped or "high" in tags:
                        priority = "high"
                    elif "🟡" in stripped or "medium" in tags:
                        priority = "medium"
                    elif "🟢" in stripped or "low" in tags:
                        priority = "low"
                    else:
                        priority = ""
                    all_tasks.append({
                        "done": done, "title": title, "due": due,
                        "tags": tags, "kind": t_kind, "priority": priority
                    })
            except Exception as e:
                pass

        # JS for filtering
        script = """
        <script>
        function filter(kind) {
            document.querySelectorAll('.fbtn').forEach(b => b.classList.remove('active'));
            if (kind === 'all') {
                document.querySelectorAll('.section').forEach(s => s.style.display = '');
                document.querySelectorAll('.fbtn')[0].classList.add('active');
            } else {
                document.querySelectorAll('.section').forEach(s => {
                    s.style.display = s.dataset.kind === kind ? '' : 'none';
                });
                document.querySelectorAll('.fbtn').forEach(b => {
                    b.classList.toggle('active', b.dataset.f === kind);
                });
            }
        }
        function filterDone(showDone) {
            document.querySelectorAll('.task').forEach(t => {
                t.style.display = (showDone || !t.classList.contains('done')) ? '' : 'none';
            });
        }
        </script>
        """

        # Build sections HTML
        sections_html = ""
        for kind, label, cls in [("bot","🤖 Бот","bot"),("work","💼 Работа","work"),("personal","🏠 Личное","personal")]:
            tasks = [t for t in all_tasks if t["kind"] == kind]
            pending = [t for t in tasks if not t["done"]]
            done_list = [t for t in tasks if t["done"]]
            if not tasks:
                continue
            tasks_html = ""
            for t in pending + done_list:
                due_str = f'<span class="due{' overdue' if t["due"] and t["due"] < "2026-03-19" else ''}">📅 {t["due"]}</span>' if t["due"] else ""
                pri = f'<span class="priority {t["priority"]}">{"🔴" if t["priority"]=="high" else "🟡" if t["priority"]=="medium" else "🟢"}</span>' if t["priority"] else ""
                tag_html = "".join(f'<span class="tag {t["kind"]}">#{tag}</span>' for tag in t["tags"][:3])
                tasks_html += f"""
                <div class="task{' done' if t['done'] else ''}">
                    <div class="cb {'done' if t['done'] else 'pending'}"></div>
                    <div class="title">{html.escape(t['title'])}</div>
                    <div class="meta">{pri}{due_str}{tag_html}</div>
                </div>"""
            if not tasks_html:
                tasks_html = '<div class="empty-sec">Нет задач</div>'
            sections_html += f'<div class="section" data-kind="{kind}"><div class="sec-title {cls}">{label} <span style="opacity:.6;font-weight:400">({len(pending)} / {len(tasks)})</span></div>{tasks_html}</div>'

        if not sections_html:
            sections_html = '<p style="color:#4a4a6a">Пока нет задач. Создай первую в Obsidian!</p>'

        pending_all = len([t for t in all_tasks if not t["done"]])
        done_all = len([t for t in all_tasks if t["done"]])
        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Tasks</title>
{script}
<style>{TASKS_CSS}</style>
</head>
<body>
<div class="back"><a href="/">← Bot Reports</a></div>
<h1>📋 Tasks <span style="font-size:.7em;color:#5a5a8a">({pending_all} active · {done_all} done)</span></h1>

<div class="filters">
  <button class="fbtn all active" onclick="filter('all')">Все</button>
  <button class="fbtn" data-f="bot" onclick="filter('bot')">🤖 Бот</button>
  <button class="fbtn" data-f="work" onclick="filter('work')">💼 Работа</button>
  <button class="fbtn" data-f="personal" onclick="filter('personal')">🏠 Личное</button>
  <button class="fbtn" onclick="filterDone(false)" style="margin-left:auto">Активные</button>
  <button class="fbtn" onclick="filterDone(true)">Все</button>
</div>

{sections_html}
</body></html>"""
        self.send_html(html_content)

    def _serve_report(self, name):
        path = REPORTS_DIR / f"{name}.md"
        if not path.exists():
            path = REPORTS_DIR / name
        if path.exists() and path.is_file():
            content = path.read_text(encoding="utf-8", errors="ignore")
            self.send_html(page(name.replace("_"," "), render_md(content), back="/"))
        else:
            self.send_html(page("Not Found", f"<p>Report <code>{html.escape(name)}</code> not found.</p>", back="/"), status=404)

    def _serve_a2ui(self, form_type, query):
        form_id = None
        form_data = None
        # Parse ?id= from query string
        for param in query.split("&"):
            if param.startswith("id="):
                form_id = param[3:]
                break
        # Load from forms cache
        if form_id and os.path.exists(FORMS_CACHE):
            try:
                with open(FORMS_CACHE) as f:
                    forms = json.load(f)
                form_data = forms.get(form_id)
            except: pass

        # Server-side render crypto-signal (Telegram WebApp JS doesn't execute)
        if form_type == "crypto-signal" and form_data:
            sig = form_data.get("formData") or form_data
            sym    = sig.get("symbol") or "—"
            direction = sig.get("direction") or sig.get("action") or "—"
            price  = sig.get("price") or sig.get("current_price") or "—"
            change = sig.get("price_change_pct")
            change_str = f"{change:+.2f}%" if change is not None else "—"
            volume = _fmt_num(sig.get("volume_24h"))
            mcap   = _fmt_num(sig.get("market_cap"))
            source = sig.get("source") or sig.get("exchange") or "Binance"
            ts_str = _fmt_ts(sig.get("timestamp") or sig.get("generatedAt") or "")
            reason = html.escape(sig.get("reason") or "")
            badge  = "&#128308; BUY" if direction=="BUY" else "&#128993; SELL" if direction=="SELL" else "Signal"
            bcls   = "buy" if direction=="BUY" else "sell" if direction=="SELL" else "neutral"
            dcol   = "#5cb87a" if direction=="BUY" else "#dc5064" if direction=="SELL" else "#ccc"
            pclass = "positive" if (change or 0) > 0 else "negative" if (change or 0) < 0 else ""
            reason_html = f"<p style='margin-top:10px;color:#888;font-size:0.88em'>{reason}</p>" if reason else ""
            html_content = f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Crypto Signal</title>
{TELEGRAM_INIT}
<style>{CSS}</style>
</head>
<body>
<h1 style="color:#a0a0c0;margin-bottom:12px">Crypto Signal</h1>
<div style="background:#252545;border-radius:10px;padding:16px">
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
    <span class="signal-symbol">{html.escape(sym)}</span>
    <span class="badge badge-{bcls}">{badge}</span>
  </div>
  <hr class="divider">
  <div class="row"><span class="label">Direction</span><span class="value" style="color:{dcol}">{html.escape(direction)}</span></div>
  <div class="row"><span class="label">Price</span><span class="value">{html.escape(str(price))}</span></div>
  <div class="row"><span class="label">24h Change</span><span class="value {pclass}">{change_str}</span></div>
  <div class="row"><span class="label">Volume (24h)</span><span class="value">{volume}</span></div>
  <div class="row"><span class="label">Market Cap</span><span class="value">{mcap}</span></div>
  <div class="row"><span class="label">Source</span><span class="value">{html.escape(source)}</span></div>
  {reason_html}
  <div class="meta">{html.escape(ts_str)}</div>
</div>
<div class="actions">
  <button class="btn btn-buy" onclick="location.href='bybit://trade/buy?symbol={sym}USDT'">&#128308; Buy</button>
  <button class="btn btn-skip">&#9194; Skip</button>
</div>
</body></html>"""
            self.send_html(html_content)
            return

        # Morning briefing: server-side rendered from morning.html template
        if form_type == "morning" and form_data:
            sig     = form_data.get("formData") or form_data
            greeting = sig.get("greeting", "Good morning")
            date_str = sig.get("date", "")
            prices   = sig.get("crypto", {})
            total_val = sig.get("portfolio", "—")
            pnl_html  = sig.get("pnl", "")
            updated   = sig.get("updated", "")
            icons = {"BTC":"B","ETH":"E","SOL":"S"}
            colors = {"BTC":"btc","ETH":"eth","SOL":"sol"}
            def _fp(p, coin):
                if coin == "BTC": return f"${p:,.0f}"
                if coin == "ETH": return f"${p:,.2f}"
                return f"${p:.2f}"
            crypto_rows = []
            for coin in ["BTC","ETH","SOL"]:
                if coin not in prices: continue
                pc = prices[coin]
                chg = pc.get("chg", 0)
                chg_cls = "positive" if chg >= 0 else "negative"
                chg_str = f"+{chg:.2f}%" if chg >= 0 else f"{chg:.2f}%"
                crypto_rows.append(
                    f'''
    <div class="coin-row">
      <div class="coin-icon {colors[coin]}">{icons[coin]}</div>
      <div><div class="coin-name">{coin}</div><div class="coin-sym">{coin}USDT</div></div>
      <div class="coin-data">
        <div class="coin-price">{_fp(pc.get("price",0),coin)}</div>
        <span class="coin-chg {chg_cls}">{chg_str}</span>
      </div>
    </div>''')
            crypto_html = "\n".join(crypto_rows) if crypto_rows else '<div class="row"><span class="label">No data</span></div>'
            template_path = WEBAPP_DIR / "morning.html"
            if template_path.exists():
                tpl = template_path.read_text(encoding="utf-8")
                tpl = tpl.replace("{{GREETING}}", html.escape(greeting))
                tpl = tpl.replace("{{DATE}}", html.escape(date_str))
                tpl = tpl.replace("{{CRYPTO_ROWS}}", crypto_html)
                tpl = tpl.replace("{{TOTAL_VALUE}}", html.escape(str(total_val)))
                tpl = tpl.replace("{{PNL}}", pnl_html)
                tpl = tpl.replace("{{UPDATED}}", html.escape(updated))
                self.send_html(tpl)
                return
            else:
                self.send_html(page("Morning Briefing","<p>morning.html template not found.</p>"), status=404)
                return

        # Fallback: simple JSON display
        if form_data:
            self.send_html(page(
                f"A2UI Form: {form_type}",
                f"<h1>{html.escape(form_type.title())}</h1>"
                f"<pre style='background:#252545;padding:16px;border-radius:8px;overflow:auto'>"
                f"{html.escape(json.dumps(form_data, indent=2, ensure_ascii=False))}</pre>",
                back="/"
            ))
        else:
            self.send_html(page(
                "A2UI Form",
                f"<p class='empty'>Form <code>{html.escape(form_id or '')}</code> not found. "
                f"Form data may have expired.</p>",
                back="/"
            ), status=404)

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path.lstrip("/") == "forms" and parsed.query.startswith("id="):
            form_id = parsed.query[3:]
            cl = int(self.headers.get("Content-Length", 0))
            data = self.rfile.read(cl)
            try:
                fd = json.loads(data)
                forms = {}
                if os.path.exists(FORMS_CACHE):
                    try: forms = json.load(open(FORMS_CACHE))
                    except: pass
                forms[form_id] = fd
                with open(FORMS_CACHE, "w") as f:
                    json.dump(forms, f, ensure_ascii=False)
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"ok": True}).encode())
            except Exception as e:
                self.send_response(400)
                self.send_header("Content-Type", "text/plain")
                self.end_headers()
                self.wfile.write(str(e).encode())
        else:
            self.send_error(404)

if __name__ == "__main__":
    print(f"[vault-viewer] mistune={'OK' if HAVE_MISTUNE else 'missing'}")
    print(f"[vault-viewer] vault={VAULT_PATH} reports={REPORTS_DIR} forms={FORMS_CACHE}")
    HTTPServer(("0.0.0.0", PORT), VH).serve_forever()
