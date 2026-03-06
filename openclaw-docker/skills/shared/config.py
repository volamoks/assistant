"""
Universal Configuration Module for OpenClaw Skills

This module provides a centralized configuration system using Pydantic for validation.
All settings are loaded from environment variables with sensible defaults.

Usage:
    from shared.config import CryptoConfig, get_config
    
    # Get config with defaults
    config = get_config("crypto")
    print(config.rsi_oversold)  # 30.0
    
    # Override via environment variables
    # RSI_OVERSOLD=25 python script.py → 25.0
"""

import os
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field, field_validator

# Optional dotenv support
try:
    from dotenv import load_dotenv
    _DOTENV_AVAILABLE = True
except ImportError:
    _DOTENV_AVAILABLE = False
    def load_dotenv(*args, **kwargs):
        pass


# Initialize dotenv at module load time
def _init_dotenv():
    """Load .env file if python-dotenv is available."""
    if _DOTENV_AVAILABLE:
        # Try to load from common locations
        load_dotenv(dotenv_path=".env")
        load_dotenv(dotenv_path="../.env")


# Initialize dotenv when module is imported
_init_dotenv()


# =============================================================================
# Base Configuration
# =============================================================================

class Config(BaseModel):
    """
    Base configuration class with common settings.
    
    Attributes:
        debug: Enable debug mode for verbose logging
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        bybit_base_url: Base URL for Bybit API
        rate_limit_ms: Rate limit in milliseconds between API calls
        cache_ttl_default: Default cache TTL in seconds
        cache_dir: Directory for cache storage
    """
    
    # General settings
    debug: bool = Field(default=False, description="Enable debug mode")
    log_level: str = Field(default="INFO", description="Logging level")
    
    # API settings
    bybit_base_url: str = Field(default="https://api.bybit.com", description="Bybit API base URL")
    rate_limit_ms: int = Field(default=200, description="Rate limit in milliseconds")
    
    # Cache settings
    cache_ttl_default: int = Field(default=300, description="Default cache TTL in seconds")
    cache_dir: str = Field(default="/tmp/cache", description="Cache directory path")
    
    @classmethod
    def from_env(cls, env_vars: Optional[Dict[str, Any]] = None) -> "Config":
        """Create config from environment variables."""
        values = _load_env_values(cls, env_vars)
        return cls(**values)


# =============================================================================
# Crypto Configuration
# =============================================================================

