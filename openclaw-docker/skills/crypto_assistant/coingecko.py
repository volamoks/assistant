#!/usr/bin/env python3
"""
Crypto Assistant - CoinGecko Market Data
Get real-time prices and market data
"""

import os
import json
import time
from datetime import datetime

try:
    import requests
except ImportError:
    import requests


# CoinGecko API (free tier)
BASE_URL = "https://api.coingecko.com/api/v3"

# Popular crypto IDs
COIN_IDS = {
    "BTC": "bitcoin",
    "ETH": "ethereum", 
    "SOL": "solana",
    "BNB": "binancecoin",
    "XRP": "ripple",
    "ADA": "cardano",
    "DOGE": "dogecoin",
    "TON": "the-open-network",
    "NOT": "notcoin",
    "PEPE": "pepe",
    "SHIB": "shiba-inu",
    "AVAX": "avalanche-2",
    "DOT": "polkadot",
    "MATIC": "matic-network",
    "LINK": "chainlink"
}


def get_prices(ids=None, currency="usd"):
    """Get prices for multiple coins"""
    if ids is None:
        ids = list(COIN_IDS.values())
    
    url = f"{BASE_URL}/simple/price"
    params = {
        "ids": ",".join(ids),
        "vs_currencies": currency,
        "include_24hr_change": "true",
        "include_market_cap": "true"
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        return {"error": str(e)}
    
    return {}


def get_coin_data(coin_id):
    """Get detailed coin data"""
    url = f"{BASE_URL}/coins/{coin_id}"
    params = {
        "localization": "false",
        "tickers": "false",
        "community_data": "false",
        "developer_data": "false"
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        return {"error": str(e)}
    
    return {}


def get_trending():
    """Get trending coins on CoinGecko"""
    url = f"{BASE_URL}/search/trending"
    
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            coins = []
            for item in data.get('coins', [])[:7]:
                coin = item.get('item', {})
                coins.append({
                    "name": coin.get('name'),
                    "symbol": coin.get('symbol', '').upper(),
                    "price": coin.get('price_btc', 0),
                    "market_cap_rank": coin.get('market_cap_rank')
                })
            return coins
    except Exception as e:
        return []
    
    return []


def get_fear_greed():
    """Get Fear & Greed Index (from alternative.me)"""
    url = "https://api.alternative.me/fng/"
    
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get('data'):
                d = data['data'][0]
                return {
                    "value": int(d.get('value', 50)),
                    "classification": d.get('value_classification', 'Neutral'),
                    "timestamp": d.get('timestamp')
                }
    except Exception as e:
        return {"error": str(e)}
    
    return {}


def analyze_opportunities(stablecoins_value, sentiment):
    """Generate investment opportunities based on data"""
    opportunities = []
    
    # Get current prices and sentiment
    prices = get_prices()
    fear_greed = get_fear_greed()
    trending = get_trending()
    
    # High sentiment + user has stablecoins = opportunity to deploy capital
    if stablecoins_value > 100 and sentiment > 0.2:
        opportunities.append({
            "type": "DEPLOY_STABLES",
            "title": "Deploy Stablecoins",
            "description": f"Sentiment is positive ({sentiment:.2f}) and you have ${stablecoins_value:.0f} in stablecoins",
            "action": "Consider dollar-cost averaging into quality assets"
        })
    
    # Fear + user has stablecoins = potential bottom
    if stablecoins_value > 100 and sentiment < -0.2:
        opportunities.append({
            "type": "FEAR_BOTTOM",
            "title": "Potential Bottom",
            "description": f"Negative sentiment ({sentiment:.2f}) - historically this could be a buying opportunity",
            "action": "Only invest what you can afford to lose"
        })
    
    # High fear & greed index
    if fear_greed.get('value', 50) < 25:
        opportunities.append({
            "type": "EXTREME_FEAR",
            "title": "Extreme Fear",
            "description": f"Fear & Greed Index: {fear_greed.get('value')} ({fear_greed.get('classification')})",
            "action": "Historically good time to buy, but could go lower"
        })
    
    # Trending coins
    if trending:
        opportunities.append({
            "type": "TRENDING",
            "title": "Trending on CoinGecko",
            "coins": [c['symbol'] for c in trending[:5]],
            "action": "Research before buying - trending != good investment"
        })
    
    return opportunities


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='CoinGecko Market Data')
    parser.add_argument('--prices', action='store_true', help='Get current prices')
    parser.add_argument('--trending', action='store_true', help='Get trending coins')
    parser.add_argument('--fng', action='store_true', help='Get Fear & Greed Index')
    parser.add_argument('--json', action='store_true', help='Output as JSON')
    
    args = parser.parse_args()
    
    if args.prices:
        data = get_prices()
        if args.json:
            print(json.dumps(data, indent=2))
        else:
            print("\n" + "="*50)
            print("💰 MARKET PRICES")
            print("="*50)
            for symbol, cid in COIN_IDS.items():
                if cid in data:
                    price = data[cid].get('usd', 0)
                    change = data[cid].get('usd_24h_change', 0)
                    emoji = "🟢" if change > 0 else "🔴"
                    print(f"{symbol}: ${price:,.4f} {emoji} {change:+.2f}%")
    
    if args.trending:
        data = get_trending()
        if args.json:
            print(json.dumps(data, indent=2))
        else:
            print("\n" + "="*50)
            print("🔥 TRENDING COINS")
            print("="*50)
            for coin in data:
                print(f"#{coin.get('market_cap_rank')} {coin.get('symbol')}: {coin.get('name')}")
    
    if args.fng:
        data = get_fear_greed()
        if args.json:
            print(json.dumps(data, indent=2))
        else:
            print("\n" + "="*50)
            print("😱 FEAR & GREED INDEX")
            print("="*50)
            value = data.get('value', 0)
            classification = data.get('classification', 'Unknown')
            
            if value < 25:
                emoji = "😱"
            elif value < 45:
                emoji = "😰"
            elif value < 55:
                emoji = "😐"
            elif value < 75:
                emoji = "😊"
            else:
                emoji = "🤑"
            
            print(f"{emoji} {value}/100 - {classification}")
    
    if not args.pricing and not args.trending and not args.fng:
        # Show all
        print("\n" + "="*50)
        print("📊 MARKET OVERVIEW")
        print("="*50)
        
        # Prices
        data = get_prices()
        print("\n💰 Prices:")
        for symbol, cid in list(COIN_IDS.items())[:5]:
            if cid in data:
                price = data[cid].get('usd', 0)
                change = data[cid].get('usd_24h_change', 0)
                emoji = "🟢" if change > 0 else "🔴"
                print(f"  {symbol}: ${price:,.2f} {emoji} {change:+.1f}%")
        
        # Fear & Greed
        fg = get_fear_greed()
        if fg:
            print(f"\n😱 Fear & Greed: {fg.get('value')}/100 - {fg.get('classification')}")
        
        # Trending
        trending = get_trending()
        if trending:
            print(f"\n🔥 Trending: {', '.join([c['symbol'] for c in trending[:3]])}")
