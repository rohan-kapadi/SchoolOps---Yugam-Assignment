"""In-memory TTL cache for external API calls."""

from functools import wraps
import threading
import time
from typing import Any, Callable


class TTLCache:
    """Thread-safe in-memory cache with per-item time-to-live (TTL)."""

    def __init__(self) -> None:
        self._entries: dict[str, tuple[float, Any]] = {}
        self._lock = threading.Lock()

    def get(self, key: str) -> Any | None:
        """Retrieve value by key if not expired, otherwise return None."""
        with self._lock:
            entry = self._entries.get(key)
            if entry is None:
                return None
            expires_at, value = entry
            if time.monotonic() > expires_at:
                del self._entries[key]
                return None
            return value

    def set(self, key: str, value: Any, ttl_seconds: int | float) -> None:
        """Store value with expiration timestamp."""
        with self._lock:
            expires_at = time.monotonic() + ttl_seconds
            self._entries[key] = (expires_at, value)

    def delete(self, key: str) -> None:
        """Remove a key from cache."""
        with self._lock:
            self._entries.pop(key, None)

    def clear(self) -> None:
        """Clear all cache entries."""
        with self._lock:
            self._entries.clear()

    def __len__(self) -> int:
        with self._lock:
            now = time.monotonic()
            return sum(1 for _, (exp, _) in self._entries.items() if exp > now)


# Global cache instance for tools
default_cache = TTLCache()


def ttl_cache(ttl_seconds: int | float, cache_instance: TTLCache | None = None):
    """Decorator to cache function results with a TTL.

    Only caches successful tool responses (status == 'ok') so transient errors
    or timeouts are never permanently cached.
    """
    cache = cache_instance or default_cache

    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Exclude client or mock instances from cache key calculation
            cache_kwargs = {k: v for k, v in kwargs.items() if k != "client"}

            # Normalize float args for consistent cache keys
            norm_args = [round(a, 4) if isinstance(a, float) else a for a in args]
            norm_kwargs = {
                k: round(v, 4) if isinstance(v, float) else v
                for k, v in sorted(cache_kwargs.items())
            }
            cache_key = f"{func.__name__}:{repr(norm_args)}:{repr(norm_kwargs)}"

            cached_value = cache.get(cache_key)
            if cached_value is not None:
                return cached_value

            result = func(*args, **kwargs)

            # Only cache if successful response
            if isinstance(result, dict) and result.get("status") == "ok":
                cache.set(cache_key, result, ttl_seconds)

            return result

        wrapper.clear_cache = lambda: cache.clear()
        wrapper.cache = cache
        return wrapper

    return decorator
