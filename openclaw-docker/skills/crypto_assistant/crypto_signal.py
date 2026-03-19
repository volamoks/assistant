#!/usr/bin/env python3
"""
Crypto Signal — Proactive buy opportunity detector
Sends Telegram alerts with inline Bybit buttons when conditions align.
Only fires when conditions are met — otherwise silent.
"""

import os, sys, json, subprocess, urllib.request, urllib.parse

SKILLS_DIR = os.path.expanduser('~/.openclaw/skills')
BYBIT_SCRIPT = f"{SKILLS_DIR}/crypto_assistant/bybit_read.py"
CHAT_ID = "6053956251"
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")


def run_json(script, args, timeout=25):
    try:
        r = subprocess.run(['python3', script]+args, capture_output=True, text=True, timeout=timeout)
        if r.returncode == 0 and r.stdout.strip():
            return json.loads(r.stdout)
    except Exception:
        pass
    return {}


def get_prices():
    market = run_json(BYBIT_SCRIPT, ['--market', '--json'])
    out = {}
    targets = {'BTCUSDT':'BTC','ETHUSDT':'ETH','SOLUSDT':'SOL'}
    for t in market.get('tickers', []):
        sym = t.get('symbol','')
        if sym in targets:
            out[targets[sym]] = {
                'price': float(t.get('last_price', 0)),
                'pct_24h': float(t.get('price_24h_change', 0)),
            }
    return out


def get_portfolio_value():
    data = run_json(BYBIT_SCRIPT, ['--json'])
    try:
        return float(data.get('analysis',{}).get('total_portfolio_value', 0))
    except (TypeError, ValueError):
        return 0.0


def check_signal(prices):
    """Return signal dict or None"""
    candidates = []

    for coin, thresh in [('BTC',-3.0),('ETH',-4.0),('SOL',-5.0)]:
        if coin in prices:
            p = prices[coin]
            if p['pct_24h'] <= thresh:
                candidates.append({
                    'action':'BUY', 'coin':coin,
                    'pct_24h':p['pct_24h'], 'price':p['price'],
                    'urgency':'high' if p['pct_24h']<=thresh-2 else 'medium',
                })

    for coin, thresh in [('BTC',5.0),('ETH',7.0),('SOL',10.0)]:
        if coin in prices:
            p = prices[coin]
            if p['pct_24h'] >= thresh:
                candidates.append({
                    'action':'TAKE_PROFIT', 'coin':coin,
                    'pct_24h':p['pct_24h'], 'price':p['price'],
                    'urgency':'high',
                })

    if not candidates:
        return None

    buys = [c for c in candidates if c['action']=='BUY']
    return min(buys, key=lambda x: x['pct_24h']) if buys else candidates[0]


def format_signal(signal, portfolio_value):
    coin = signal['coin']
    action = signal['action']
    pct = signal['pct_24h']
    price = signal['price']
    urgency = signal['urgency']

    if price >= 1000:
        ps = f"${price:,.0f}"
    elif price >= 1:
        ps = f"${price:,.2f}"
    else:
        ps = f"${price:.4f}"

    emoji = "📉" if pct < 0 else "📈"

    if action == 'BUY':
        header = f"🚀 Crypto Signal — {coin} падает\n\n"
        body = (f"{coin} {ps}  {emoji} {pct:+.1f}%\n\n"
                f"💡 Докупить {coin}\n"
                f"   {'Сильное падение — хорошая точка входа' if urgency=='high' else 'Заметное снижение — умеренная точка'}\n")
    else:
        header = f"💰 Crypto Signal — {coin} растёт\n\n"
        body = (f"{coin} {ps}  {emoji} {pct:+.1f}%\n\n"
                f"💡 Зафиксировать часть {coin}\n"
                f"   Хороший рост, рассмотри продажу\n")

    if portfolio_value > 0:
        body += f"\n💰 Портфель: ${portfolio_value:,.0f}"

    # Build inline keyboard rows
    keyboard = []
    if action == 'BUY':
        for amt in [50, 100, 200]:
            keyboard.append([{
                "text": f"📲 Купить {coin} ${amt}",
                "url": f"https://www.bybit.com/trade/spot/{coin}USDT"
            }])
    else:
        keyboard.append([{
            "text": f"📲 Продать {coin}",
            "url": f"https://www.bybit.com/trade/spot/{coin}USDT"
        }])

    keyboard.append([{"text": "Пропустить", "callback_data": "crypto_signal_skip"}])

    return header + body, {"inline_keyboard": keyboard}


def tg_send_message(text, reply_markup=None):
    """Send via Telegram Bot API directly"""
    if not BOT_TOKEN:
        return False

    payload = {
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True,
    }
    if reply_markup:
        payload["reply_markup"] = json.dumps(reply_markup)

    try:
        data = urllib.parse.urlencode(payload).encode()
        req = urllib.request.Request(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            data=data
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read()).get("ok", False)
    except Exception as e:
        print(f"Telegram error: {e}", file=sys.stderr)
        return False


def main():
    prices = get_prices()
    if not prices:
        sys.exit(0)

    portfolio_value = get_portfolio_value()
    signal = check_signal(prices)
    if not signal:
        sys.exit(0)

    msg, keyboard = format_signal(signal, portfolio_value)

    if tg_send_message(msg, keyboard):
        print(f"Signal sent: {signal['action']} {signal['coin']} {signal['pct_24h']:+.1f}%")
    else:
        print("Send failed", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
