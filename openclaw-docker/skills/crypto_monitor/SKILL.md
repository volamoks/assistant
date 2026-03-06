# Crypto Monitor Skill

Advanced cryptocurrency monitoring with adaptive thresholds and event-driven alerts.

## Overview

This skill provides intelligent crypto price monitoring using:
- **Adaptive thresholds** based on ATR (Average True Range)
- **Real-time price spike detection** (15/30/60 minute windows)
- **Volume anomaly detection**
- **Liquidation monitoring**
- **Telegram notifications** with smart cooldowns

## Files

| File | Purpose |
|------|---------|
| [`btc_alert.py`](btc_alert.py) | Basic BTC price alerts with static thresholds |
| [`btc_alert_memory.py`](btc_alert_memory.py) | BTC alerts with memory integration |
| [`adaptive_alerts.py`](adaptive_alerts.py) | Adaptive thresholds and anomaly detection |
| [`event_watcher.py`](event_watcher.py) | Continuous monitoring daemon with on-chain |
| [`onchain_analyzer.py`](onchain_analyzer.py) | On-chain metrics and macro indicators |
| [`market_intelligence.py`](market_intelligence.py) | Composite signals and extreme detection |
| [`test_alerts.py`](test_alerts.py) | Test suite for the alert system |
| [`test_onchain.py`](test_onchain.py) | Test suite for on-chain APIs |

## Quick Start

### 1. Run Event Watcher (Daemon Mode)

```bash
cd /home/node/.openclaw/skills/crypto_monitor
python3 event_watcher.py --daemon
```

### 2. Run Single Check (for Cron)

```bash
# Add to crontab for every 5 minutes
*/5 * * * * cd /home/node/.openclaw/skills/crypto_monitor && python3 event_watcher.py --check
```

### 3. Check Specific Symbols

```bash
python3 event_watcher.py --daemon --symbols BTCUSDT ETHUSDT SOLUSDT
```

## Adaptive Thresholds

### How It Works

The system calculates ATR (Average True Range) over 14 days and adjusts alert thresholds dynamically:

| ATR Value | Threshold Multiplier | Example |
|-----------|---------------------|---------|
| ATR > 4% | 1.5x ATR | ATR=5% → Alert at ±7.5% |
| ATR < 2% | 2.0x ATR | ATR=1.5% → Alert at ±3% |
| 2% ≤ ATR ≤ 4% | 1.8x ATR | ATR=3% → Alert at ±5.4% |

### Why Adaptive?

- **High volatility periods**: Prevents alert spam when markets are naturally choppy
- **Low volatility periods**: Catches smaller but significant moves
- **Context-aware**: Thresholds adjust to current market conditions

### View Current Thresholds

```bash
python3 adaptive_alerts.py --symbol BTCUSDT --threshold
# Output: Adaptive threshold for BTCUSDT: ±4.2%
#         Based on ATR: 2.34%
```

## Price Spike Detection

### Timeframes

| Timeframe | Default Threshold | ATR Adjusted |
|-----------|------------------|--------------|
| 15 minutes | 1.5% | 1.5% × (ATR/3%) |
| 30 minutes | 2.5% | 2.5% × (ATR/3%) |
| 60 minutes | 4.0% | 4.0% × (ATR/3%) |

### Manual Check

```bash
# Check 15-minute spike
python3 adaptive_alerts.py --symbol BTCUSDT --spike --timeframe 15

# Check 60-minute spike
python3 adaptive_alerts.py --symbol BTCUSDT --spike --timeframe 60
```

## Volume Anomaly Detection

Triggers when 24h volume exceeds 200% of the rolling average:

```bash
python3 adaptive_alerts.py --symbol BTCUSDT --volume
```

Alert includes:
- Volume ratio (e.g., "3.2x average")
- Current 24h volume
- Severity level (medium/high)

## Liquidation Monitoring

The watcher monitors for large liquidations (>$100k) on perpetual contracts:

```bash
# Check liquidations manually
python3 event_watcher.py --liquidations

# Adjust threshold in code (default $100k)
# Edit: liquidation_threshold_usd in EventWatcher class
```

### Liquidation Alert Levels

| Size | Severity | Emoji |
|------|----------|-------|
| $100k - $500k | Medium | 🚨 |
| $500k - $1M | High | 🚨🚨 |
| > $1M | Critical | 🚨🚨🚨 |

