#!/usr/bin/env python3
"""
Crypto Assistant - Proactive Monitor
Checks portfolio and sentiment conditions, sends alerts when triggered.
"""

import os
import sys
import json
import subprocess
from datetime import datetime
from typing import Dict, Any, Optional

# Add paths for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.expanduser('~/.openclaw/skills'))


def run_script(script_path: str, args: list, timeout: int = 20) -> Optional[Dict]:
    """Run a script and return JSON output"""
    try:
        cmd = ['python3', script_path] + args
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        if result.returncode == 0 and result.stdout.strip():
            return json.loads(result.stdout)
        return None
    except subprocess.TimeoutExpired:
        print(f"Timeout running {script_path} (>{timeout}s)", file=sys.stderr)
        return None
    except Exception as e:
        print(f"Error running {script_path}: {e}", file=sys.stderr)
        return None


def get_portfolio_data() -> Optional[Dict]:
    """Get portfolio data from bybit_read.py"""
    script_path = os.path.expanduser('~/.openclaw/skills/crypto_assistant/bybit_read.py')
    return run_script(script_path, ['--json'])


def get_sentiment_data() -> Optional[Dict]:
    """Get sentiment data from reddit_scan.py"""
    script_path = os.path.expanduser('~/.openclaw/skills/crypto_assistant/reddit_scan.py')
    return run_script(script_path, ['--signals', '--json'])


def check_conditions(portfolio: Dict, sentiment: Dict) -> Dict[str, Any]:
    """
    Check all alert conditions
    Returns dict with triggered conditions and details
    """
    conditions = {}
    
    # Extract portfolio data
    analysis = portfolio.get('analysis', {})
    total_value = analysis.get('total_portfolio_value', 0)
    allocation = analysis.get('allocation', {})
    stablecoins_pct = analysis.get('stablecoins_percentage', 0)
    stablecoins_value = analysis.get('stablecoins_value', 0)
    coins = portfolio.get('balance', {}).get('coins', [])
    
    # Extract sentiment data
    sentiment_score = sentiment.get('sentiment_score', 0)
    opportunities = sentiment.get('opportunities', [])
    
    # Get trending tokens from sentiment
    trending_tokens = [opp.get('token', '').upper() for opp in opportunities if opp.get('type') == 'TRENDING']
    
    # Condition 1: High sentiment + Low portfolio position
    # sentiment > 0.3 AND token_in_trend AND user_position < 5%
    if sentiment_score > 0.3 and trending_tokens:
        for token in trending_tokens[:3]:  # Check top 3 trending
            token_normalized = token.replace('BTC', 'BTC').replace('ETH', 'ETH').replace('SOL', 'SOL')
            # Find token in allocation
            user_position_pct = 0
            for alloc_token, pct in allocation.items():
                if token_normalized in alloc_token or alloc_token in token_normalized:
                    user_position_pct = pct
                    break
            
            if user_position_pct < 5:
                conditions['high_sentiment_low_portfolio'] = {
                    'token': token,
                    'sentiment': sentiment_score,
                    'user_position_pct': user_position_pct,
                    'user_position_usd': total_value * (user_position_pct / 100),
                    'stablecoins_usd': stablecoins_value,
                    'stablecoins_pct': stablecoins_pct
                }
                break  # Only alert on first match
    
    # Condition 2: Fear bottom
    # sentiment < -0.3 AND stablecoins > 50% of portfolio
    if sentiment_score < -0.3 and stablecoins_pct > 50:
        conditions['fear_bottom'] = {
            'sentiment': sentiment_score,
            'stablecoins_pct': stablecoins_pct,
            'stablecoins_usd': stablecoins_value,
            'total_portfolio': total_value
        }
    
    # Condition 3: Portfolio imbalance
    # any_asset > 80% AND asset not in [BTC, ETH]
    major_coins = ['BTC', 'ETH', 'USDT', 'USDC', 'DAI']
    for token, pct in allocation.items():
        if pct > 80 and token not in major_coins:
            conditions['portfolio_imbalance'] = {
                'token': token,
                'allocation_pct': pct,
                'usd_value': next((c.get('usd_value', 0) for c in coins if c.get('symbol') == token), 0)
            }
            break
    
    # Condition 4: Significant price move
    # Check if any portfolio asset changed > 8% in 24h
    # Note: This requires price change data from bybit_read.py
    # We'll check if any coin has significant unrealized PnL as proxy
    for coin in coins:
        unreal_pnl = coin.get('unrealised_pnl')
        usd_value = coin.get('usd_value', 0)
        if unreal_pnl is not None and usd_value > 0:
            # Calculate PnL percentage relative to position value
            pnl_pct = (unreal_pnl / usd_value) * 100 if usd_value > 0 else 0
            if abs(pnl_pct) > 8:
                conditions['significant_price_move'] = {
                    'token': coin.get('symbol'),
                    'price_change_pct': round(pnl_pct, 2),
                    'usd_value': usd_value,
                    'unrealized_pnl': unreal_pnl
                }
                break
    
    return conditions


