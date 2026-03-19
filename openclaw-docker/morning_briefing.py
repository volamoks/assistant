#!/usr/bin/env python3
"""
Morning Briefing — красивая WebApp утренняя сводка
Запускать каждое утро (через cron или вручную)
"""

import os, sys, json, datetime, urllib.request, subprocess
from pathlib import Path

# Paths
SYS_DIR   = Path("/data/bot/openclaw-docker")
VAULT_DIR = Path("/data/obsidian/vault")
FORMS_CACHE = Path("/home/node/.openclaw/a2ui_forms.json")
WEBAPP_BASE = "https://vault.volamoks.store/a2ui/morning"

# ── Bybit prices ──────────────────────────────────────────────────────────────
def get_bybit_prices():
    try:
        url = "https://api.bybit.com/v5/market/tickers?category=spot"
        with urllib.request.urlopen(url, timeout=8) as r:
            data = json.loads(r.read())
        result = {}
        for t in data.get("result", {}).get("list", []):
            sym = t.get("symbol", "")
            price = float(t.get("lastPrice", 0))
            chg   = float(t.get("price24hPcnt", 0)) * 100
            if sym not in ("BTCUSDT","ETHUSDT","SOLUSDT"): continue
            coin = {"BTCUSDT":"BTC","ETHUSDT":"ETH","SOLUSDT":"SOL"}[sym]
            result[coin] = {"price": price, "chg": chg}
        return result
    except Exception as e:
        print(f"[morning] Bybit prices error: {e}")
        return {}

# ── Bybit portfolio ─────────────────────────────────────────────────────────
def get_bybit_portfolio():
    try:
        script = f"{os.environ.get('HOME','/root')}/.openclaw/skills/crypto_assistant/bybit_read.py"
        r = subprocess.run(["python3", script, "--json"], capture_output=True, text=True, timeout=20)
        if r.returncode == 0:
            return json.loads(r.stdout)
    except Exception as e:
        print(f"[morning] Bybit portfolio error: {e}")
    return {}

# ── Format helpers ────────────────────────────────────────────────────────────
def fmt_price(price, coin):
    if coin == "BTC": return f"${price:,.0f}"
    if coin == "ETH": return f"${price:,.2f}"
    return f"${price:.2f}"

def fmt_chg(chg):
    sign = "+" if chg >= 0 else ""
    cls  = "positive" if chg >= 0 else "negative"
    return f'<span class="coin-chg {cls}">{sign}{chg:.2f}%</span>'

# ── Build crypto rows HTML ─────────────────────────────────────────────────────
def build_crypto_rows(prices):
    icons = {"BTC":"B","ETH":"E","SOL":"S"}
    colors = {"BTC":"btc","ETH":"eth","SOL":"sol"}
    rows = []
    for coin in ["BTC","ETH","SOL"]:
        if coin not in prices: continue
        p = prices[coin]
        chg_cls = "positive" if p["chg"] >= 0 else "negative"
        rows.append(f'''    <div class="coin-row">
      <div class="coin-icon {colors[coin]}">{icons[coin]}</div>
      <div>
        <div class="coin-name">{coin}</div>
        <div class="coin-sym">{coin}USDT</div>
      </div>
      <div class="coin-data">
        <div class="coin-price">{fmt_price(p["price"], coin)}</div>
        {fmt_chg(p["chg"])}
      </div>
    </div>''')
    return "\n".join(rows) if rows else '<div class="row"><span class="label">Нет данных</span></div>'

# ── Build portfolio rows HTML ─────────────────────────────────────────────────
def build_portfolio_rows(portfolio):
    total = portfolio.get("analysis",{}).get("total_portfolio_value", 0)
    pnl   = portfolio.get("analysis",{}).get("total_pnl_pct", 0)
    total_str = f"${total:,.2f}" if total else "—"
    pnl_str   = f"{pnl:+.2f}% P/L" if pnl else ""
    pnl_cls   = "positive" if (pnl or 0) >= 0 else "negative"
    return total_str, f'<span class="pnl {pnl_cls}">{pnl_str}</span>'

# ── Generate morning form and return button ───────────────────────────────────
def generate_morning_button():
    prices   = get_bybit_prices()
    portfolio = get_bybit_portfolio()
    now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=5)))  # Tashkent

    greeting = "Good morning" if 5 <= now.hour < 12 else \
               "Good afternoon" if 12 <= now.hour < 18 else "Good evening"
    date_str = now.strftime("%A, %B %-d, %Y")

    crypto_rows, total_val, pnl_html = build_crypto_rows(prices), "", ""
    if portfolio:
        total_val, pnl_html = build_portfolio_rows(portfolio)

    # If no portfolio data yet, use placeholders
    if not total_val:
        total_val = "Loading..."
        pnl_html = '<span class="pnl" style="color:#555">PNL unavailable</span>'

    # Fallback crypto rows if no data
    if not crypto_rows.strip():
        crypto_rows = '<div class="row"><span class="label">No data</span></div>'

    form_data = {
        "type": "morning_briefing",
        "greeting": greeting,
        "date": date_str,
        "crypto": prices,
        "portfolio": total_val.replace("$","").replace(",",""),
        "pnl": pnl_html,
        "source": "Bybit",
        "updated": now.strftime("%H:%M"),
    }

    form_id = _write_form(form_data)
    url = f"{WEBAPP_BASE}?id={form_id}"
    return {
        "text": "📊 Morning Briefing",
        "web_app": {"url": url},
        "form_id": form_id,
        "prices": prices,
        "portfolio": total_val,
    }


def _write_form(form_data):
    form_id = datetime.datetime.now().strftime("%m%d%H%M%S")
    forms = {}
    if FORMS_CACHE.exists():
        try:
            with open(FORMS_CACHE) as f:
                forms = json.load(f)
        except: pass
    forms[form_id] = {
        "formType": "morning",
        "formData": form_data,
        "createdAt": datetime.datetime.utcnow().isoformat() + "Z",
    }
    with open(FORMS_CACHE, "w") as f:
        json.dump(forms, f, ensure_ascii=False)
    # Also sync to vault-viewer volume
    _sync_to_vault_viewer(FORMS_CACHE)
    return form_id


def _sync_to_vault_viewer(src_path):
    """Copy forms cache to vault-viewer docker volume"""
    try:
        import docker
        client = docker.from_env()
        container = client.containers.get("vault-viewer")
        with open(src_path, "rb") as f:
            container.put_archive("/", [("a2ui_forms.json", 0o644, 0, f.read())])
    except Exception as e:
        print(f"[morning] Sync to vault-viewer failed: {e}")
        # Fallback: use docker cp
        try:
            subprocess.run(["docker", "cp", src_path, "vault-viewer:/home/node/.openclaw/a2ui_forms.json"],
                         capture_output=True, timeout=10)
        except: pass


if __name__ == "__main__":
    result = generate_morning_button()
    print(json.dumps(result, ensure_ascii=False, indent=2))
