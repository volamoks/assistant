#!/usr/bin/env python3
"""BTC Price Monitor — dynamic alerts based on 24h % change

Features:
- Dynamic thresholds based on 24h % change
- Telegram notifications for triggered alerts
- Price logging to CSV
- State management to prevent duplicate alerts
"""

import os
import sys
import json
import requests
import logging
from datetime import datetime

# Add skills path for imports
sys.path.insert(0, '/home/node/.openclaw/skills')

STATE_FILE = os.path.expanduser('~/.openclaw/skills/crypto_monitor/state.json')
LOG_FILE = os.path.expanduser('~/.openclaw/skills/crypto_monitor/btc_alert.log')

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Dynamic thresholds — keyed by date+level, so they reset daily
ALERT_THRESHOLDS = {
    'extreme_dip': {'pct': -10.0, 'label': '🆘 EXTREME DIP',  'action': 'Major DCA zone'},
    'hot_buy':     {'pct':  -5.0, 'label': '🔥 DIP ALERT',    'action': 'Strong buy opportunity'},
    'mild_dip':    {'pct':  -3.0, 'label': '💧 Mild dip',     'action': 'Consider adding'},
    'breakout':    {'pct':  +5.0, 'label': '🚀 BREAKOUT',     'action': 'Momentum signal'},
}


def get_btc_data():
    """Get BTC price + 24h data from public Bybit endpoint (no auth needed)"""
    url = 'https://api.bybit.com/v5/market/tickers'
    params = {'category': 'spot', 'symbol': 'BTCUSDT'}
    try:
        resp = requests.get(url, params=params, timeout=10)
        data = resp.json()
        if data.get('retCode') == 0:
            t = data['result']['list'][0]
            return {
                'price':      float(t['lastPrice']),
                'pct_24h':    float(t['price24hPcnt']) * 100,
                'high_24h':   float(t['highPrice24h']),
                'low_24h':    float(t['lowPrice24h']),
                'volume_24h': float(t['volume24h']),
            }
    except Exception as e:
        print(f'Error fetching BTC data: {e}')
    return None


def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return json.load(f)
    return {}


def save_state(state):
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)


def check_levels(btc):
    """Check BTC price against alert thresholds."""
    today = datetime.now().strftime('%Y-%m-%d')
    state = load_state()
    triggered = []

    for name, threshold in ALERT_THRESHOLDS.items():
        key = f'{today}_{name}'
        if state.get(key):
            logger.debug(f"Alert {key} already triggered today, skipping")
            continue
        pct = threshold['pct']
        if (pct < 0 and btc['pct_24h'] <= pct) or (pct > 0 and btc['pct_24h'] >= pct):
            triggered.append((name, threshold))
            state[key] = True
            logger.info(f"Alert triggered: {name} ({threshold['label']})")

    save_state(state)
    return triggered


def send_telegram_alert(btc: dict, alert_name: str, threshold: dict):
    """
    Send alert to Telegram using the unified notification module.
    
    Args:
        btc: BTC price data dict
        alert_name: Name of the triggered alert
        threshold: Threshold config dict
    """
    try:
        from telegram.notify import TelegramNotifier
        
        # Initialize notifier (uses env vars TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID)
        notifier = TelegramNotifier()
        
        # Format message
        direction = "📉" if threshold['pct'] < 0 else "📈"
        message = f"""
{direction} *{threshold['label']}*

💰 *BTC Price:* `${btc['price']:,.0f}`
📊 *24h Change:* `{btc['pct_24h']:+.2f}%`
🎯 *Threshold:* `{threshold['pct']:+.1f}%`

📈 *24h High:* `${btc['high_24h']:,.0f}`
📉 *24h Low:* `${btc['low_24h']:,.0f}`

💡 *Action:* {threshold['action']}

⏰ _{datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}_
"""
        
        # Send message
        notifier.send(message.strip())
        logger.info(f"Telegram alert sent: {alert_name}")
        
    except ImportError:
        logger.warning("Telegram notifier not available, skipping notification")
    except Exception as e:
        logger.error(f"Failed to send Telegram alert: {e}")


def main():
    """Main entry point for BTC alert monitor."""
    logger.info("Starting BTC price check...")
    
    btc = get_btc_data()
    if not btc:
        logger.error('Failed to fetch BTC data')
        print('ERROR: Failed to fetch BTC data')
        return

    logger.info(f"BTC: ${btc['price']:,.0f}, 24h: {btc['pct_24h']:+.2f}%")
    print(f"BTC: ${btc['price']:,.0f}  24h: {btc['pct_24h']:+.2f}%  "
          f"H: ${btc['high_24h']:,.0f}  L: ${btc['low_24h']:,.0f}")

    alerts = check_levels(btc)
    
    if alerts:
        logger.info(f"Triggered {len(alerts)} alert(s)")
        for name, threshold in alerts:
            print(f"\n{threshold['label']} — {threshold['action']}")
            print(f"  BTC dropped {btc['pct_24h']:+.1f}% → ${btc['price']:,.0f}")
            
            # Send Telegram notification
            send_telegram_alert(btc, name, threshold)
    else:
        logger.info(f"No alert: 24h change ({btc['pct_24h']:+.1f}%) within normal range")
        print(f"No alert: 24h change ({btc['pct_24h']:+.1f}%) within normal range")

    # Append to price log
    log_file = os.path.expanduser('~/.openclaw/skills/crypto_monitor/price_log.csv')
    write_header = not os.path.exists(log_file)
    with open(log_file, 'a') as f:
        if write_header:
            f.write('timestamp,price,pct_24h\n')
        f.write(f"{datetime.now().isoformat()},{btc['price']},{btc['pct_24h']:.2f}\n")
    
    logger.info("BTC price check completed")


if __name__ == '__main__':
    main()