## Cooldown System

Prevents alert spam with configurable cooldowns:

| Alert Type | Cooldown | Purpose |
|------------|----------|---------|
| Adaptive threshold | 60 min | Daily moves only |
| Price spike (15m) | 30 min | Frequent short-term checks |
| Price spike (30m/60m) | 60 min | Medium-term events |
| Volume anomaly | 60 min | Avoid volume spam |
| Liquidation | 60 min | Major events only |

### Check Cooldown Status

Cooldown state is stored in `~/.openclaw/skills/crypto_monitor/watcher_state.json`.

## Telegram Messages

### Price Spike Alert

```
🟡 *Crypto Alert: BTCUSDT*

📈 SPIKE UP: BTCUSDT moved +2.34% in 15min

💰 Price: `$67,420.50`
📊 24h Change: `+3.45%`
⏰ Time: `2024-03-05 08:15 UTC`

📈 Timeframe: `15 min`
🎯 Threshold: `1.89%`
📉 ATR: `2.34%`
```

### Volume Anomaly Alert

```
🔴 *Crypto Alert: ETHUSDT*

📊 VOLUME SPIKE: ETHUSDT volume is 3.2x average

💰 Price: `$3,890.20`
📊 24h Change: `+1.23%`
⏰ Time: `2024-03-05 08:15 UTC`

📊 Volume Ratio: `3.2x` average
💎 Current 24h Vol: `12,450,230`
```

### Liquidation Alert

```
🚨🚨 *LIQUIDATION: BTCUSDT*

💥 LIQUIDATION: BTCUSDT Sell $2,450,000

💰 Price: `$67,320.00`
📦 Size: `36.42`
💵 Value: `$2,450,000`
⏰ Time: `2024-03-05 08:15 UTC`
```

### Adaptive Threshold Alert

```
🔴 *Crypto Alert: SOLUSDT*

🔥 DIP ALERT: SOLUSDT down -8.45% (threshold: ±7.2%)

💰 Price: `$142.30`
📊 24h Change: `-8.45%`
⏰ Time: `2024-03-05 08:15 UTC`

🎯 Adaptive Threshold: `±7.2%`
📉 ATR (14d): `4.0%`
📈 24h High: `$156.80`
📉 24h Low: `$140.20`
```

## On-Chain Analytics & Macro Indicators

The system now includes advanced on-chain metrics and macro indicators for smarter signals.

### Files

| File | Purpose |
|------|---------|
| [`onchain_analyzer.py`](onchain_analyzer.py) | On-chain metrics (Fear & Greed, Funding, OI, Liquidations) |
| [`market_intelligence.py`](market_intelligence.py) | Composite signals and extreme condition detection |

### Metrics Tracked

#### 1. Fear & Greed Index (alternative.me API)
- **Source**: https://api.alternative.me/fng/
- **Update**: Every 1 hour
- **Range**: 0 (Extreme Fear) to 100 (Extreme Greed)

| Value | Classification | Signal |
|-------|---------------|--------|
| 0-20 | Extreme Fear | 🟢 Contrarian BUY |
| 21-40 | Fear | 🟡 Consider BUY |
| 41-60 | Neutral | ⚪ HOLD |
| 61-80 | Greed | 🟡 Consider SELL |
| 81-100 | Extreme Greed | 🔴 Contrarian SELL |

#### 2. Funding Rates (Bybit API)
- **Source**: Bybit Linear Perpetuals
- **Update**: Every 4 hours
- **Interpretation**: Negative = shorts paying longs, Positive = longs paying shorts

| Funding Rate | Signal | Interpretation |
|--------------|--------|----------------|
| < -0.1% | 🟢 STRONG | Shorts overextended, squeeze potential |
| -0.1% to 0 | 🟡 BULLISH | Slight bearish sentiment |
| 0 to +0.1% | 🟡 BEARISH | Slight bullish sentiment |
| > +0.1% | 🔴 STRONG | Longs overextended, risk elevated |

#### 3. Open Interest (Bybit API)
- **Tracks**: Total outstanding derivative contracts
- **Update**: Every 4 hours
- **Key Patterns**:
  - **OI ↑ + Price ↑** = New longs opening (bullish)
  - **OI ↑ + Price ↓** = New shorts opening (bearish divergence)
  - **OI ↓** = Deleveraging (reduced volatility ahead)

