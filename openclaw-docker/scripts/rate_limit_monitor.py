#!/usr/bin/env python3
"""
Rate Limit Monitor - Console UI similar to Alibaba Cloud Console
Shows remaining API quota for various LLM providers.

Usage:
    python3 rate_limit_monitor.py                    # Show all providers
    python3 rate_limit_monitor.py --watch             # Watch mode with live updates
    python3 rate_limit_monitor.py --provider deepseek # Specific provider
    python3 rate_limit_monitor.py --json              # JSON output
    
    # Configure manual quota (for providers without API access):
    python3 rate_limit_monitor.py --set-quota dashscope 1000000
    python3 rate_limit_monitor.py --track-usage dashscope 50000 100

Note: Alibaba Cloud (DashScope) doesn't provide a public quota API.
Use --set-quota to configure your known quota limit manually.
"""

import os
import sys
import json
import time
import argparse
from datetime import datetime
from typing import Optional, Dict, List, Any

try:
    import requests
except ImportError:
    print("Error: 'requests' package not installed. Run: pip install requests")
    sys.exit(1)


# ANSI Colors
class Colors:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    
    # Status colors
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    MAGENTA = "\033[95m"
    
    # Progress bar colors
    PROGRESS_FULL = "\033[48;5;82m"    # Green
    PROGRESS_MEDIUM = "\033[48;5;226m" # Yellow
    PROGRESS_LOW = "\033[48;5;196m"   # Red
    PROGRESS_EMPTY = "\033[48;5;240m" # Gray


def clear_screen():
    """Clear terminal screen"""
    os.system('cls' if os.name == 'nt' else 'clear')


def create_progress_bar(percentage: float, width: int = 30) -> str:
    """Create a progress bar similar to Alibaba Cloud console"""
    # Handle negative percentages
    if percentage < 0:
        percentage = 0
    
    filled = int(width * percentage / 100)
    if filled > width:
        filled = width
    empty = width - filled
    
    # Determine color based on percentage
    if percentage > 60:
        color = Colors.PROGRESS_FULL
    elif percentage > 30:
        color = Colors.PROGRESS_MEDIUM
    else:
        color = Colors.PROGRESS_LOW
    
    bar = color + " " * filled + Colors.PROGRESS_EMPTY + " " * empty + Colors.RESET
    return bar


def format_number(num: float) -> str:
    """Format large numbers with K/M suffixes"""
    if num >= 1_000_000:
        return f"{num / 1_000_000:.1f}M"
    elif num >= 1_000:
        return f"{num / 1_000:.1f}K"
    return f"{num:.0f}"


def get_next_reset() -> tuple:
    """Get next reset time for DashScope (approximate)"""
    from datetime import datetime, timedelta, timezone
    import calendar
    
    now = datetime.now(timezone.utc)
    
    # Daily reset is at midnight UTC
    tomorrow = now + timedelta(days=1)
    daily_reset = tomorrow.replace(hour=0, minute=0, second=0, microsecond=0)
    
    # Monthly reset - based on user's plan end date from console: 2026-04-03 21:00:00
    # That's approximately the monthly billing cycle
    # Current cycle ends April 3, 2026
    
    # Calculate based on actual plan end date
    # User's plan: End Time 2026-04-03 21:00:00 UTC
    plan_end = datetime(2026, 4, 3, 21, 0, 0, tzinfo=timezone.utc)
    
    # Days until monthly reset
    monthly_days = (plan_end - now).days
    monthly_reset_str = plan_end.strftime("%Y-%m-%d 21:00 UTC")
    
    # Hours until daily reset
    daily_hours = (daily_reset - now).total_seconds() / 3600
    daily_reset_str = daily_reset.strftime("%Y-%m-%d 00:00 UTC")
    
    return f"Daily: ~{daily_reset_str} (в {daily_hours:.1f}ч)", f"Monthly: {monthly_reset_str} (через {monthly_days}д)"


