#!/usr/bin/env python3
"""
Optimization Utilities - Caching, rate limiting, and scheduling functionality
"""

import time
import threading
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Callable, List
from functools import wraps
import hashlib
import json
import pickle
import os
from pathlib import Path
import logging
from dataclasses import dataclass
from collections import defaultdict, deque
import schedule
import streamlit as st

from .config import get_config

logger = logging.getLogger(__name__)

@dataclass
class CacheEntry:
    """Cache entry with value and metadata."""
    value: Any
    timestamp: float
    ttl: float
    hits: int = 0
    
    @property
    def is_expired(self) -> bool:
        """Check if cache entry is expired."""
        return time.time() - self.timestamp > self.ttl
    
    @property
    def age(self) -> float:
        """Get age of cache entry in seconds."""
        return time.time() - self.timestamp

class MemoryCache:
    """In-memory cache with TTL support."""
    
    def __init__(self, default_ttl: int = 3600, max_size: int = 1000):
        self.default_ttl = default_ttl
        self.max_size = max_size
        self._cache: Dict[str, CacheEntry] = {}
        self._access_order: deque = deque()
        self._lock = threading.RLock()
        
    def _generate_key(self, func_name: str, args: tuple, kwargs: dict) -> str:
        """Generate cache key from function name and arguments."""
        key_data = {
            'func': func_name,
            'args': args,
            'kwargs': sorted(kwargs.items())
        }
        key_str = json.dumps(key_data, sort_keys=True, default=str)
        return hashlib.md5(key_str.encode()).hexdigest()
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        with self._lock:
            if key in self._cache:
                entry = self._cache[key]
                if not entry.is_expired:
                    entry.hits += 1
                    # Move to end (most recently used)
                    if key in self._access_order:
                        self._access_order.remove(key)
                    self._access_order.append(key)
                    return entry.value
                else:
                    # Remove expired entry
                    del self._cache[key]
                    if key in self._access_order:
                        self._access_order.remove(key)
            return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value in cache."""
        with self._lock:
            ttl = ttl or self.default_ttl
            
            # Remove old entry if exists
            if key in self._cache:
                if key in self._access_order:
                    self._access_order.remove(key)
            
            # Check if we need to evict entries
            while len(self._cache) >= self.max_size:
                if self._access_order:
                    oldest_key = self._access_order.popleft()
                    if oldest_key in self._cache:
                        del self._cache[oldest_key]
                else:
                    break
            
            # Add new entry
            self._cache[key] = CacheEntry(
                value=value,
                timestamp=time.time(),
                ttl=ttl
            )
            self._access_order.append(key)
    
    def delete(self, key: str) -> bool:
        """Delete entry from cache."""
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                if key in self._access_order:
                    self._access_order.remove(key)
                return True
            return False
    
    def clear(self) -> None:
        """Clear all cache entries."""
        with self._lock:
            self._cache.clear()
            self._access_order.clear()
    
    def cleanup_expired(self) -> int:
        """Remove expired entries and return count removed."""
        with self._lock:
            expired_keys = [
                key for key, entry in self._cache.items()
                if entry.is_expired
            ]
            
            for key in expired_keys:
                del self._cache[key]
                if key in self._access_order:
                    self._access_order.remove(key)
            
            return len(expired_keys)
    
    def stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self._lock:
            total_hits = sum(entry.hits for entry in self._cache.values())
            return {
                'size': len(self._cache),
                'max_size': self.max_size,
                'total_hits': total_hits,
                'expired_count': sum(1 for entry in self._cache.values() if entry.is_expired)
            }

class FileCache:
    """File-based cache for persistent storage."""
    
    def __init__(self, cache_dir: str = ".cache", default_ttl: int = 3600):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.default_ttl = default_ttl
        self._lock = threading.RLock()
    
    def _get_file_path(self, key: str) -> Path:
        """Get file path for cache key."""
        return self.cache_dir / f"{key}.cache"
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from file cache."""
        with self._lock:
            file_path = self._get_file_path(key)
            
            if not file_path.exists():
                return None
            
            try:
                with open(file_path, 'rb') as f:
                    entry = pickle.load(f)
                
                if not entry.is_expired:
                    entry.hits += 1
                    # Update hits count
                    with open(file_path, 'wb') as f:
                        pickle.dump(entry, f)
                    return entry.value
                else:
                    # Remove expired file
                    file_path.unlink(missing_ok=True)
                    return None
                    
            except Exception as e:
                logger.warning(f"Error reading cache file {file_path}: {e}")
                file_path.unlink(missing_ok=True)
                return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value in file cache."""
        with self._lock:
            ttl = ttl or self.default_ttl
            file_path = self._get_file_path(key)
            
            entry = CacheEntry(
                value=value,
                timestamp=time.time(),
                ttl=ttl
            )
            
            try:
                with open(file_path, 'wb') as f:
                    pickle.dump(entry, f)
            except Exception as e:
                logger.error(f"Error writing cache file {file_path}: {e}")
    
    def delete(self, key: str) -> bool:
        """Delete entry from file cache."""
        with self._lock:
            file_path = self._get_file_path(key)
            if file_path.exists():
                file_path.unlink()
                return True
            return False
    
    def clear(self) -> None:
        """Clear all cache files."""
        with self._lock:
            for file_path in self.cache_dir.glob("*.cache"):
                file_path.unlink(missing_ok=True)
    
    def cleanup_expired(self) -> int:
        """Remove expired cache files."""
        with self._lock:
            removed_count = 0
            
            for file_path in self.cache_dir.glob("*.cache"):
                try:
                    with open(file_path, 'rb') as f:
                        entry = pickle.load(f)
                    
                    if entry.is_expired:
                        file_path.unlink()
                        removed_count += 1
                        
                except Exception:
                    # Remove corrupted files
                    file_path.unlink(missing_ok=True)
                    removed_count += 1
            
            return removed_count

class RateLimiter:
    """Token bucket rate limiter."""
    
    def __init__(self, requests_per_window: int, window_seconds: int):
        self.requests_per_window = requests_per_window
        self.window_seconds = window_seconds
        self.tokens = requests_per_window
        self.last_refill = time.time()
        self._lock = threading.RLock()
    
    def acquire(self, tokens: int = 1) -> bool:
        """Try to acquire tokens. Returns True if successful."""
        with self._lock:
            now = time.time()
            
            # Refill tokens based on elapsed time
            elapsed = now - self.last_refill
            tokens_to_add = elapsed * (self.requests_per_window / self.window_seconds)
            self.tokens = min(self.requests_per_window, self.tokens + tokens_to_add)
            self.last_refill = now
            
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            
            return False
    
    def wait_time(self, tokens: int = 1) -> float:
        """Get time to wait before tokens are available."""
        with self._lock:
            if self.tokens >= tokens:
                return 0.0
            
            tokens_needed = tokens - self.tokens
            return tokens_needed * (self.window_seconds / self.requests_per_window)
    
    def reset(self) -> None:
        """Reset rate limiter."""
        with self._lock:
            self.tokens = self.requests_per_window
            self.last_refill = time.time()

class GlobalRateLimiters:
    """Global rate limiters for different APIs."""
    
    def __init__(self):
        config = get_config()
        
        # YouTube Data API: 10,000 units per day
        self.youtube_data = RateLimiter(
            requests_per_window=config.rate_limit_requests,
            window_seconds=config.rate_limit_window
        )
        
        # YouTube Analytics API: 50,000 requests per day
        self.youtube_analytics = RateLimiter(
            requests_per_window=50,  # Conservative limit
            window_seconds=3600  # Per hour
        )
        
        # Gemini API: Depends on tier, default conservative
        self.gemini = RateLimiter(
            requests_per_window=60,  # 60 requests per minute
            window_seconds=60
        )

# Global instances
_memory_cache = None
_file_cache = None
_rate_limiters = None

def get_memory_cache() -> MemoryCache:
    """Get global memory cache instance."""
    global _memory_cache
    if _memory_cache is None:
        config = get_config()
        _memory_cache = MemoryCache(default_ttl=config.cache_ttl)
    return _memory_cache

def get_file_cache() -> FileCache:
    """Get global file cache instance."""
    global _file_cache
    if _file_cache is None:
        config = get_config()
        _file_cache = FileCache(default_ttl=config.cache_ttl)
    return _file_cache

def get_rate_limiters() -> GlobalRateLimiters:
    """Get global rate limiters instance."""
    global _rate_limiters
    if _rate_limiters is None:
        _rate_limiters = GlobalRateLimiters()
    return _rate_limiters

def cached(ttl: Optional[int] = None, 
          use_file_cache: bool = False,
          key_prefix: str = ""):
    """Decorator for caching function results."""
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            cache = get_file_cache() if use_file_cache else get_memory_cache()
            
            # Generate cache key
            func_name = f"{key_prefix}{func.__module__}.{func.__name__}"
            key = cache._generate_key(func_name, args, kwargs) if hasattr(cache, '_generate_key') else f"{func_name}_{hash((args, tuple(sorted(kwargs.items()))))}"
            
            # Try to get from cache
            result = cache.get(key)
            if result is not None:
                return result
            
            # Execute function and cache result
            result = func(*args, **kwargs)
            cache.set(key, result, ttl)
            
            return result
        
        return wrapper
    return decorator

def rate_limited(limiter_name: str, tokens: int = 1, wait: bool = True):
    """Decorator for rate limiting function calls."""
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            limiters = get_rate_limiters()
            limiter = getattr(limiters, limiter_name, None)
            
            if limiter is None:
                logger.warning(f"Rate limiter '{limiter_name}' not found")
                return func(*args, **kwargs)
            
            if not limiter.acquire(tokens):
                if wait:
                    wait_time = limiter.wait_time(tokens)
                    logger.info(f"Rate limit reached, waiting {wait_time:.2f} seconds")
                    time.sleep(wait_time)
                    limiter.acquire(tokens)  # Should succeed now
                else:
                    raise Exception(f"Rate limit exceeded for {limiter_name}")
            
            return func(*args, **kwargs)
        
        return wrapper
    return decorator

class TaskScheduler:
    """Simple task scheduler for background operations."""
    
    def __init__(self):
        self.jobs: List[Callable] = []
        self.running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.RLock()
    
    def add_job(self, func: Callable, interval_hours: int = 24, 
               run_immediately: bool = False) -> None:
        """Add a scheduled job."""
        with self._lock:
            if interval_hours > 0:
                schedule.every(interval_hours).hours.do(func)
            
            if run_immediately:
                self.jobs.append(func)
    
    def start(self) -> None:
        """Start the scheduler."""
        with self._lock:
            if self.running:
                return
            
            self.running = True
            self._thread = threading.Thread(target=self._run_scheduler, daemon=True)
            self._thread.start()
            logger.info("Task scheduler started")
    
    def stop(self) -> None:
        """Stop the scheduler."""
        with self._lock:
            self.running = False
            if self._thread:
                self._thread.join(timeout=5)
            logger.info("Task scheduler stopped")
    
    def _run_scheduler(self) -> None:
        """Run the scheduler loop."""
        # Run immediate jobs
        for job in self.jobs:
            try:
                job()
            except Exception as e:
                logger.error(f"Error running immediate job: {e}")
        
        # Run scheduled jobs
        while self.running:
            try:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
            except Exception as e:
                logger.error(f"Error in scheduler: {e}")
                time.sleep(60)

# Global scheduler instance
_scheduler = None

def get_scheduler() -> TaskScheduler:
    """Get global scheduler instance."""
    global _scheduler
    if _scheduler is None:
        _scheduler = TaskScheduler()
    return _scheduler

def cleanup_caches() -> Dict[str, int]:
    """Cleanup expired cache entries."""
    results = {}
    
    try:
        memory_cache = get_memory_cache()
        results['memory_expired'] = memory_cache.cleanup_expired()
    except Exception as e:
        logger.error(f"Error cleaning memory cache: {e}")
        results['memory_expired'] = 0
    
    try:
        file_cache = get_file_cache()
        results['file_expired'] = file_cache.cleanup_expired()
    except Exception as e:
        logger.error(f"Error cleaning file cache: {e}")
        results['file_expired'] = 0
    
    return results

def get_cache_stats() -> Dict[str, Any]:
    """Get comprehensive cache statistics."""
    stats = {}
    
    try:
        memory_cache = get_memory_cache()
        stats['memory'] = memory_cache.stats()
    except Exception as e:
        logger.error(f"Error getting memory cache stats: {e}")
        stats['memory'] = {'error': str(e)}
    
    try:
        file_cache = get_file_cache()
        cache_files = list(file_cache.cache_dir.glob("*.cache"))
        total_size = sum(f.stat().st_size for f in cache_files)
        stats['file'] = {
            'file_count': len(cache_files),
            'total_size_bytes': total_size,
            'total_size_mb': total_size / (1024 * 1024)
        }
    except Exception as e:
        logger.error(f"Error getting file cache stats: {e}")
        stats['file'] = {'error': str(e)}
    
    return stats

# Streamlit integration
def st_cache_data_with_ttl(ttl: int = 3600):
    """Streamlit cache decorator with TTL."""
    return st.cache_data(ttl=ttl, show_spinner=False)

def st_cache_resource_with_ttl(ttl: int = 3600):
    """Streamlit resource cache decorator with TTL."""
    return st.cache_resource(ttl=ttl, show_spinner=False)

# Initialize scheduler if enabled
def initialize_optimization():
    """Initialize optimization features."""
    config = get_config()
    
    if config.schedule_enabled:
        scheduler = get_scheduler()
        
        # Add cache cleanup job
        scheduler.add_job(
            cleanup_caches,
            interval_hours=6  # Cleanup every 6 hours
        )
        
        scheduler.start()
        logger.info("Optimization features initialized")

# Auto-initialize when module is imported
if get_config().schedule_enabled:
    try:
        initialize_optimization()
    except Exception as e:
        logger.warning(f"Failed to initialize optimization features: {e}")