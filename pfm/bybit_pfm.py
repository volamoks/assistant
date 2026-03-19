#!/usr/bin/env python3
"""
bybit_pfm.py — sync Bybit portfolio snapshots & trade history → Sure PFM

Usage:
    python3 bybit_pfm.py              # sync all (valuations + recent trades)
    python3 bybit_pfm.py --portfolio  # portfolio snapshot only (valuations)
    python3 bybit_pfm.py --trades     # trade history only
    python3 bybit_pfm.py --trades --days 30  # last 30 days of trades

Sure account structure:
    - One "Crypto" account per coin held on Bybit (e.g. "Bybit BTC", "Bybit USDT")
    - Valuations updated on each sync (portfolio balance over time)
    - Realized PnL trades pushed as income/expense transactions
"""
import sys
import os
import json
import requests
import argparse
from datetime import datetime, timedelta
from pathlib import Path

# ── path setup ─────────────────────────────────────────────────────────────────
BASE = Path(__file__).parent
DOCKER_DIR = BASE.parent / "openclaw-docker"
SKILLS_DIR = DOCKER_DIR / "skills"
sys.path.insert(0, str(SKILLS_DIR))
sys.path.insert(0, str(DOCKER_DIR))

# ── env ────────────────────────────────────────────────────────────────────────
def _env(key: str, default: str = "") -> str:
    val = os.environ.get(key, "")
    if val:
        return val
    for env_path in [DOCKER_DIR / ".env", BASE.parent / ".env"]:
        try:
            for line in env_path.read_text().splitlines():
                if line.strip().startswith(f"{key}="):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
        except Exception:
            pass
    return default

SURE_URL     = _env("SURE_URL", "http://localhost:3020")
SURE_API_KEY = _env("SURE_API_KEY", "")
BYBIT_KEY    = _env("BYBIT_API")
BYBIT_SECRET = _env("BYBIT_API_SECRET")

HEADERS = lambda: {"X-Api-Key": SURE_API_KEY, "Content-Type": "application/json", "Accept": "application/json"}

# ── Sure API helpers ────────────────────────────────────────────────────────────

def sure_get(path: str, params: dict = None) -> dict:
    r = requests.get(f"{SURE_URL}/api/v1{path}", headers=HEADERS(), params=params, timeout=10)
    r.raise_for_status()
    return r.json()

def sure_post(path: str, payload: dict) -> dict:
    r = requests.post(f"{SURE_URL}/api/v1{path}", headers=HEADERS(), json=payload, timeout=10)
    r.raise_for_status()
    return r.json()

def _create_account_via_rails(name: str, currency: str = "USD") -> bool:
    """Create a Sure account via docker exec rails runner (bypasses read-only API)."""
    import subprocess
    script = (
        f"family = Family.first; "
        f"unless Account.exists?(name: '{name}', family: family); "
        f"  Account.create!(name: '{name}', family: family, "
        f"    accountable: Crypto.new, currency: '{currency}', balance: 0, status: 'active'); "
        f"  puts 'created'; "
        f"end"
    )
    result = subprocess.run(
        ["docker", "exec", "sure", "bin/rails", "runner", script],
        capture_output=True, text=True, timeout=15
    )
    return result.returncode == 0

def _all_accounts() -> list:
    """Fetch all Sure accounts across pages."""
    accounts, page = [], 1
    while True:
        resp = sure_get("/accounts", {"page": page, "per_page": 100})
        batch = resp.get("accounts", [])
        accounts.extend(batch)
        pagination = resp.get("pagination", {})
        if page >= pagination.get("total_pages", 1):
            break
        page += 1
    return accounts

def get_or_create_crypto_account(name: str, currency: str = "USD") -> str:
    """Return Sure account ID by name, creating via Rails if missing."""
    for acc in _all_accounts():
        if acc.get("name") == name:
            return acc["id"]

    print(f"  🆕 Creating Sure account: {name}")
    if _create_account_via_rails(name, currency):
        for acc in _all_accounts():
            if acc.get("name") == name:
                return acc["id"]

    raise RuntimeError(f"Failed to create Sure account '{name}'")

def push_valuation(account_id: str, value_usd: float, date: str) -> bool:
    """Push a balance snapshot (valuation) for an account."""
    try:
        sure_post("/valuations", {
            "valuation": {
                "account_id": account_id,
                "date": date,
                "amount": round(value_usd, 2),
            }
        })
        return True
    except Exception as e:
        print(f"  ⚠️  Valuation error: {e}")
        return False

def transaction_exists(account_id: str, imported_id: str) -> bool:
    try:
        txs = sure_get("/transactions", {"account_id": account_id, "search": imported_id, "per_page": 5})
        return any(imported_id in (t.get("notes") or "") for t in txs.get("transactions", []))
    except Exception:
        return False

def push_trade(account_id: str, trade: dict) -> bool:
    """Push a realized PnL trade as a Sure transaction."""
    imported_id = f"bybit-{trade['symbol']}-{trade['orderId']}"
    if transaction_exists(account_id, imported_id):
        return True  # already synced

    pnl = trade.get("closedPnl", 0)
    nature = "income" if pnl >= 0 else "expense"
    try:
        sure_post("/transactions", {
            "transaction": {
                "account_id": account_id,
                "date": trade["date"],
                "amount": abs(pnl),
                "currency": "USD",
                "name": f"{trade['symbol']} {trade['side']}",
                "notes": f"{imported_id} | qty={trade.get('qty')} @ {trade.get('avgExitPrice')}",
                "nature": nature,
            }
        })
        emoji = "📈" if pnl >= 0 else "📉"
        print(f"  {emoji} Trade: {trade['symbol']} PnL=${pnl:+.2f} → Sure ({nature})")
        return True
    except Exception as e:
        print(f"  ⚠️  Trade push error: {e}")
        return False