class DashScopeMonitor:
    """Monitor Alibaba Cloud (DashScope) API quota"""
    
    API_BASE = "https://dashscope-intl.aliyuncs.com/api/v1"
    
    # Default quota limits for Lite Basic Plan
    DEFAULT_QUOTA = {
        "daily": 1000000,  # 1M tokens/day (approximate)
        "monthly": 10000000,  # 10M tokens/month
    }
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        })
    
    def get_quota(self) -> Optional[Dict[str, Any]]:
        """Fetch quota information from DashScope - returns None as API unavailable"""
        # DashScope doesn't provide a public quota API
        # We'll return None and use local tracking or manual config
        return None
    
    def get_local_usage(self) -> Dict[str, Any]:
        """Get locally tracked usage"""
        return load_local_usage("dashscope")
    
    def parse_quota(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse quota - uses local tracking since API not available"""
        result = {
            "provider": "Alibaba Cloud (DashScope)",
            "quota_type": "tokens",
            "total": 0,
            "used": 0,
            "remaining": 0,
            "percentage": 0,
            "models": [],
            "note": "Manual config or local tracking required"
        }
        
        # Try to get local usage
        local_usage = self.get_local_usage()
        
        # Use manual quota if configured
        daily_limit = local_usage.get("daily_limit", self.DEFAULT_QUOTA["daily"])
        monthly_limit = local_usage.get("monthly_limit", self.DEFAULT_QUOTA["monthly"])
        tokens_used = local_usage.get("tokens", 0)
        
        # Check if user has set manual quota
        if daily_limit > 0:
            result["total"] = daily_limit
            result["used"] = tokens_used
            result["remaining"] = max(0, daily_limit - tokens_used)
            result["quota_type"] = "tokens/day"
            
            if result["total"] > 0:
                result["percentage"] = (result["remaining"] / result["total"]) * 100
        
        return result


class DeepSeekMonitor:
    """Monitor DeepSeek API quota"""
    
    API_BASE = "https://api.deepseek.com"
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        })
    
    def get_quota(self) -> Optional[Dict[str, Any]]:
        """Fetch quota from DeepSeek"""
        try:
            response = self.session.get(
                f"{self.API_BASE}/v1/user/balance",
                timeout=10
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return None
        except:
            return None
    
    def parse_quota(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse DeepSeek quota"""
        result = {
            "provider": "DeepSeek",
            "quota_type": "credits",
            "total": 0,
            "used": 0,
            "remaining": 0,
            "percentage": 0,
            "models": []
        }
        
        if not data:
            return result
        
        try:
            # DeepSeek returns balance info
            balance_info = data.get("balance_infos", [])
            for bal in balance_info:
                if bal.get("currency") == "USD":
                    remaining = float(bal.get("total_balance", 0))
                    # Total includes usage
                    result["remaining"] = remaining
                    # Assume a reasonable quota limit
                    result["total"] = max(remaining * 2, 10)  # At least $10
                    result["used"] = result["total"] - result["remaining"]
            
            if result["total"] > 0:
                result["percentage"] = (result["remaining"] / result["total"]) * 100
                
        except:
            pass
        
        return result


class OpenRouterMonitor:
    """Monitor OpenRouter API quota"""
    
    API_BASE = "https://openrouter.ai/api/v1"
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        })
    
    def get_quota(self) -> Optional[Dict[str, Any]]:
        """Fetch quota from OpenRouter"""
        try:
            response = self.session.get(
                f"{self.API_BASE}/credits",
                timeout=10
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return None
        except:
            return None
    
    def parse_quota(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse OpenRouter quota"""
        result = {
            "provider": "OpenRouter",
            "quota_type": "credits",
            "total": 0,
            "used": 0,
            "remaining": 0,
            "percentage": 0,
            "models": []
        }
        
        if not data:
            return result
        
        try:
            data_obj = data.get("data", {})
            result["total"] = data_obj.get("total_credits", 0)
            result["used"] = data_obj.get("total_usage", 0)
            result["remaining"] = result["total"] - result["used"]
            
            if result["total"] > 0:
                result["percentage"] = (result["remaining"] / result["total"]) * 100
                
        except:
            pass
        
        return result


class GroqMonitor:
    """Monitor Groq API quota"""
    
    # Groq doesn't have a public quota API, so we'll estimate from usage
    # This is a placeholder - in production you'd track requests locally
    
    def __init__(self, api_key: str):
        self.api_key = api_key
    
    def get_quota(self) -> Optional[Dict[str, Any]]:
        """Groq doesn't expose quota via API - return None"""
        return None
    
    def parse_quota(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Return unknown status for Groq"""
        return {
            "provider": "Groq",
            "quota_type": "unknown",
            "total": 0,
            "used": 0,
            "remaining": 0,
            "percentage": 0,
            "models": [],
            "note": "Rate limit based (no quota API)"
        }


class KiloCodeMonitor:
    """Monitor KiloCode API quota"""
    
    API_BASE = "https://api.kilo.ai/api/gateway"
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        })
    
    def get_quota(self) -> Optional[Dict[str, Any]]:
        """Fetch quota from KiloCode"""
        try:
            # Try user info endpoint
            response = self.session.get(
                f"{self.API_BASE}/user",
                timeout=10
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return None
        except:
            return None
    
    def parse_quota(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse KiloCode quota"""
        result = {
            "provider": "KiloCode",
            "quota_type": "requests",
            "total": 0,
            "used": 0,
            "remaining": 0,
            "percentage": 0,
            "models": []
        }
        
        if not data:
            return result
        
        try:
            # KiloCode response format
            user_data = data.get("data", {})
            if "credits" in user_data:
                credits = user_data.get("credits", {})
                result["remaining"] = credits.get("remaining", 0)
                result["total"] = credits.get("limit", result["remaining"] * 2)
                result["used"] = result["total"] - result["remaining"]
            
            if result["total"] > 0:
                result["percentage"] = (result["remaining"] / result["total"]) * 100
                
        except:
            pass
        
        return result


def load_env_key(key: str) -> Optional[str]:
    """Load API key from environment or .env file"""
    # First try environment variable
    value = os.environ.get(key)
    if value:
        return value
    
    # Try loading from litellm .env file (multiple possible paths)
    possible_paths = [
        os.path.join(os.path.dirname(__file__), "..", "litellm", ".env"),
        os.path.join(os.path.dirname(__file__), "litellm", ".env"),
        os.path.join(os.path.dirname(__file__), "..", "..", "litellm", ".env"),
        os.path.expanduser("~/Projects/bot/openclaw-docker/litellm/.env"),
    ]
    
    for env_path in possible_paths:
        if os.path.exists(env_path):
            with open(env_path, "r") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("#") or not line:
                        continue
                    if "=" in line:
                        k, v = line.split("=", 1)
                        if k.strip() == key:
                            return v.strip().strip('"')
    
    return None


def get_usage_file_path(provider: str) -> str:
    """Get path for local usage tracking file"""
    base_dir = os.path.join(os.path.dirname(__file__), "..", "data")
    os.makedirs(base_dir, exist_ok=True)
    return os.path.join(base_dir, f"{provider}_usage.json")


def load_local_usage(provider: str) -> Dict[str, Any]:
    """Load locally tracked usage for a provider"""
    usage_file = get_usage_file_path(provider)
    
    if os.path.exists(usage_file):
        try:
            with open(usage_file, 'r') as f:
                return json.load(f)
        except:
            pass
    
    return {}


def save_local_usage(provider: str, usage: Dict[str, Any]):
    """Save locally tracked usage"""
    usage_file = get_usage_file_path(provider)
    with open(usage_file, 'w') as f:
        json.dump(usage, f, indent=2)


def get_all_monitors() -> List[tuple]:
    """Get all available monitors"""
    monitors = []
    
    # DashScope / Alibaba
    dashscope_key = load_env_key("DASHSCOPE_API_KEY")
    if dashscope_key:
        monitors.append(("dashscope", DashScopeMonitor(dashscope_key)))
    
    # DeepSeek
    deepseek_key = load_env_key("DEEPSEEK_API_KEY")
    if deepseek_key:
        monitors.append(("deepseek", DeepSeekMonitor(deepseek_key)))
    
    # OpenRouter
    openrouter_key = load_env_key("OPENROUTER_API_KEY")
    if openrouter_key:
        monitors.append(("openrouter", OpenRouterMonitor(openrouter_key)))
    
    # Groq
    groq_key = load_env_key("GROQ_API_KEY")
    if groq_key:
        monitors.append(("groq", GroqMonitor(groq_key)))
    
    # KiloCode
    kilocode_key = load_env_key("KILOCODE_API_KEY")
    if kilocode_key:
        monitors.append(("kilocode", KiloCodeMonitor(kilocode_key)))
    
    return monitors


def display_quota(name: str, quota: Dict[str, Any]):
    """Display quota in Alibaba Cloud console style"""
    provider = quota.get("provider", name.upper())
    percentage = quota.get("percentage", 0)
    remaining = quota.get("remaining", 0)
    used = quota.get("used", 0)
    total = quota.get("total", 0)
    quota_type = quota.get("quota_type", "tokens")
    
    # Status color - handle negative percentages and edge cases
    if remaining <= 0:
        status_color = Colors.DIM
        status_text = "✗ EMPTY"
    elif percentage > 60:
        status_color = Colors.GREEN
        status_text = "✓ NORMAL"
    elif percentage > 30:
        status_color = Colors.YELLOW
        status_text = "⚠ LOW"
    elif percentage > 0:
        status_color = Colors.RED
        status_text = "✗ CRITICAL"
    else:
        status_color = Colors.DIM
        status_text = "✗ EMPTY"
    
    print(f"\n{Colors.BOLD}{'='*60}{Colors.RESET}")
    print(f"{Colors.BOLD}  🟢 {provider} - API Quota{Colors.RESET}")
    print(f"{Colors.BOLD}{'='*60}{Colors.RESET}")
    print(f"\n  Status: {status_color}{status_text}{Colors.RESET}")
    print(f"\n  {Colors.CYAN}Quota Type:{Colors.RESET} {quota_type}")
    
    # Progress bar
    print(f"\n  {Colors.CYAN}Usage:{Colors.RESET}")
    bar = create_progress_bar(percentage)
    print(f"  [{bar}] {percentage:.1f}%")
    
    # Numbers
    print(f"\n  {Colors.CYAN}Statistics:{Colors.RESET}")
    print(f"    Total:    {format_number(total)} {quota_type}")
    print(f"    Used:     {format_number(used)} {quota_type}")
    print(f"    Remain:   {status_color}{format_number(remaining)} {quota_type}{Colors.RESET}")
    
    # Note if any
    if "note" in quota:
        print(f"\n  {Colors.DIM}Note: {quota['note']}{Colors.RESET}")
    
    # Show reset time for DashScope
    if name == "dashscope" or quota.get("provider", "").find("DashScope") >= 0:
        daily_reset, monthly_reset = get_next_reset()
        print(f"\n  {Colors.CYAN}Next Reset:{Colors.RESET}")
        print(f"    {daily_reset}")
        print(f"    {monthly_reset}")


def display_summary(quotas: List[tuple]):
    """Display summary of all quotas"""
    clear_screen()
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    print(f"\n{Colors.BOLD}{Colors.CYAN}")
    print("╔════════════════════════════════════════════════════════════╗")
    print("║        🔥 API RATE LIMIT MONITOR - Alibaba Style 🔥       ║")
    print("╚════════════════════════════════════════════════════════════╝")
    print(f"{Colors.RESET}")
    print(f"  Last Updated: {timestamp}")
    print(f"  {'─' * 56}")
    
    # Display each provider
    for name, quota in quotas:
        display_quota(name, quota)
    
    print(f"\n{Colors.DIM}  Press Ctrl+C to exit watch mode{Colors.RESET}\n")


def watch_mode(interval: int = 30):
    """Watch mode - continuously update quota display"""
    try:
        while True:
            monitors = get_all_monitors()
            quotas = []
            
            for name, monitor in monitors:
                data = monitor.get_quota()
                quota = monitor.parse_quota(data)
                quotas.append((name, quota))
            
            display_summary(quotas)
            time.sleep(interval)
            
    except KeyboardInterrupt:
        print(f"\n{Colors.CYAN}👋 Exiting rate limit monitor{Colors.RESET}\n")
        sys.exit(0)


def main():
    parser = argparse.ArgumentParser(
        description="API Rate Limit Monitor - Alibaba Cloud Console Style"
    )
    parser.add_argument(
        "--watch", "-w",
        action="store_true",
        help="Watch mode - continuously update"
    )
    parser.add_argument(
        "--interval", "-i",
        type=int,
        default=30,
        help="Update interval in seconds (default: 30)"
    )
    parser.add_argument(
        "--provider", "-p",
        choices=["dashscope", "deepseek", "openrouter", "groq", "kilocode", "all"],
        default="all",
        help="Specific provider to check"
    )
    parser.add_argument(
        "--json", "-j",
        action="store_true",
        help="Output in JSON format"
    )
    parser.add_argument(
        "--set-quota",
        type=str,
        nargs=2,
        metavar=("PROVIDER", "QUOTA"),
        help="Set manual quota limit (e.g., --set-quota dashscope 1000000)"
    )
    parser.add_argument(
        "--track-usage",
        type=str,
        nargs=3,
        metavar=("PROVIDER", "TOKENS", "REQUESTS"),
        help="Track usage manually (e.g., --track-usage dashscope 50000 100)"
    )
    
    args = parser.parse_args()
    
    # Handle quota configuration
    if args.set_quota:
        provider, quota = args.set_quota
        usage_file = get_usage_file_path(provider)
        usage = load_local_usage(provider)
        usage["daily_limit"] = int(quota)
        usage["monthly_limit"] = int(quota) * 10
        save_local_usage(provider, usage)
        print(f"{Colors.GREEN}✓ Set {provider} daily quota to {quota} tokens{Colors.RESET}")
        sys.exit(0)
    
    # Handle usage tracking
    if args.track_usage:
        provider, tokens, requests = args.track_usage
        usage_file = get_usage_file_path(provider)
        usage = load_local_usage(provider)
        usage["tokens"] = usage.get("tokens", 0) + int(tokens)
        usage["requests"] = usage.get("requests", 0) + int(requests)
        usage["last_updated"] = datetime.now().isoformat()
        save_local_usage(provider, usage)
        print(f"{Colors.GREEN}✓ Tracked {tokens} tokens, {requests} requests for {provider}{Colors.RESET}")
        sys.exit(0)
    
    monitors = get_all_monitors()
    
    if not monitors:
        print(f"{Colors.RED}Error: No API keys found.{Colors.RESET}")
        print("Please set environment variables:")
        print("  DASHSCOPE_API_KEY")
        print("  DEEPSEEK_API_KEY")
        print("  OPENROUTER_API_KEY")
        print("  GROQ_API_KEY")
        print("  KILOCODE_API_KEY")
        sys.exit(1)
    
    # Filter by provider if specified
    if args.provider != "all":
        monitors = [(n, m) for n, m in monitors if n == args.provider]
    
    if args.watch:
        watch_mode(args.interval)
    
    # Single fetch
    quotas = []
    for name, monitor in monitors:
        data = monitor.get_quota()
        quota = monitor.parse_quota(data)
        quotas.append((name, quota))
    
    if args.json:
        output = {name: quota for name, quota in quotas}
        print(json.dumps(output, indent=2))
    else:
        display_summary(quotas)


if __name__ == "__main__":
    main()