class CryptoConfig(BaseModel):
    """
    Cryptocurrency monitoring and trading configuration.
    
    Combines settings for:
    - Symbol watchlists
    - RSI (Relative Strength Index) thresholds
    - ATR (Average True Range) volatility settings
    - Alert thresholds for price spikes and volume anomalies
    - On-chain metrics (Fear & Greed, funding rates, open interest)
    
    Attributes:
        default_symbols: Default trading symbols to monitor
        watchlist: Extended watchlist of symbols
        rsi_period: Period for RSI calculation
        rsi_oversold: RSI level indicating oversold condition
        rsi_overbought: RSI level indicating overbought condition
        atr_period: Period for ATR calculation
        atr_multiplier_high_vol: Multiplier for high volatility detection
        atr_multiplier_low_vol: Multiplier for low volatility detection
        atr_multiplier_normal: Default multiplier for normal conditions
        price_spike_threshold_15m: Price spike threshold for 15m timeframe (%)
        price_spike_threshold_1h: Price spike threshold for 1h timeframe (%)
        volume_anomaly_multiplier: Volume anomaly detection multiplier
        fear_greed_extreme_fear: Fear & Greed index extreme fear threshold
        fear_greed_extreme_greed: Fear & Greed index extreme greed threshold
        funding_rate_threshold: Funding rate threshold for alerts (0.1%)
        oi_change_threshold: Open interest change threshold (10%)
    """
    
    # Symbols
    default_symbols: List[str] = Field(
        default=["BTCUSDT", "ETHUSDT", "SOLUSDT"],
        description="Default trading symbols"
    )
    watchlist: List[str] = Field(
        default=[
            "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNB", "XRP", "ADA",
            "DOGE", "AVAX", "LINK", "DOT", "MATIC", "ATOM",
            "UNI", "LTC", "ETC"
        ],
        description="Extended watchlist"
    )
    
    # RSI settings
    rsi_period: int = Field(default=14, description="RSI calculation period")
    rsi_oversold: float = Field(default=30.0, description="RSI oversold threshold")
    rsi_overbought: float = Field(default=70.0, description="RSI overbought threshold")
    
    # ATR settings
    atr_period: int = Field(default=14, description="ATR calculation period")
    atr_multiplier_high_vol: float = Field(default=1.5, description="High volatility multiplier")
    atr_multiplier_low_vol: float = Field(default=2.0, description="Low volatility multiplier")
    atr_multiplier_normal: float = Field(default=1.8, description="Normal volatility multiplier")
    
    # Alert thresholds
    price_spike_threshold_15m: float = Field(default=2.0, description="15m price spike threshold (%)")
    price_spike_threshold_1h: float = Field(default=5.0, description="1h price spike threshold (%)")
    volume_anomaly_multiplier: float = Field(default=2.0, description="Volume anomaly multiplier")
    
    # On-chain metrics
    fear_greed_extreme_fear: int = Field(default=20, description="Extreme fear threshold")
    fear_greed_extreme_greed: int = Field(default=80, description="Extreme greed threshold")
    funding_rate_threshold: float = Field(default=0.001, description="Funding rate threshold (0.1%)")
    oi_change_threshold: float = Field(default=0.10, description="Open interest change threshold (10%)")
    
    @classmethod
    def from_env(cls, env_vars: Optional[Dict[str, Any]] = None) -> "CryptoConfig":
        """Create config from environment variables."""
        values = _load_env_values(cls, env_vars)
        return cls(**values)


# =============================================================================
# Alert Configuration
# =============================================================================

class AlertConfig(BaseModel):
    """
    Alert system configuration.
    
    Controls alert behavior including cooldown periods and notification channels.
    
    Attributes:
        enabled: Master switch for all alerts
        cooldown_minutes: Minimum time between repeated alerts for same condition
        telegram_enabled: Enable Telegram notifications
    """
    
    enabled: bool = Field(default=True, description="Master alert switch")
    cooldown_minutes: int = Field(default=60, description="Alert cooldown in minutes")
    telegram_enabled: bool = Field(default=True, description="Enable Telegram alerts")
    
    @classmethod
    def from_env(cls, env_vars: Optional[Dict[str, Any]] = None) -> "AlertConfig":
        """Create config from environment variables."""
        values = _load_env_values(cls, env_vars)
        return cls(**values)


# =============================================================================
# Bybit API Configuration
# =============================================================================

class BybitConfig(BaseModel):
    """
    Bybit API specific configuration.
    
    Attributes:
        api_key: Bybit API key
        api_secret: Bybit API secret
        base_url: API base URL
        testnet: Use testnet environment
        rate_limit_ms: Rate limit between requests
        timeout_seconds: Request timeout
    """
    
    api_key: str = Field(default="", description="Bybit API key")
    api_secret: str = Field(default="", description="Bybit API secret")
    base_url: str = Field(default="https://api.bybit.com", description="API base URL")
    testnet: bool = Field(default=False, description="Use testnet")
    rate_limit_ms: int = Field(default=200, description="Rate limit in ms")
    timeout_seconds: int = Field(default=30, description="Request timeout")
    
    @classmethod
    def from_env(cls, env_vars: Optional[Dict[str, Any]] = None) -> "BybitConfig":
        """Create config from environment variables."""
        values = _load_env_values(cls, env_vars)
        return cls(**values)


# =============================================================================
# Telegram Configuration
# =============================================================================

class TelegramConfig(BaseModel):
    """
    Telegram bot configuration.
    
    Attributes:
        bot_token: Telegram bot token
        chat_ids: List of chat IDs for notifications
        streaming_mode: Streaming mode (off, partial, block, progress)
    """
    
    bot_token: str = Field(default="", description="Telegram bot token")
    chat_ids: List[int] = Field(default=[], description="Chat IDs for notifications")
    streaming_mode: str = Field(default="block", description="Streaming mode")
    
    @classmethod
    def from_env(cls, env_vars: Optional[Dict[str, Any]] = None) -> "TelegramConfig":
        """Create config from environment variables."""
        values = _load_env_values(cls, env_vars)
        return cls(**values)


