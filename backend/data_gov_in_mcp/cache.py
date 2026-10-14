"""
Caching layer for API responses
"""

import time
import hashlib
import json
from typing import Optional, Any, Dict
from collections import OrderedDict
from threading import Lock


class CacheEntry:
    """Represents a cached entry with TTL"""

    def __init__(self, value: Any, ttl: int):
        self.value = value
        self.expiry = time.time() + ttl

    def is_expired(self) -> bool:
        """Check if cache entry has expired"""
        return time.time() > self.expiry


class Cache:
    """Thread-safe LRU cache with TTL support"""

    def __init__(self, max_size: int = 1000, default_ttl: int = 3600):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = Lock()
        self._hits = 0
        self._misses = 0

    def _make_key(self, *args, **kwargs) -> str:
        """Generate cache key from arguments"""
        key_dict = {
            "args": args,
            "kwargs": sorted(kwargs.items())
        }
        key_str = json.dumps(key_dict, sort_keys=True, default=str)
        return hashlib.sha256(key_str.encode()).hexdigest()

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache if exists and not expired"""
        with self._lock:
            if key in self._cache:
                entry = self._cache[key]
                if entry.is_expired():
                    del self._cache[key]
                    self._misses += 1
                    return None
                # Move to end (most recently used)
                self._cache.move_to_end(key)
                self._hits += 1
                return entry.value
            self._misses += 1
            return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value in cache with TTL"""
        with self._lock:
            if key in self._cache:
                del self._cache[key]
            elif len(self._cache) >= self.max_size:
                # Remove least recently used
                self._cache.popitem(last=False)

            ttl = ttl or self.default_ttl
            self._cache[key] = CacheEntry(value, ttl)

    def clear(self) -> None:
        """Clear all cache entries"""
        with self._lock:
            self._cache.clear()
            self._hits = 0
            self._misses = 0

    def stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        with self._lock:
            total = self._hits + self._misses
            hit_rate = (self._hits / total * 100) if total > 0 else 0
            return {
                "size": len(self._cache),
                "max_size": self.max_size,
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": f"{hit_rate:.2f}%"
            }