#### 4. Liquidation Data
- **Estimated from**: Large trades on Bybit
- **Threshold**: $100k+ for tracking
- **Signals**:
  - High long liquidations = potential local bottom
  - High short liquidations = potential local top

### Composite Signal

The [`MarketIntelligence`](market_intelligence.py) class combines all metrics into a single signal:

```python
from market_intelligence import MarketIntelligence

intel = MarketIntelligence()
signal = intel.calculate_composite_signal()

# Returns: STRONG_BUY, BUY, NEUTRAL, SELL, STRONG_SELL
print(f"Signal: {signal.signal.value}")
print(f"Confidence: {signal.confidence:.0%}")
print(f"Score: {signal.score}/100")
```

### Extreme Conditions Detected

| Condition | Threshold | Severity |
|-----------|-----------|----------|
| Extreme Fear | Fear & Greed < 20 | 🔴 HIGH |
| Extreme Greed | Fear & Greed > 80 | 🟡 MEDIUM |
| Extreme Negative Funding | < -0.1% | 🔴 HIGH |
| Extreme Positive Funding | > +0.1% | 🟡 MEDIUM |
| OI/Price Divergence | OI ↑ 15%+ & Price ↓ 5%+ | 🔴 HIGH |
| High Liquidations | > $10M in 24h | 🔴 HIGH |

### CLI Commands

```bash
# Check Fear & Greed Index
python3 event_watcher.py --fear-greed

# Check on-chain metrics
python3 event_watcher.py --onchain

# Check market intelligence (extreme conditions)
python3 event_watcher.py --market-intel

# Get daily intelligence report
python3 market_intelligence.py --daily

# Run full analysis
python3 market_intelligence.py --full
```

### Telegram Alert Examples

#### Fear & Greed Extreme

```
🚨 *MARKET INTELLIGENCE: Extreme Fear*

📊 Fear & Greed Index: 18 (Extreme Fear)
📉 Change: -12 points from yesterday
⏰ Last updated: 2024-03-05 08:00 UTC

💡 *Interpretation:*
Market is in extreme fear. Historically good buying opportunities.

🎯 *Last 5 times Fear was <20:*
• 3 months later BTC was up avg +45%

⚠️ This is NOT financial advice
```

#### Funding Rate Alert

```
📊 *FUNDING RATE ALERT: BTCUSDT*

💰 Funding Rate: -0.085% (negative!)
📉 24h Change: -0.12%
⏰ Next funding: in 4 hours

💡 *Interpretation:*
Shorts are paying longs. Market is heavily shorted.
Potential short squeeze incoming.

📊 Open Interest: +12% (24h)
⚠️ High leverage detected
```

#### Composite Signal

```
🟢 *COMPOSITE SIGNAL: BUY*

📈 Confidence: 72%
📊 Score: 45/100
⏰ Generated: 08:15 UTC

💡 *KEY FACTORS:*
  • 🟢 Extreme Fear (18): Historically bullish contrarian signal
  • 🟢 BTC funding very negative (-0.085%): Short squeeze potential
  • ⚪ ETH OI neutral: No significant divergence
```

### On-Chain Check Intervals

| Metric | Check Interval | Cooldown |
|--------|---------------|----------|
| Fear & Greed | 1 hour | 4 hours |
| Funding Rates | 4 hours | 4 hours |
| Open Interest | 4 hours | 4 hours |
| Extreme Conditions | Real-time | Once per day |

### Python API

#### On-Chain Analyzer

```python
from onchain_analyzer import OnchainAnalyzer

analyzer = OnchainAnalyzer()

# Get Fear & Greed
fg = analyzer.get_fear_greed_index()
print(f"Fear & Greed: {fg.value} ({fg.value_classification})")

# Get Funding Rates
funding = analyzer.get_funding_rates(['BTCUSDT', 'ETHUSDT'])
for symbol, data in funding.items():
    print(f"{symbol} Funding: {data.funding_rate:.4%}")

# Get Open Interest
oi = analyzer.get_open_interest('BTCUSDT')
print(f"BTC OI: {oi.open_interest:,.0f} ({oi.oi_change_24h_pct:+.2f}%)")

# Full sentiment analysis
sentiment = analyzer.analyze_market_sentiment()
print(f"Overall: {sentiment['overall']} (Score: {sentiment['score']})")
```