# =============================================================================
# Environment Variable Loading
# =============================================================================

def _get_env_mapping() -> Dict[str, str]:
    """Get mapping of environment variable names to config keys."""
    return {
        # Base config
        "DEBUG": "debug",
        "LOG_LEVEL": "log_level",
        "BYBIT_BASE_URL": "bybit_base_url",
        "RATE_LIMIT_MS": "rate_limit_ms",
        "CACHE_TTL_DEFAULT": "cache_ttl_default",
        "CACHE_DIR": "cache_dir",
        
        # Crypto config
        "DEFAULT_SYMBOLS": "default_symbols",
        "WATCHLIST": "watchlist",
        "RSI_PERIOD": "rsi_period",
        "RSI_OVERSOLD": "rsi_oversold",
        "RSI_OVERBOUGHT": "rsi_overbought",
        "ATR_PERIOD": "atr_period",
        "ATR_MULTIPLIER_HIGH_VOL": "atr_multiplier_high_vol",
        "ATR_MULTIPLIER_LOW_VOL": "atr_multiplier_low_vol",
        "ATR_MULTIPLIER_NORMAL": "atr_multiplier_normal",
        "PRICE_SPIKE_THRESHOLD_15M": "price_spike_threshold_15m",
        "PRICE_SPIKE_THRESHOLD_1H": "price_spike_threshold_1h",
        "VOLUME_ANOMALY_MULTIPLIER": "volume_anomaly_multiplier",
        "FEAR_GREED_EXTREME_FEAR": "fear_greed_extreme_fear",
        "FEAR_GREED_EXTREME_GREED": "fear_greed_extreme_greed",
        "FUNDING_RATE_THRESHOLD": "funding_rate_threshold",
        "OI_CHANGE_THRESHOLD": "oi_change_threshold",
        
        # Alert config
        "ALERT_ENABLED": "enabled",
        "ALERT_COOLDOWN_MINUTES": "cooldown_minutes",
        "TELEGRAM_ENABLED": "telegram_enabled",
        
        # Bybit config
        "BYBIT_API": "api_key",
        "BYBIT_API_SECRET": "api_secret",
        "BYBIT_TESTNET": "testnet",
        "BYBIT_TIMEOUT": "timeout_seconds",
        
        # Telegram config
        "TELEGRAM_BOT_TOKEN": "bot_token",
        "TELEGRAM_CHAT_ID": "chat_ids",
        "TELEGRAM_STREAMING_MODE": "streaming_mode",
    }


def _parse_env_value(value: str, key: str) -> Any:
    """
    Parse environment variable value to appropriate type.
    
    Args:
        value: Raw string value from environment
        key: Configuration key for type hinting
        
    Returns:
        Parsed value (bool, int, float, list, or str)
    """
    # Boolean parsing
    if key in ("debug", "testnet", "enabled", "telegram_enabled"):
        return value.lower() in ("true", "1", "yes", "on")
    
    # Integer parsing
    if key in ("rsi_period", "atr_period", "cooldown_minutes", "rate_limit_ms",
               "timeout_seconds", "fear_greed_extreme_fear", "fear_greed_extreme_greed",
               "cache_ttl_default"):
        return int(value)
    
    # Float parsing
    if key in ("rsi_oversold", "rsi_overbought", "atr_multiplier_high_vol",
               "atr_multiplier_low_vol", "atr_multiplier_normal",
               "price_spike_threshold_15m", "price_spike_threshold_1h",
               "volume_anomaly_multiplier", "funding_rate_threshold", "oi_change_threshold"):
        return float(value)
    
    # List parsing (comma-separated)
    if key in ("default_symbols", "watchlist"):
        return [item.strip() for item in value.split(",")]
    
    if key == "chat_ids":
        return [int(item.strip()) for item in value.split(",")]
    
    # Default: return as string
    return value