def generate_recommendation(condition_type: str, details: Dict) -> str:
    """Generate recommendation based on condition type"""
    recommendations = {
        'high_sentiment_low_portfolio': 
            f"На Reddit хайп по ${details['token']}, а у тебя всего {details['user_position_pct']:.1f}% портфеля. "
            f"Если веришь в тренд — можно выделить часть USDT (${details['stablecoins_usd']:.0f}) через DCA.",
        
        'fear_bottom': 
            f"Рынок в страхе (sentiment {details['sentiment']:.2f}). У тебя {details['stablecoins_pct']:.1f}% в стейблах. "
            f"Исторически это время для покупок, но никто не знает дно. Рассмотри DCA в BTC/ETH.",
        
        'portfolio_imbalance': 
            f"{details['allocation_pct']:.1f}% портфеля в ${details['token']} — высокая концентрация риска. "
            f"Рекомендуется диверсификация или фиксация части прибыли.",
        
        'significant_price_move': 
            f"${details['token']} движется сильно: {details['price_change_pct']:+.1f}% PnL. "
            + ("Может быть время фиксировать прибыль." if details['price_change_pct'] > 0 else "Следи за стопами.")
    }
    
    return recommendations.get(condition_type, "Проверь портфель вручную для деталей.")


def format_alert(condition_type: str, details: Dict, portfolio: Dict) -> str:
    """Format alert message for Telegram"""
    
    # Map condition type to readable name
    condition_names = {
        'high_sentiment_low_portfolio': 'Хайп на токене',
        'fear_bottom': 'Рынок в страхе',
        'portfolio_imbalance': 'Дисбаланс портфеля',
        'significant_price_move': 'Сильное движение цены'
    }
    
    condition_name = condition_names.get(condition_type, condition_type)
    
    # Build details section
    details_lines = []
    
    if condition_type == 'high_sentiment_low_portfolio':
        details_lines.append(f"- Токен: ${details['token']}")
        details_lines.append(f"- Sentiment: {details['sentiment']:+.2f} (Reddit хайп)")
        details_lines.append(f"- Твоя позиция: {details['user_position_pct']:.1f}% (${details['user_position_usd']:,.0f})")
        details_lines.append(f"- Свободно USDT: ${details['stablecoins_usd']:,.0f} ({details['stablecoins_pct']:.1f}%)")
    
    elif condition_type == 'fear_bottom':
        details_lines.append(f"- Sentiment: {details['sentiment']:.2f} (страх на рынке)")
        details_lines.append(f"- Стейблкоины: {details['stablecoins_pct']:.1f}% (${details['stablecoins_usd']:,.0f})")
        details_lines.append(f"- Всего в портфеле: ${details['total_portfolio']:,.0f}")
    
    elif condition_type == 'portfolio_imbalance':
        details_lines.append(f"- Токен: ${details['token']}")
        details_lines.append(f"- Доля в портфеле: {details['allocation_pct']:.1f}%")
        details_lines.append(f"- USD значение: ${details['usd_value']:,.0f}")
    
    elif condition_type == 'significant_price_move':
        details_lines.append(f"- Токен: ${details['token']}")
        details_lines.append(f"- Изменение: {details['price_change_pct']:+.1f}%")
        details_lines.append(f"- Позиция: ${details['usd_value']:,.0f}")
        details_lines.append(f"- Нереализованный PnL: ${details['unrealized_pnl']:+.2f}")
    
    recommendation = generate_recommendation(condition_type, details)
    
    alert = f"""🔥 Crypto Alert — {condition_name}

{chr(10).join(details_lines)}

💡 Рекомендация: {recommendation}
⚠️ Не финансовый совет"""
    
    return alert


def send_telegram_alert(message: str) -> bool:
    """Send alert via Telegram using OpenClaw message tool"""
    try:
        # Get Telegram config from environment or config file
        telegram_config_path = os.path.expanduser('~/.openclaw/config/telegram.json')
        if os.path.exists(telegram_config_path):
            with open(telegram_config_path) as f:
                config = json.load(f)
                # Use the configured default channel
                channel = config.get('defaultChannel', 'telegram')
        else:
            channel = 'telegram'
        
        # Write alert to a file that can be picked up by the cron system
        # Or use subprocess to call the message tool
        alert_file = os.path.expanduser('~/.openclaw/workspace-main/.crypto_alert')
        with open(alert_file, 'w') as f:
            f.write(message)
        
        # Also print to stdout for logging
        print(message)
        return True
    except Exception as e:
        print(f"Error sending alert: {e}", file=sys.stderr)
        return False


def main():
    """Main monitoring function"""
    
    # Load portfolio data
    portfolio = get_portfolio_data()
    if not portfolio:
        # Silent exit on error
        sys.exit(0)
    
    # Load sentiment data
    sentiment = get_sentiment_data()
    if not sentiment:
        # Silent exit on error
        sys.exit(0)
    
    # Check conditions
    triggered_conditions = check_conditions(portfolio, sentiment)
    
    # If no conditions triggered, exit silently
    if not triggered_conditions:
        sys.exit(0)
    
    # Send alerts for triggered conditions
    alerts_sent = 0
    for condition_type, details in triggered_conditions.items():
        alert_message = format_alert(condition_type, details, portfolio)
        if send_telegram_alert(alert_message):
            alerts_sent += 1
    
    # Exit with success if alerts were sent
    sys.exit(0 if alerts_sent > 0 else 0)


if __name__ == '__main__':
    main()
