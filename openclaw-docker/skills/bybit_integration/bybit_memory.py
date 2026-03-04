#!/usr/bin/env python3
"""
Bybit integration with memory layer.

Extends bybit_read.py with long-term memory for:
- Portfolio preferences
- Alert thresholds
- Strategy notes
"""

import sys
import os
sys.path.insert(0, '/home/node/.openclaw/skills')
sys.path.insert(0, os.path.dirname(__file__))

from agent_memory.memory import Memory
from src.client import BybitClient


class BybitWithMemory:
    """Bybit client with memory integration."""
    
    def __init__(self):
        self.client = BybitClient()
        self.memory = Memory(collection="crypto")
    
    def get_portfolio_with_context(self) -> dict:
        """
        Get portfolio with relevant memory context.
        
        Returns:
            Dict with portfolio data and memory context
        """
        # Fetch portfolio
        balance = self.client.get_wallet_balance(account_type='UNIFIED')
        positions = self.client.get_positions(category='linear', settle_coin='USDT')
        
        # Get relevant memories
        memories = self.memory.search("portfolio strategy preferences", limit=3)
        
        return {
            "balance": balance,
            "positions": positions,
            "memory_context": self.memory.format_for_prompt(memories)
        }
    
    def store_preference(self, text: str, category: str = "preference") -> str:
        """
        Store a portfolio preference or strategy note.
        
        Args:
            text: The preference/note to store
            category: Type (preference, strategy, alert_threshold)
        """
        return self.memory.store(
            text=text,
            metadata={
                "category": category,
                "source": "bybit_integration",
                "update_user_md": category == "preference"
            }
        )
    
    def check_alerts(self) -> list:
        """
        Check portfolio against stored alert thresholds.
        
        Returns:
            List of triggered alerts
        """
        # Get current portfolio
        balance = self.client.get_wallet_balance(account_type='UNIFIED')
        equity = float(balance.get('list', [{}])[0].get('totalEquity', 0))
        
        # Get alert thresholds from memory
        alerts = self.memory.get_by_category("alert_threshold", limit=10)
        
        triggered = []
        for alert in alerts:
            # Simple threshold check - could be more sophisticated
            if "below" in alert.text.lower() and "$" in alert.text:
                # Extract amount (simplified)
                try:
                    threshold = float(alert.text.split("$")[1].split()[0])
                    if equity < threshold:
                        triggered.append({
                            "type": "below_threshold",
                            "threshold": threshold,
                            "current": equity,
                            "note": alert.text
                        })
                except (IndexError, ValueError):
                    pass
        
        return triggered


def main():
    """CLI demo of bybit with memory."""
    import argparse
    
    p = argparse.ArgumentParser(description="Bybit with Memory")
    p.add_argument("action", choices=["portfolio", "remember", "alerts"])
    p.add_argument("--text", "-t", help="Text to remember")
    p.add_argument("--category", "-c", default="preference", 
                   choices=["preference", "strategy", "alert_threshold"])
    
    args = p.parse_args()
    
    bm = BybitWithMemory()
    
    if args.action == "portfolio":
        data = bm.get_portfolio_with_context()
        print("Portfolio fetched with memory context")
        print(f"Memory context: {data['memory_context'][:200]}...")
        
    elif args.action == "remember":
        if not args.text:
            print("Error: --text required")
            sys.exit(1)
        mid = bm.store_preference(args.text, args.category)
        print(f"Stored: {mid}")
        
    elif args.action == "alerts":
        alerts = bm.check_alerts()
        if alerts:
            print("Triggered alerts:")
            for a in alerts:
                print(f"  - {a['note']} (current: ${a['current']:,.2f})")
        else:
            print("No alerts triggered")


if __name__ == "__main__":
    main()