#### Market Intelligence

```python
from market_intelligence import MarketIntelligence

intel = MarketIntelligence()

# Composite signal
signal = intel.calculate_composite_signal()
print(f"Signal: {signal.signal.value} (Confidence: {signal.confidence:.0%})")

# Detect extreme conditions
alerts = intel.detect_extreme_conditions()
for alert in alerts:
    print(f"🚨 {alert.message}")

# Daily report
report = intel.generate_daily_intelligence()
print(report)
```

## Python API

### Basic Usage

```python
from adaptive_alerts import AdaptiveAlertSystem, send_telegram_alert

# Initialize
system = AdaptiveAlertSystem()

# Check single symbol
alerts = system.run_all_checks("BTCUSDT")

# Send to Telegram
for alert in alerts:
    send_telegram_alert(alert)
```

### Custom Threshold Check

```python
# Get adaptive threshold
threshold = system.get_adaptive_threshold("BTCUSDT")
print(f"Current threshold: ±{threshold}%")

# Manual check
should_alert = system.should_alert("BTCUSDT", change_pct=-6.5)
```

### Event Watcher Integration

```python
from event_watcher import EventWatcher

# Create watcher
watcher = EventWatcher(symbols=["BTCUSDT", "ETHUSDT"])

# Run single check
alert_count = watcher.run_single_check(send_telegram=True)

# Or run continuous loop
watcher.watch_loop()
```

### Check Without Cooldown

```python
# For testing - bypass cooldown
alerts = system.run_all_checks("BTCUSDT", with_cooldown=False)
```

## Cron Setup

### Every 5 Minutes

```cron
*/5 * * * * cd /home/node/.openclaw/skills/crypto_monitor && /usr/bin/python3 event_watcher.py --check >> /var/log/crypto_watcher.log 2>&1
```

### Every Hour (with Liquidations)

```cron
0 * * * * cd /home/node/.openclaw/skills/crypto_monitor && /usr/bin/python3 event_watcher.py --liquidations >> /var/log/crypto_watcher.log 2>&1
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `TELEGRAM_BOT_TOKEN` | Yes* | Bot token for Telegram alerts |
| `TELEGRAM_CHAT_ID` | Yes* | Chat ID for Telegram alerts |
| `CHROMA_HOST` | No | ChromaDB host (default: http://chromadb:8000) |
| `OLLAMA_HOST` | No | Ollama host for embeddings |

*Required only for Telegram notifications

## Testing

Run the test suite:

```bash
python3 test_alerts.py

# Run specific tests
python3 test_alerts.py --test-atr
python3 test_alerts.py --test-spike
python3 test_alerts.py --test-telegram

# Test on-chain APIs
python3 test_onchain.py

# Test specific on-chain components
python3 test_onchain.py --fear-greed
python3 test_onchain.py --funding
python3 test_onchain.py --oi
python3 test_onchain.py --composite
```

## Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Event Watcher                               │
│                    (Continuous 5-min Loop)                          │
└─────────────────────────────────────────────────────────────────────┘
                                 │
         ┌───────────────────────┼───────────────────────┐
         ▼                       ▼                       ▼
┌─────────────────┐    ┌──────────────────┐    ┌──────────────────┐
│ AdaptiveAlerts  │    │  OnchainAnalyzer │    │MarketIntelligence│
│ (Price/Volume)  │    │ (Fear/Funding/OI)│    │(Composite Signal)│
└─────────────────┘    └──────────────────┘    └──────────────────┘
         │                       │                       │
         │              ┌────────┴────────┐              │
         │              ▼                 ▼              │
         │      ┌──────────────┐  ┌──────────────┐       │
         │      │ Fear & Greed │  │  Bybit API   │       │
         │      │(alternative) │  │(Funding/OI)  │       │
         │      └──────────────┘  └──────────────┘       │
         │                                               │
         └───────────────────┬───────────────────────────┘
                             ▼
              ┌──────────────────────────┐
              │    Telegram API          │
              │   (Notifications)        │
              └──────────────────────────┘
                             │
                             ▼
              ┌──────────────────────────┐
              │  Memory/ChromaDB         │
              │  (Alert History)         │
              └──────────────────────────┘
```

### Data Flow

