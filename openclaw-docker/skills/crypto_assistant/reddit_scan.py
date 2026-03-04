#!/usr/bin/env python3
"""
Crypto Assistant - Reddit Sentiment Scanner
Scans crypto subreddits for sentiment analysis
"""

import os
import json
import re
import time
from datetime import datetime, timedelta
from collections import Counter

try:
    import requests
except ImportError:
    print("Installing requests...")
    os.system("pip install requests")
    import requests


# Popular crypto subreddits
SUBREDDITS = {
    "CryptoCurrency": "r/CryptoCurrency",
    "Bitcoin": "r/Bitcoin", 
    "ethereum": "r/ethereum",
    "Solana": "r/Solana",
    "Cardano": "r/Cardano",
    "ethtrader": "r/ethtrader"
}

# Keywords for sentiment analysis
POSITIVE_KEYWORDS = [
    "bullish", "moon", "pump", "gain", "profit", "up", "buy", "long", "accumulate",
    "gem", "alpha", "breakout", "rally", "surge", "soar", "ATH", "bullrun",
    "green", "calls", "dyor", "hodl", "future", "growth", "adoption"
]

NEGATIVE_KEYWORDS = [
    "bearish", "dump", "crash", "loss", "down", "sell", "short", "scam", "rug",
    "fud", "fear", "drop", "red", "correction", "rekt", "panic", "top", "bubble",
    "liquidate", "warning", "risk", "danger"
]

BULLRUN_KEYWORDS = ["bitcoin", "btc", "solana", "sol", "eth", "ethereum", "ton", "notcoin"]


def get_reddit_posts(subreddit, limit=25):
    """Fetch posts from subreddit using Reddit API"""
    url = f"https://www.reddit.com/r/{subreddit}/hot.json"
    headers = {
        "User-Agent": "CryptoAssistant/1.0",
        "Accept": "application/json"
    }
    params = {"limit": limit, "raw_json": 1}
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            posts = []
            for child in data.get('data', {}).get('children', []):
                post = child.get('data', {})
                posts.append({
                    'title': post.get('title', ''),
                    'score': post.get('score', 0),
                    'num_comments': post.get('num_comments', 0),
                    'created_utc': post.get('created_utc', 0),
                    'url': f"https://reddit.com{post.get('permalink', '')}"
                })
            return posts
    except Exception as e:
        print(f"Error fetching r/{subreddit}: {e}")
    
    return []


def analyze_sentiment(text):
    """Analyze sentiment of text"""
    text_lower = text.lower()
    
    positive_count = sum(1 for kw in POSITIVE_KEYWORDS if kw in text_lower)
    negative_count = sum(1 for kw in NEGATIVE_KEYWORDS if kw in text_lower)
    
    # Calculate sentiment score (-1 to 1)
    total = positive_count + negative_count
    if total > 0:
        sentiment = (positive_count - negative_count) / total
    else:
        sentiment = 0
    
    return {
        "positive": positive_count,
        "negative": negative_count,
        "score": sentiment,  # -1 to 1
        "strength": total
    }


def detect_trending_tokens(posts):
    """Detect which tokens are being mentioned"""
    token_mentions = Counter()
    
    for post in posts:
        title_lower = post['title'].lower()
        
        # Count mentions
        for token in BULLRUN_KEYWORDS:
            if token in title_lower:
                token_mentions[token.upper()] += post.get('score', 1) + post.get('num_comments', 0)
    
    return token_mentions.most_common(10)


