from __future__ import annotations

from collections import OrderedDict
from datetime import datetime, timedelta
from threading import Lock
from typing import Any, Dict, Optional, Tuple

DEFAULT_TTL_HOURS = 6
MAX_CACHE_SIZE = 50  # Maximum number of cached evaluations (prevents unbounded memory growth)

_CacheKey = Tuple[int, str]
_CacheValue = Tuple[datetime, Dict[str, Any]]

_memory_cache: OrderedDict[_CacheKey, _CacheValue] = OrderedDict()
_cache_lock = Lock()


def _is_expired(expiry: datetime) -> bool:
    return expiry < datetime.utcnow()


def _cleanup_expired() -> None:
    """Proactively remove all expired entries from cache to prevent memory leaks."""
    expired_keys = [
        key for key, (expiry, _) in _memory_cache.items()
        if _is_expired(expiry)
    ]
    for key in expired_keys:
        _memory_cache.pop(key, None)


def _evict_oldest() -> None:
    """Remove oldest entry when cache is full (LRU eviction strategy)."""
    if _memory_cache:
        _memory_cache.popitem(last=False)  # Remove oldest (FIFO)


def get_cached_payload(evaluation_id: int, cache_type: str) -> Optional[Dict[str, Any]]:
    key: _CacheKey = (evaluation_id, cache_type)
    with _cache_lock:
        entry = _memory_cache.get(key)
        if not entry:
            return None
        expires_at, payload = entry
        if _is_expired(expires_at):
            _memory_cache.pop(key, None)
            return None
        # Move to end to mark as recently used (LRU)
        _memory_cache.move_to_end(key)
        return payload


def set_cached_payload(
    evaluation_id: int,
    cache_type: str,
    payload: Dict[str, Any],
    ttl_hours: int = DEFAULT_TTL_HOURS,
) -> None:
    key: _CacheKey = (evaluation_id, cache_type)
    expires_at = datetime.utcnow() + timedelta(hours=ttl_hours)
    
    with _cache_lock:
        # Periodic cleanup of expired entries (every 10th insertion)
        if len(_memory_cache) % 10 == 0:
            _cleanup_expired()
        
        # Evict oldest entry if cache is at max capacity
        while len(_memory_cache) >= MAX_CACHE_SIZE:
            _evict_oldest()
        
        _memory_cache[key] = (expires_at, payload)
        # Move to end to mark as most recently used
        _memory_cache.move_to_end(key)


def clear_cache_entry(evaluation_id: int, cache_type: str) -> None:
    key: _CacheKey = (evaluation_id, cache_type)
    with _cache_lock:
        _memory_cache.pop(key, None)


def get_cache_stats() -> Dict[str, Any]:
    """Get cache statistics for monitoring and debugging."""
    with _cache_lock:
        total = len(_memory_cache)
        expired = sum(1 for expiry, _ in _memory_cache.values() if _is_expired(expiry))
        return {
            'total_entries': total,
            'expired_entries': expired,
            'active_entries': total - expired,
            'max_size': MAX_CACHE_SIZE,
            'utilization_percent': round((total / MAX_CACHE_SIZE * 100), 2) if MAX_CACHE_SIZE > 0 else 0,
        }
