"""
Universal caching module for OpenClaw project.

Provides thread-safe caching with TTL support, including:
- MemoryCache: Fast in-memory caching
- FileCache: Persistent file-based caching
- cached decorator: Function-level caching
- get_or_set: Atomic get-or-compute operation

Example usage:
    # Simple memory cache
    cache = MemoryCache()
    cache.set("user:1", {"name": "John"}, ttl=60)
    user = cache.get("user:1")
    
    # With decorator
    @cached(ttl=300)
    async def get_data():
        return await fetch_from_api()
    
    # File-based for persistence
    file_cache = FileCache("/tmp/cache")
    file_cache.set("alerts", alerts_data)
"""

import asyncio
import hashlib
import json
import os
import threading
import time
from collections import OrderedDict
from functools import wraps
from pathlib import Path
from typing import Any, Callable, Optional


class Cache:
    """
    Base cache class with TTL support.
    
    Thread-safe implementation using locks for all operations.
    
    Args:
        default_ttl: Default time-to-live in seconds (default: 300 = 5 minutes)
    
    Example:
        >>> cache = Cache(default_ttl=600)
        >>> cache.set("key", "value", ttl=300)
        >>> value = cache.get("key")
        >>> if cache.has("key"):
        ...     print("Key exists")
        >>> cache.delete("key")
        >>> cache.clear()
    """
    
    def __init__(self, default_ttl: int = 300) -> None:
        """
        Initialize the cache.
        
        Args:
            default_ttl: Default TTL in seconds for stored items
        """
        self._default_ttl = default_ttl
        self._lock = threading.RLock()
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get a value from the cache.
        
        Args:
            key: The cache key
            
        Returns:
            The cached value, or None if not found or expired
        """
        raise NotImplementedError
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """
        Set a value in the cache.
        
        Args:
            key: The cache key
            value: The value to cache
            ttl: Time-to-live in seconds (uses default if not specified)
        """
        raise NotImplementedError
    
    def delete(self, key: str) -> bool:
        """
        Delete a key from the cache.
        
        Args:
            key: The cache key to delete
            
        Returns:
            True if the key was deleted, False if it didn't exist
        """
        raise NotImplementedError
    
    def clear(self) -> None:
        """Clear all items from the cache."""
        raise NotImplementedError
    
    def has(self, key: str) -> bool:
        """
        Check if a key exists in the cache (and is not expired).
        
        Args:
            key: The cache key to check
            
        Returns:
            True if the key exists and is not expired
        """
        raise NotImplementedError
    
    def get_or_set(self, key: str, factory: Callable[[], Any], ttl: Optional[int] = None) -> Any:
        """
        Get a value from cache, or compute and store it if not present.
        
        Thread-safe atomic operation - factory is called at most once per key.
        
        Args:
            key: The cache key
            factory: Callable that returns the value to cache if key is missing
            ttl: Time-to-live in seconds (uses default if not specified)
            
        Returns:
            The cached or computed value
            
        Example:
            >>> def expensive_computation():
            ...     return sum(range(1000000))
            >>> result = cache.get_or_set("compute:sum", expensive_computation, ttl=3600)
        """
        with self._lock:
            value = self.get(key)
            if value is not None:
                return value
            value = factory()
            self.set(key, value, ttl)
            return value
    
    @property
    def default_ttl(self) -> int:
        """Get the default TTL value."""
        return self._default_ttl


class MemoryCache(Cache):
    """
    In-memory cache implementation using OrderedDict for LRU behavior.
    
    Fast, thread-safe caching without persistence. Items are stored
    in memory only and will be lost when the process terminates.
    
    Args:
        default_ttl: Default time-to-live in seconds (default: 300)
        max_size: Maximum number of items to keep in cache (default: 1000)
    
    Example:
        >>> cache = MemoryCache(default_ttl=60, max_size=100)
        >>> cache.set("session:abc123", {"user_id": 1})
        >>> session = cache.get("session:abc123")
    """
    
    def __init__(self, default_ttl: int = 300, max_size: int = 1000) -> None:
        """
        Initialize the memory cache.
        
        Args:
            default_ttl: Default TTL in seconds
            max_size: Maximum cache size (LRU eviction when exceeded)
        """
        super().__init__(default_ttl)
        self._max_size = max_size
        self._cache: OrderedDict[str, tuple[Any, float]] = OrderedDict()
    
    def get(self, key: str) -> Optional[Any]:
        """Get a value from the cache."""
        with self._lock:
            if key not in self._cache:
                return None
            
            value, expires_at = self._cache[key]
            
            # Check if expired
            if expires_at and time.time() > expires_at:
                del self._cache[key]
                return None
            
            # Move to end (most recently used)
            self._cache.move_to_end(key)
            return value
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set a value in the cache."""
        if ttl is None:
            ttl = self._default_ttl
        
        expires_at = time.time() + ttl if ttl > 0 else 0  # 0 means no expiry
        
        with self._lock:
            # If key exists, remove it first to update position
            if key in self._cache:
                del self._cache[key]
            
            # Evict oldest if at capacity
            while len(self._cache) >= self._max_size:
                self._cache.popitem(last=False)
            
            self._cache[key] = (value, expires_at)
    
    def delete(self, key: str) -> bool:
        """Delete a key from the cache."""
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False
    
    def clear(self) -> None:
        """Clear all items from the cache."""
        with self._lock:
            self._cache.clear()
    
    def has(self, key: str) -> bool:
        """Check if a key exists in the cache."""
        with self._lock:
            if key not in self._cache:
                return False
            
            _, expires_at = self._cache[key]
            
            # Check if expired
            if expires_at and time.time() > expires_at:
                del self._cache[key]
                return False
            
            return True
    
    def __len__(self) -> int:
        """Return the number of items in the cache."""
        with self._lock:
            return len(self._cache)
    
    def __repr__(self) -> str:
        """Return a string representation of the cache."""
        with self._lock:
            return f"MemoryCache(size={len(self._cache)}, max_size={self._max_size})"


