#!/usr/bin/env python3
"""
BTC Price Monitor with memory layer.

Extends btc_alert.py with:
- Custom alert thresholds from memory
- Alert history
- User preferences
"""

import os
import sys
sys.path.insert(0, '/home/node/.openclaw/skills')

from datetime import datetime
from btc_alert import get_btc_data, ALERT_THRESHOLDS
from agent_memory.memory import Memory


class BTCAlertWithMemory:
    """BTC alert system with memory integration."""
    
    def __init__(self):
        self.memory = Memory(collection="crypto")
    
    def get_custom_thresholds(self) -> dict:
        """
        Get custom thresholds from memory, fallback to defaults.
        
        Returns:
            Dict of threshold configs
        """
        # Get thresholds from memory
        thresholds = self.memory.get_by_category("alert_threshold", limit=5)
        
        if not thresholds:
            return ALERT_THRESHOLDS
        
        # Parse custom thresholds (simplified)
        custom = {}
        for t in thresholds:
            text = t.text.lower()
            try:
                if "dip" in text and "%" in text:
                    pct = float(text.split("%")[0].split()[-1].replace("-", ""))
                    custom['custom_dip'] = {
                        'pct': -pct,
                        'label': f'💾 Custom Dip ({pct}%)',
                        'action': 'User-defined threshold from memory'
                    }
            except (ValueError, IndexError):
                pass
        
        return {**ALERT_THRESHOLDS, **custom}
    
    def store_alert(self, alert_type: str, price: float, pct_24h: float):
        """
        Store triggered alert in memory.
        
        Args:
            alert_type: Type of alert triggered
            price: BTC price at trigger
            pct_24h: 24h change percentage
        """
        self.memory.store(
            text=f"BTC alert {alert_type} at ${price:,.0f} ({pct_24h:+.1f}% 24h)",
            metadata={
                "category": "alert_history",
                "alert_type": alert_type,
                "price": price,
                "pct_24h": pct_24h,
                "timestamp": datetime.now().isoformat()
            }
        )
    
    def store_preference(self, text: str) -> str:
        """Store user preference about crypto."""
        return self.memory.store(
            text=text,
            metadata={
                "category": "preference",
                "source": "crypto_monitor",
                "update_user_md": True
            }
        )
    
    def check_with_memory(self):
        """Check BTC with custom thresholds and memory logging."""
        btc = get_btc_data()
        if not btc:
            print('ERROR: Failed to fetch BTC data')
            return
        
        print(f"BTC: ${btc['price']:,.0f}  24h: {btc['pct_24h']:+.2f}%")
        
        # Get thresholds (custom + default)
        thresholds = self.get_custom_thresholds()
        
        # Check levels
        triggered = []
        for name, threshold in thresholds.items():
            pct = threshold['pct']
            if (pct < 0 and btc['pct_24h'] <= pct) or (pct > 0 and btc['pct_24h'] >= pct):
                triggered.append((name, threshold))
        
        # Log and report
        if triggered:
            for name, threshold in triggered:
                print(f"\n{threshold['label']} — {threshold['action']}")
                self.store_alert(name, btc['price'], btc['pct_24h'])
        else:
            print(f"No alert: 24h change ({btc['pct_24h']:+.1f}%) within range")
        
        return triggered


def main():
    """CLI for BTC alert with memory."""
    import argparse
    
    p = argparse.ArgumentParser(description="BTC Alert with Memory")
    p.add_argument("action", choices=["check", "remember"], default="check")
    p.add_argument("--text", "-t", help="Preference text to remember")
    
    args = p.parse_args()
    
    alert = BTCAlertWithMemory()
    
    if args.action == "check":
        alert.check_with_memory()
    elif args.action == "remember":
        if not args.text:
            print("Error: --text required")
            sys.exit(1)
        mid = alert.store_preference(args.text)
        print(f"Stored preference: {mid}")


if __name__ == '__main__':
    main()