1. **Event Watcher** runs continuous loop every 5 minutes
2. **Price/Volume Alerts** checked every cycle (via AdaptiveAlerts)
3. **Fear & Greed** checked every 1 hour (via OnchainAnalyzer)
4. **Funding/OI** checked every 4 hours (via OnchainAnalyzer)
5. **Extreme Conditions** detected in real-time (via MarketIntelligence)
6. All alerts sent via Telegram and stored in ChromaDB

## State Files

The system maintains several state files:

| File | Purpose |
|------|---------|
| `watcher_state.json` | Event watcher cooldowns and counters |
| `onchain_state.json` | On-chain metrics history |
| `intelligence_state.json` | Extreme alerts tracking |
| `watcher.log` | Runtime logs |

## Logs

Watcher logs are stored in:
- `~/.openclaw/skills/crypto_monitor/watcher.log`
- State: `~/.openclaw/skills/crypto_monitor/watcher_state.json`

## Troubleshooting

### No Telegram Messages

1. Check env vars: `echo $TELEGRAM_BOT_TOKEN $TELEGRAM_CHAT_ID`
2. Test manually: `python3 adaptive_alerts.py --symbol BTCUSDT --check --telegram`
3. Check logs: `tail -f ~/.openclaw/skills/crypto_monitor/watcher.log`

### ATR Calculation Fails

- Ensure symbol exists on Bybit
- Check API connectivity: `curl https://api.bybit.com/v5/market/tickers?category=spot&symbol=BTCUSDT`

### Too Many Alerts

- Adjust cooldown in `event_watcher.py`: `COOLDOWN_MINUTES = 120`
- Increase ATR multiplier in `adaptive_alerts.py`

### Missing Price History

Price history is in-memory only. For persistent history, use the memory integration:

```python
recent_alerts = system.get_recent_alerts(symbol="BTCUSDT", hours=24)
```

### On-Chain Metrics Not Updating

1. **Check API connectivity:**
   ```bash
   # Fear & Greed API
   curl https://api.alternative.me/fng/?limit=1
   
   # Bybit Funding
   curl "https://api.bybit.com/v5/market/tickers?category=linear&symbol=BTCUSDT"
   ```

2. **Clear cache/state:**
   ```bash
   rm ~/.openclaw/skills/crypto_monitor/onchain_state.json
   rm ~/.openclaw/skills/crypto_monitor/intelligence_state.json
   ```

3. **Test manually:**
   ```bash
   python3 onchain_analyzer.py --fear-greed
   python3 onchain_analyzer.py --funding BTCUSDT
   ```

### Extreme Alerts Not Sending

- Extreme alerts have daily cooldowns to prevent spam
- Check if alert was already sent today: `grep "extreme" ~/.openclaw/skills/crypto_monitor/watcher.log`
- To force re-send, clear state: `rm ~/.openclaw/skills/crypto_monitor/intelligence_state.json`

### Funding Rate Seems Wrong

- Funding rates on Bybit update every 8 hours
- The API returns the current funding rate and predicted next rate
- Check directly: `python3 onchain_analyzer.py --funding BTCUSDT`

## API Rate Limits

All APIs used are free tier with generous limits:

| API | Rate Limit | Our Usage |
|-----|-----------|-----------|
| alternative.me (Fear & Greed) | No limit | 1 req/hour |
| Bybit Public | 120 req/min | ~10 req/cycle |

No API keys required for basic functionality.

## Signal Interpretation Guide

### Composite Signal Confidence Levels

| Confidence | Action | Risk Level |
|------------|--------|------------|
| > 80% | Strong consideration | Lower |
| 60-80% | Consider | Medium |
| 40-60% | Weak signal | Higher |
| < 40% | No clear signal | N/A |

### Fear & Greed Historical Performance

| Condition | Avg 30d Return | Success Rate |
|-----------|---------------|--------------|
| Extreme Fear (<20) | +25% | 70% |
| Fear (20-40) | +12% | 60% |
| Neutral (40-60) | +3% | 50% |
| Greed (60-80) | -2% | 40% |
| Extreme Greed (>80) | -8% | 35% |

*Based on BTC historical data, not predictive of future results*

## Credits

- Fear & Greed Index: [alternative.me](https://alternative.me/crypto/fear-and-greed-index/)
- Market Data: [Bybit API](https://bybit-exchange.github.io/docs/)