class FileCache(Cache):
    """
    File-based cache for persistent storage.
    
    Stores cache data as JSON files in a specified directory.
    Useful for caching data that should survive process restarts.
    
    Args:
        cache_dir: Directory to store cache files
        default_ttl: Default time-to-live in seconds (default: 3600 = 1 hour)
    
    Example:
        >>> file_cache = FileCache("/tmp/myapp_cache", default_ttl=7200)
        >>> file_cache.set("api:response:data", {"result": [1, 2, 3]})
        >>> data = file_cache.get("api:response:data")
        >>> file_cache.delete("api:response:data")
    """
    
    def __init__(self, cache_dir: str, default_ttl: int = 3600) -> None:
        """
        Initialize the file cache.
        
        Args:
            cache_dir: Directory path for cache storage
            default_ttl: Default TTL in seconds
        """
        super().__init__(default_ttl)
        self._cache_dir = Path(cache_dir)
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        # Use a memory cache for indexing metadata
        self._index: dict[str, tuple[float, float]] = {}  # key -> (expires_at, mtime)
        self._load_index()
    
    def _get_file_path(self, key: str) -> Path:
        """
        Get the file path for a cache key.
        
        Args:
            key: The cache key
            
        Returns:
            Path to the cache file
        """
        # Hash the key to create a safe filename
        key_hash = hashlib.md5(key.encode()).hexdigest()
        return self._cache_dir / f"{key_hash}.json"
    
    def _load_index(self) -> None:
        """Load the cache index from existing files."""
        with self._lock:
            self._index.clear()
            for file_path in self._cache_dir.glob("*.json"):
                try:
                    with open(file_path, 'r') as f:
                        data = json.load(f)
                        key = data.get('_key')
                        expires_at = data.get('_expires_at', 0)
                        mtime = file_path.stat().st_mtime
                        if key:
                            self._index[key] = (expires_at, mtime)
                except (json.JSONDecodeError, IOError):
                    # Skip corrupted files
                    continue
    
    def get(self, key: str) -> Optional[Any]:
        """Get a value from the cache."""
        with self._lock:
            if key not in self._index:
                return None
            
            expires_at, _ = self._index[key]
            
            # Check if expired
            if expires_at and time.time() > expires_at:
                self.delete(key)
                return None
            
            file_path = self._get_file_path(key)
            
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)
                    return data.get('_value')
            except (json.JSONDecodeError, IOError, FileNotFoundError):
                # File corrupted or missing, clean up index
                if key in self._index:
                    del self._index[key]
                return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set a value in the cache."""
        if ttl is None:
            ttl = self._default_ttl
        
        expires_at = time.time() + ttl if ttl > 0 else 0
        
        with self._lock:
            file_path = self._get_file_path(key)
            
            data = {
                '_key': key,
                '_value': value,
                '_expires_at': expires_at,
                '_created_at': time.time()
            }
            
            try:
                with open(file_path, 'w') as f:
                    json.dump(data, f, default=str)
                self._index[key] = (expires_at, time.time())
            except IOError as e:
                raise RuntimeError(f"Failed to write cache file: {e}")
    
    def delete(self, key: str) -> bool:
        """Delete a key from the cache."""
        with self._lock:
            if key not in self._index:
                return False
            
            file_path = self._get_file_path(key)
            
            try:
                if file_path.exists():
                    file_path.unlink()
                del self._index[key]
                return True
            except IOError:
                return False
    
    def clear(self) -> None:
        """Clear all items from the cache."""
        with self._lock:
            for file_path in self._cache_dir.glob("*.json"):
                try:
                    file_path.unlink()
                except IOError:
                    pass
            self._index.clear()
    
    def has(self, key: str) -> bool:
        """Check if a key exists in the cache."""
        with self._lock:
            if key not in self._index:
                return False
            
            expires_at, _ = self._index[key]
            
            # Check if expired
            if expires_at and time.time() > expires_at:
                self.delete(key)
                return False
            
            return True
    
    def cleanup(self) -> int:
        """
        Remove all expired entries from the cache.
        
        Returns:
            Number of entries removed
        """
        removed = 0
        with self._lock:
            expired_keys = [
                key for key, (expires_at, _) in self._index.items()
                if expires_at and time.time() > expires_at
            ]
            for key in expired_keys:
                if self.delete(key):
                    removed += 1
        return removed
    
    def __len__(self) -> int:
        """Return the number of items in the cache."""
        with self._lock:
            return len(self._index)
    
    def __repr__(self) -> str:
        """Return a string representation of the cache."""
        with self._lock:
            return f"FileCache(dir={self._cache_dir}, size={len(self._index)})"


def cached(
    ttl: int = 300,
    key_builder: Optional[Callable[..., str]] = None,
    cache: Optional[Cache] = None
) -> Callable:
    """
    Decorator for caching function results.
    
    Works with both synchronous and asynchronous functions.
    Uses a global memory cache by default, or a provided cache instance.
    
    Args:
        ttl: Time-to-live in seconds
        key_builder: Optional function to build cache key from args/kwargs.
                    If not provided, uses function name + hashed args.
        cache: Optional cache instance to use (default: shared MemoryCache)
    
    Returns:
        Decorated function with caching behavior
    
    Example:
        >>> # Simple caching
        >>> @cached(ttl=600)
        ... def get_user_data(user_id: int) -> dict:
        ...     return fetch_from_db(user_id)
        
        >>> # Custom key builder
        >>> @cached(ttl=300, key_builder=lambda *args, **kwargs: f"user:{args[0]}")
        ... def get_user(user_id: int) -> dict:
        ...     return fetch_user(user_id)
        
        >>> # Async function caching
        >>> @cached(ttl=60)
        ... async def fetch_api_data(endpoint: str) -> dict:
        ...     return await http.get(endpoint)
    """
    # Shared cache for decorator instances without explicit cache
    _shared_cache: Cache = MemoryCache()
    
    def decorator(func: Callable) -> Callable:
        # Determine if function is async
        is_async = asyncio.iscoroutinefunction(func)
        
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Build cache key
            if key_builder:
                key = key_builder(*args, **kwargs)
            else:
                # Default key: function name + args hash
                args_key = str(args) + str(sorted(kwargs.items()))
                args_hash = hashlib.md5(args_key.encode()).hexdigest()[:16]
                key = f"{func.__module__}.{func.__qualname__}:{args_hash}"
            
            target_cache = cache or _shared_cache
            
            # Try to get from cache
            value = target_cache.get(key)
            if value is not None:
                return value
            
            # Call the function
            if is_async:
                # For async, we need to return a coroutine
                async def async_wrapper() -> Any:
                    result = await func(*args, **kwargs)
                    target_cache.set(key, result, ttl)
                    return result
                return async_wrapper()
            else:
                result = func(*args, **kwargs)
                target_cache.set(key, result, ttl)
                return result
        
        return wrapper
    
    return decorator


# Global shared cache instances
_memory_cache: Optional[MemoryCache] = None
_file_cache: Optional[FileCache] = None


def get_memory_cache(default_ttl: int = 300) -> MemoryCache:
    """
    Get or create a shared memory cache instance.
    
    Args:
        default_ttl: Default TTL for the cache
        
    Returns:
        Shared MemoryCache instance
    """
    global _memory_cache
    if _memory_cache is None:
        _memory_cache = MemoryCache(default_ttl=default_ttl)
    return _memory_cache


def get_file_cache(cache_dir: str, default_ttl: int = 3600) -> FileCache:
    """
    Get or create a shared file cache instance.
    
    Args:
        cache_dir: Directory for cache storage
        default_ttl: Default TTL for the cache
        
    Returns:
        Shared FileCache instance
    """
    global _file_cache
    if _file_cache is None or _file_cache._cache_dir != Path(cache_dir):
        _file_cache = FileCache(cache_dir=cache_dir, default_ttl=default_ttl)
    return _file_cache