def scan_crypto_reddits():
    """Main scanning function"""
    results = {
        "timestamp": datetime.now().isoformat(),
        "subreddits": {},
        "overall_sentiment": 0,
        "trending_tokens": [],
        "hot_topics": []
    }
    
    all_posts = []
    total_sentiment = 0
    total_posts = 0
    
    for sub_name in SUBREDDITS.keys():
        posts = get_reddit_posts(sub_name)
        all_posts.extend(posts)
        
        sub_sentiment = 0
        for post in posts:
            sentiment = analyze_sentiment(post['title'])
            sub_sentiment += sentiment['score']
        
        if posts:
            avg_sentiment = sub_sentiment / len(posts)
            results["subreddits"][SUBREDDITS[sub_name]] = {
                "post_count": len(posts),
                "sentiment": round(avg_sentiment, 3)
            }
            total_sentiment += sub_sentiment
            total_posts += len(posts)
    
    # Overall sentiment
    if total_posts > 0:
        results["overall_sentiment"] = round(total_sentiment / total_posts, 3)
    
    # Trending tokens
    results["trending_tokens"] = detect_trending_tokens(all_posts)
    
    # Hot topics (top posts by score)
    top_posts = sorted(all_posts, key=lambda x: x.get('score', 0), reverse=True)[:5]
    for post in top_posts:
        results["hot_topics"].append({
            "title": post['title'][:100],
            "score": post.get('score', 0),
            "url": post['url']
        })
    
    return results


def get_investment_signals():
    """Generate investment signals based on sentiment"""
    data = scan_crypto_reddits()
    
    signals = {
        "timestamp": data["timestamp"],
        "sentiment_score": data["overall_sentiment"],
        "signal": "NEUTRAL",
        "reasoning": [],
        "opportunities": []
    }
    
    sentiment = data["overall_sentiment"]
    
    # Determine signal
    if sentiment > 0.3:
        signals["signal"] = "BULLISH"
        signals["reasoning"].append("High positive sentiment across crypto communities")
    elif sentiment > 0.1:
        signals["signal"] = "SLIGHTLY_BULLISH"
        signals["reasoning"].append("Moderately positive sentiment")
    elif sentiment < -0.3:
        signals["signal"] = "BEARISH"
        signals["reasoning"].append("High negative sentiment - possible fear in market")
    elif sentiment < -0.1:
        signals["signal"] = "SLIGHTLY_BEARISH"
        signals["reasoning"].append("Negative sentiment prevailing")
    else:
        signals["signal"] = "NEUTRAL"
        signals["reasoning"].append("Mixed or neutral sentiment")
    
    # Find opportunities (trending + positive)
    for token, count in data["trending_tokens"]:
        if count > 10:  # Minimum threshold
            signals["opportunities"].append({
                "token": token,
                "mention_score": count,
                "type": "TRENDING"
            })
    
    return signals


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Reddit Crypto Sentiment Scanner')
    parser.add_argument('--scan', action='store_true', help='Full sentiment scan')
    parser.add_argument('--signals', action='store_true', help='Get investment signals')
    parser.add_argument('--json', action='store_true', help='Output as JSON')
    
    args = parser.parse_args()
    
    if args.signals or not args.scan:
        data = get_investment_signals()
    else:
        data = scan_crypto_reddits()
    
    if args.json:
        print(json.dumps(data, indent=2))
    else:
        print("\n" + "="*50)
        print("🐕 REDDIT SENTIMENT ANALYSIS")
        print("="*50)
        
        if args.signals or not args.scan:
            score = data["sentiment_score"]
            emoji = "🐂" if score > 0 else "🐻" if score < 0 else "➖"
            print(f"\nSignal: {emoji} {data['signal']}")
            print(f"Sentiment Score: {score:.2f} (-1 to +1)")
            print(f"\nReasoning:")
            for r in data['reasoning']:
                print(f"  • {r}")
            
            if data['opportunities']:
                print(f"\n🔥 Trending Tokens:")
                for opp in data['opportunities']:
                    print(f"  • {opp['token']}: {opp['mention_score']} points")
        else:
            print(f"\nOverall Sentiment: {data['overall_sentiment']:.2f}")
            print(f"\nSubreddits:")
            for sub, info in data['subreddits'].items():
                print(f"  {sub}: {info['sentiment']} ({info['post_count']} posts)")
            
            print(f"\n🔥 Trending:")
            for token, count in data['trending_tokens'][:5]:
                print(f"  {token}: {count}")