# ── Bybit data fetchers ─────────────────────────────────────────────────────────

def get_bybit_portfolio():
    """Fetch wallet balance from Bybit via bybit_read module."""
    try:
        from bybit_integration.src.client import BybitClient
    except ImportError:
        try:
            sys.path.insert(0, str(SKILLS_DIR / "bybit_integration" / "src"))
            from client import BybitClient
        except ImportError:
            print("  ❌ Cannot import BybitClient — check skills/bybit_integration path")
            return None

    client = BybitClient()
    wallet = client.get_wallet_balance()
    if "list" not in wallet or not wallet["list"]:
        return None

    coins = []
    for coin in wallet["list"][0].get("coin", []):
        usd_val = float(coin.get("usdValue", 0))
        if usd_val > 0.01:
            coins.append({
                "symbol": coin["coin"],
                "balance": float(coin.get("walletBalance", 0)),
                "usd_value": usd_val,
            })
    return coins

def get_bybit_closed_pnl(symbol: str = None, days: int = 7):
    """Fetch closed PnL trade history from Bybit."""
    import hmac, hashlib, time as tmod, urllib.parse

    api_key    = BYBIT_KEY
    api_secret = BYBIT_SECRET
    base_url   = "https://api.bybit.com"

    ts = str(int(tmod.time() * 1000))
    params = {"category": "linear", "limit": 50}
    if symbol:
        params["symbol"] = symbol

    sorted_params = "&".join(f"{k}={v}" for k, v in sorted(params.items()))
    sign_str = ts + api_key + "5000" + sorted_params
    signature = hmac.new(api_secret.encode(), sign_str.encode(), hashlib.sha256).hexdigest()

    headers = {
        "X-BAPI-API-KEY": api_key,
        "X-BAPI-TIMESTAMP": ts,
        "X-BAPI-SIGN": signature,
        "X-BAPI-RECV-WINDOW": "5000",
    }

    r = requests.get(f"{base_url}/v5/position/closed-pnl",
                     headers=headers, params=params, timeout=10)
    r.raise_for_status()
    data = r.json()

    cutoff = datetime.now() - timedelta(days=days)
    trades = []
    for item in data.get("result", {}).get("list", []):
        ts_ms = int(item.get("updatedTime", 0))
        trade_dt = datetime.fromtimestamp(ts_ms / 1000)
        if trade_dt < cutoff:
            continue
        trades.append({
            "symbol":       item.get("symbol"),
            "side":         item.get("side"),
            "qty":          item.get("qty"),
            "avgExitPrice": item.get("avgExitPrice"),
            "closedPnl":    float(item.get("closedPnl", 0)),
            "orderId":      item.get("orderId"),
            "date":         trade_dt.strftime("%Y-%m-%d"),
        })
    return trades

# ── Main sync ───────────────────────────────────────────────────────────────────

def sync_portfolio():
    print("📊 Syncing Bybit portfolio → Sure valuations...")
    coins = get_bybit_portfolio()
    if not coins:
        print("  ⚠️  No Bybit portfolio data")
        return

    today = datetime.now().strftime("%Y-%m-%d")
    total = sum(c["usd_value"] for c in coins)
    print(f"  💼 Total: ${total:,.2f}")

    for coin in coins:
        acc_name = f"Bybit {coin['symbol']}"
        acc_id   = get_or_create_crypto_account(acc_name, "USD")
        pushed   = push_valuation(acc_id, coin["usd_value"], today)
        status   = "✅" if pushed else "⚠️"
        print(f"  {status} {acc_name}: {coin['balance']:.4f} = ${coin['usd_value']:,.2f}")

def sync_trades(days: int = 7):
    print(f"📈 Syncing Bybit trades (last {days}d) → Sure transactions...")
    try:
        trades = get_bybit_closed_pnl(days=days)
    except Exception as e:
        print(f"  ❌ Bybit API error: {e}")
        return

    if not trades:
        print("  ✅ No new trades")
        return

    # Group by symbol → one Sure account per symbol
    by_symbol: dict = {}
    for t in trades:
        by_symbol.setdefault(t["symbol"], []).append(t)

    for symbol, symbol_trades in by_symbol.items():
        # Use USDT account for PnL (settled in USDT)
        acc_name = "Bybit USDT"
        acc_id   = get_or_create_crypto_account(acc_name, "USD")
        for trade in symbol_trades:
            push_trade(acc_id, trade)

    print(f"  ✅ Synced {len(trades)} trade(s)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sync Bybit → Sure PFM")
    parser.add_argument("--portfolio", action="store_true", help="Sync portfolio valuations")
    parser.add_argument("--trades",    action="store_true", help="Sync closed PnL trades")
    parser.add_argument("--days",      type=int, default=7, help="Days of trade history (default: 7)")
    args = parser.parse_args()

    if not SURE_API_KEY:
        print("❌ SURE_API_KEY not set in .env")
        sys.exit(1)

    run_all = not args.portfolio and not args.trades

    if args.portfolio or run_all:
        sync_portfolio()
    if args.trades or run_all:
        sync_trades(days=args.days)