def _load_env_values(config_class: type, env_vars: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Load environment values for a specific config class.
    
    Args:
        config_class: The configuration class to load values for
        env_vars: Optional pre-loaded environment variables
        
    Returns:
        Dictionary of configuration values for the class
    """
    if env_vars is None:
        env_vars = load_from_env()
    
    # Get field names from the config class
    field_names = set(config_class.model_fields.keys())
    
    # Filter to only include fields that belong to this config class
    return {k: v for k, v in env_vars.items() if k in field_names}


def load_from_env() -> Dict[str, Any]:
    """
    Load configuration from environment variables.
    
    Reads all relevant environment variables and returns them as a dictionary.
    Supports both direct environment variables and .env file loading (via python-dotenv).
    
    Returns:
        Dictionary of configuration values
        
    Example:
        >>> env_config = load_from_env()
        >>> print(env_config.get('RSI_OVERSOLD', 30.0))
    """
    config: Dict[str, Any] = {}
    env_mapping = _get_env_mapping()
    
    for env_var, config_key in env_mapping.items():
        value = os.environ.get(env_var)
        if value is not None:
            config[config_key] = _parse_env_value(value, config_key)
    
    return config


def get_config(config_type: str = "crypto", env_vars: Optional[Dict[str, Any]] = None) -> BaseModel:
    """
    Factory function to get configuration by type.
    
    Creates and returns a configuration object of the specified type.
    Configuration is loaded from environment variables with fallback to defaults.
    
    Args:
        config_type: Type of configuration to load. Supported types:
            - "base" or "config": Base configuration
            - "crypto": Cryptocurrency monitoring config
            - "alert": Alert system config
            - "bybit": Bybit API config
            - "telegram": Telegram bot config
        env_vars: Optional pre-loaded environment variables
            
    Returns:
        Configuration object of the specified type
        
    Raises:
        ValueError: If config_type is not recognized
        
    Example:
        >>> config = get_config("crypto")
        >>> print(config.rsi_oversold)
        30.0
        
        >>> # Override with environment variable
        >>> # RSI_OVERSOLD=25 python script.py
        >>> config = get_config("crypto")
        >>> print(config.rsi_oversold)
        25.0
    """
    config_classes = {
        "base": Config,
        "config": Config,
        "crypto": CryptoConfig,
        "alert": AlertConfig,
        "bybit": BybitConfig,
        "telegram": TelegramConfig,
    }
    
    if config_type not in config_classes:
        valid_types = ", ".join(config_classes.keys())
        raise ValueError(f"Unknown config type: {config_type}. Valid types: {valid_types}")
    
    config_class = config_classes[config_type]
    
    # Use from_env method if available, otherwise instantiate directly
    if hasattr(config_class, "from_env"):
        return config_class.from_env(env_vars)
    
    return config_class()


def get_all_configs() -> Dict[str, BaseModel]:
    """
    Get all configuration types at once.
    
    Returns:
        Dictionary mapping config type names to their configuration objects
        
    Example:
        >>> configs = get_all_configs()
        >>> crypto = configs["crypto"]
        >>> alert = configs["alert"]
    """
    return {
        "base": get_config("base"),
        "crypto": get_config("crypto"),
        "alert": get_config("alert"),
        "bybit": get_config("bybit"),
        "telegram": get_config("telegram"),
    }


# =============================================================================
# CLI Helper
# =============================================================================

if __name__ == "__main__":
    # Simple CLI to test configuration
    import json
    
    print("OpenClaw Configuration Module")
    print("=" * 40)
    
    # Load and display all configs
    configs = get_all_configs()
    
    for config_type, config in configs.items():
        print(f"\n{config_type.upper()} Configuration:")
        print("-" * 40)
        
        # Convert to dict and display
        config_dict = config.model_dump()
        for key, value in config_dict.items():
            # Mask sensitive values
            if "secret" in key.lower() or "token" in key.lower() or "key" in key.lower():
                if value:
                    value = f"***{str(value)[-4:]}" if len(str(value)) > 4 else "***"
            print(f"  {key}: {value}")
