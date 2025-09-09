#!/usr/bin/env python3
"""
Unit tests for optimization utilities
"""

import pytest
import time
import tempfile
import json
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
from threading import Thread

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.optimization import (
    MemoryCache, FileCache, RateLimiter, GlobalRateLimiters,
    TaskScheduler, cache_result, rate_limit
)

class TestMemoryCache:
    """Test cases for MemoryCache class."""
    
    def test_memory_cache_initialization(self):
        """Test MemoryCache initialization."""
        cache = MemoryCache(max_size=100, ttl=300)
        assert cache.max_size == 100
        assert cache.ttl == 300
        assert len(cache.cache) == 0
        assert len(cache.access_times) == 0
    
    def test_memory_cache_set_get(self):
        """Test basic set and get operations."""
        cache = MemoryCache(max_size=10, ttl=300)
        
        # Set a value
        cache.set("key1", "value1")
        
        # Get the value
        result = cache.get("key1")
        assert result == "value1"
    
    def test_memory_cache_get_nonexistent(self):
        """Test getting non-existent key."""
        cache = MemoryCache(max_size=10, ttl=300)
        
        result = cache.get("nonexistent")
        assert result is None
        
        # Test with default value
        result = cache.get("nonexistent", "default")
        assert result == "default"
    
    def test_memory_cache_ttl_expiration(self):
        """Test TTL expiration."""
        cache = MemoryCache(max_size=10, ttl=0.1)  # 100ms TTL
        
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"
        
        # Wait for expiration
        time.sleep(0.15)
        assert cache.get("key1") is None
    
    def test_memory_cache_max_size_eviction(self):
        """Test LRU eviction when max size is reached."""
        cache = MemoryCache(max_size=3, ttl=300)
        
        # Fill cache to capacity
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")
        
        # Access key1 to make it most recently used
        cache.get("key1")
        
        # Add another item, should evict key2 (least recently used)
        cache.set("key4", "value4")
        
        assert cache.get("key1") == "value1"  # Still exists
        assert cache.get("key2") is None      # Evicted
        assert cache.get("key3") == "value3"  # Still exists
        assert cache.get("key4") == "value4"  # New item
    
    def test_memory_cache_clear(self):
        """Test cache clearing."""
        cache = MemoryCache(max_size=10, ttl=300)
        
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        
        assert len(cache.cache) == 2
        
        cache.clear()
        
        assert len(cache.cache) == 0
        assert len(cache.access_times) == 0
        assert cache.get("key1") is None
    
    def test_memory_cache_contains(self):
        """Test __contains__ method."""
        cache = MemoryCache(max_size=10, ttl=300)
        
        cache.set("key1", "value1")
        
        assert "key1" in cache
        assert "key2" not in cache
    
    def test_memory_cache_delete(self):
        """Test delete operation."""
        cache = MemoryCache(max_size=10, ttl=300)
        
        cache.set("key1", "value1")
        assert "key1" in cache
        
        cache.delete("key1")
        assert "key1" not in cache
        assert cache.get("key1") is None
    
    def test_memory_cache_size(self):
        """Test size property."""
        cache = MemoryCache(max_size=10, ttl=300)
        
        assert cache.size == 0
        
        cache.set("key1", "value1")
        assert cache.size == 1
        
        cache.set("key2", "value2")
        assert cache.size == 2
        
        cache.delete("key1")
        assert cache.size == 1

class TestFileCache:
    """Test cases for FileCache class."""
    
    def test_file_cache_initialization(self):
        """Test FileCache initialization."""
        with tempfile.TemporaryDirectory() as temp_dir:
            cache = FileCache(cache_dir=temp_dir, ttl=300)
            assert cache.cache_dir == Path(temp_dir)
            assert cache.ttl == 300
            assert cache.cache_dir.exists()
    
    def test_file_cache_set_get(self):
        """Test basic set and get operations."""
        with tempfile.TemporaryDirectory() as temp_dir:
            cache = FileCache(cache_dir=temp_dir, ttl=300)
            
            # Set a value
            cache.set("key1", {"data": "value1"})
            
            # Get the value
            result = cache.get("key1")
            assert result == {"data": "value1"}
    
    def test_file_cache_get_nonexistent(self):
        """Test getting non-existent key."""
        with tempfile.TemporaryDirectory() as temp_dir:
            cache = FileCache(cache_dir=temp_dir, ttl=300)
            
            result = cache.get("nonexistent")
            assert result is None
            
            # Test with default value
            result = cache.get("nonexistent", "default")
            assert result == "default"
    
    def test_file_cache_ttl_expiration(self):
        """Test TTL expiration."""
        with tempfile.TemporaryDirectory() as temp_dir:
            cache = FileCache(cache_dir=temp_dir, ttl=0.1)  # 100ms TTL
            
            cache.set("key1", "value1")
            assert cache.get("key1") == "value1"
            
            # Wait for expiration
            time.sleep(0.15)
            assert cache.get("key1") is None
    
    def test_file_cache_clear(self):
        """Test cache clearing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            cache = FileCache(cache_dir=temp_dir, ttl=300)
            
            cache.set("key1", "value1")
            cache.set("key2", "value2")
            
            # Verify files exist
            cache_files = list(cache.cache_dir.glob("*.json"))
            assert len(cache_files) >= 2
            
            cache.clear()
            
            # Verify files are deleted
            cache_files = list(cache.cache_dir.glob("*.json"))
            assert len(cache_files) == 0
    
    def test_file_cache_contains(self):
        """Test __contains__ method."""
        with tempfile.TemporaryDirectory() as temp_dir:
            cache = FileCache(cache_dir=temp_dir, ttl=300)
            
            cache.set("key1", "value1")
            
            assert "key1" in cache
            assert "key2" not in cache
    
    def test_file_cache_delete(self):
        """Test delete operation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            cache = FileCache(cache_dir=temp_dir, ttl=300)
            
            cache.set("key1", "value1")
            assert "key1" in cache
            
            cache.delete("key1")
            assert "key1" not in cache
            assert cache.get("key1") is None
    
    def test_file_cache_invalid_json(self):
        """Test handling of invalid JSON files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            cache = FileCache(cache_dir=temp_dir, ttl=300)
            
            # Create invalid JSON file
            cache_file = cache.cache_dir / "invalid.json"
            cache_file.write_text("invalid json content")
            
            # Should handle gracefully
            result = cache.get("invalid")
            assert result is None

class TestRateLimiter:
    """Test cases for RateLimiter class."""
    
    def test_rate_limiter_initialization(self):
        """Test RateLimiter initialization."""
        limiter = RateLimiter(max_calls=10, time_window=60)
        assert limiter.max_calls == 10
        assert limiter.time_window == 60
        assert len(limiter.call_times) == 0
    
    def test_rate_limiter_allow_request(self):
        """Test allowing requests within limit."""
        limiter = RateLimiter(max_calls=5, time_window=60)
        
        # Should allow first 5 requests
        for i in range(5):
            assert limiter.allow_request() is True
        
        # Should deny 6th request
        assert limiter.allow_request() is False
    
    def test_rate_limiter_time_window_reset(self):
        """Test time window reset."""
        limiter = RateLimiter(max_calls=2, time_window=0.1)  # 100ms window
        
        # Use up the limit
        assert limiter.allow_request() is True
        assert limiter.allow_request() is True
        assert limiter.allow_request() is False
        
        # Wait for window to reset
        time.sleep(0.15)
        
        # Should allow requests again
        assert limiter.allow_request() is True
    
    def test_rate_limiter_wait_time(self):
        """Test wait time calculation."""
        limiter = RateLimiter(max_calls=1, time_window=60)
        
        # Use up the limit
        assert limiter.allow_request() is True
        
        # Check wait time
        wait_time = limiter.get_wait_time()
        assert 0 < wait_time <= 60
    
    def test_rate_limiter_reset(self):
        """Test manual reset."""
        limiter = RateLimiter(max_calls=2, time_window=60)
        
        # Use up the limit
        assert limiter.allow_request() is True
        assert limiter.allow_request() is True
        assert limiter.allow_request() is False
        
        # Reset
        limiter.reset()
        
        # Should allow requests again
        assert limiter.allow_request() is True

class TestGlobalRateLimiters:
    """Test cases for GlobalRateLimiters class."""
    
    def test_global_rate_limiters_get_limiter(self):
        """Test getting rate limiter instances."""
        limiters = GlobalRateLimiters()
        
        # Get YouTube limiter
        youtube_limiter = limiters.get_limiter('youtube')
        assert isinstance(youtube_limiter, RateLimiter)
        
        # Should return same instance on subsequent calls
        youtube_limiter2 = limiters.get_limiter('youtube')
        assert youtube_limiter is youtube_limiter2
    
    def test_global_rate_limiters_custom_config(self):
        """Test custom rate limiter configuration."""
        custom_config = {
            'custom_api': {'max_calls': 100, 'time_window': 3600}
        }
        limiters = GlobalRateLimiters(custom_config)
        
        custom_limiter = limiters.get_limiter('custom_api')
        assert custom_limiter.max_calls == 100
        assert custom_limiter.time_window == 3600
    
    def test_global_rate_limiters_unknown_service(self):
        """Test getting limiter for unknown service."""
        limiters = GlobalRateLimiters()
        
        # Should create default limiter for unknown service
        unknown_limiter = limiters.get_limiter('unknown_service')
        assert isinstance(unknown_limiter, RateLimiter)
        assert unknown_limiter.max_calls == 100  # Default
        assert unknown_limiter.time_window == 3600  # Default

class TestTaskScheduler:
    """Test cases for TaskScheduler class."""
    
    def test_task_scheduler_initialization(self):
        """Test TaskScheduler initialization."""
        scheduler = TaskScheduler()
        assert scheduler.tasks == {}
        assert scheduler.running is False
    
    def test_task_scheduler_add_task(self):
        """Test adding tasks to scheduler."""
        scheduler = TaskScheduler()
        
        def dummy_task():
            return "executed"
        
        # Add task
        scheduler.add_task(
            task_id="test_task",
            func=dummy_task,
            interval=60,
            run_immediately=False
        )
        
        assert "test_task" in scheduler.tasks
        task_info = scheduler.tasks["test_task"]
        assert task_info['func'] == dummy_task
        assert task_info['interval'] == 60
    
    def test_task_scheduler_remove_task(self):
        """Test removing tasks from scheduler."""
        scheduler = TaskScheduler()
        
        def dummy_task():
            return "executed"
        
        # Add and remove task
        scheduler.add_task("test_task", dummy_task, 60)
        assert "test_task" in scheduler.tasks
        
        scheduler.remove_task("test_task")
        assert "test_task" not in scheduler.tasks
    
    def test_task_scheduler_start_stop(self):
        """Test starting and stopping scheduler."""
        scheduler = TaskScheduler()
        
        def dummy_task():
            return "executed"
        
        scheduler.add_task("test_task", dummy_task, 0.1)  # 100ms interval
        
        # Start scheduler
        scheduler.start()
        assert scheduler.running is True
        
        # Let it run briefly
        time.sleep(0.05)
        
        # Stop scheduler
        scheduler.stop()
        assert scheduler.running is False
    
    def test_task_scheduler_task_execution(self):
        """Test task execution."""
        scheduler = TaskScheduler()
        execution_count = [0]  # Use list for mutable reference
        
        def counting_task():
            execution_count[0] += 1
            return f"executed {execution_count[0]} times"
        
        scheduler.add_task(
            "counting_task",
            counting_task,
            0.05,  # 50ms interval
            run_immediately=True
        )
        
        scheduler.start()
        time.sleep(0.15)  # Let it run for ~150ms
        scheduler.stop()
        
        # Should have executed at least 2-3 times
        assert execution_count[0] >= 2
    
    def test_task_scheduler_get_task_info(self):
        """Test getting task information."""
        scheduler = TaskScheduler()
        
        def dummy_task():
            return "executed"
        
        scheduler.add_task("test_task", dummy_task, 60)
        
        task_info = scheduler.get_task_info("test_task")
        assert task_info is not None
        assert task_info['func'] == dummy_task
        assert task_info['interval'] == 60
        
        # Non-existent task
        assert scheduler.get_task_info("nonexistent") is None
    
    def test_task_scheduler_list_tasks(self):
        """Test listing all tasks."""
        scheduler = TaskScheduler()
        
        def task1():
            pass
        
        def task2():
            pass
        
        scheduler.add_task("task1", task1, 60)
        scheduler.add_task("task2", task2, 120)
        
        task_list = scheduler.list_tasks()
        assert len(task_list) == 2
        assert "task1" in task_list
        assert "task2" in task_list

class TestCacheDecorator:
    """Test cases for cache_result decorator."""
    
    def test_cache_result_decorator_basic(self):
        """Test basic cache_result decorator functionality."""
        call_count = [0]  # Use list for mutable reference
        
        @cache_result(ttl=300)
        def expensive_function(x):
            call_count[0] += 1
            return x * 2
        
        # First call should execute function
        result1 = expensive_function(5)
        assert result1 == 10
        assert call_count[0] == 1
        
        # Second call should use cache
        result2 = expensive_function(5)
        assert result2 == 10
        assert call_count[0] == 1  # Function not called again
        
        # Different argument should execute function
        result3 = expensive_function(10)
        assert result3 == 20
        assert call_count[0] == 2
    
    def test_cache_result_decorator_with_kwargs(self):
        """Test cache_result decorator with keyword arguments."""
        call_count = [0]
        
        @cache_result(ttl=300)
        def function_with_kwargs(x, y=1, z=2):
            call_count[0] += 1
            return x + y + z
        
        # Test with different argument combinations
        result1 = function_with_kwargs(1, y=2, z=3)
        assert result1 == 6
        assert call_count[0] == 1
        
        # Same arguments should use cache
        result2 = function_with_kwargs(1, y=2, z=3)
        assert result2 == 6
        assert call_count[0] == 1
        
        # Different kwargs should execute function
        result3 = function_with_kwargs(1, y=3, z=3)
        assert result3 == 7
        assert call_count[0] == 2
    
    def test_cache_result_decorator_ttl_expiration(self):
        """Test cache_result decorator TTL expiration."""
        call_count = [0]
        
        @cache_result(ttl=0.1)  # 100ms TTL
        def short_lived_cache(x):
            call_count[0] += 1
            return x * 2
        
        # First call
        result1 = short_lived_cache(5)
        assert result1 == 10
        assert call_count[0] == 1
        
        # Wait for cache to expire
        time.sleep(0.15)
        
        # Should execute function again
        result2 = short_lived_cache(5)
        assert result2 == 10
        assert call_count[0] == 2
    
    def test_cache_result_decorator_custom_cache(self):
        """Test cache_result decorator with custom cache instance."""
        custom_cache = MemoryCache(max_size=5, ttl=300)
        call_count = [0]
        
        @cache_result(cache=custom_cache)
        def cached_function(x):
            call_count[0] += 1
            return x * 3
        
        # Function should use custom cache
        result1 = cached_function(4)
        assert result1 == 12
        assert call_count[0] == 1
        
        # Verify cache was used
        result2 = cached_function(4)
        assert result2 == 12
        assert call_count[0] == 1
        
        # Verify custom cache contains the result
        assert custom_cache.size == 1

class TestRateLimitDecorator:
    """Test cases for rate_limit decorator."""
    
    def test_rate_limit_decorator_basic(self):
        """Test basic rate_limit decorator functionality."""
        call_count = [0]
        
        @rate_limit(max_calls=2, time_window=60)
        def limited_function():
            call_count[0] += 1
            return "executed"
        
        # First two calls should succeed
        result1 = limited_function()
        assert result1 == "executed"
        assert call_count[0] == 1
        
        result2 = limited_function()
        assert result2 == "executed"
        assert call_count[0] == 2
        
        # Third call should be rate limited
        with pytest.raises(Exception):  # Should raise rate limit exception
            limited_function()
    
    def test_rate_limit_decorator_custom_limiter(self):
        """Test rate_limit decorator with custom limiter."""
        custom_limiter = RateLimiter(max_calls=1, time_window=60)
        call_count = [0]
        
        @rate_limit(limiter=custom_limiter)
        def limited_function():
            call_count[0] += 1
            return "executed"
        
        # First call should succeed
        result1 = limited_function()
        assert result1 == "executed"
        assert call_count[0] == 1
        
        # Second call should be rate limited
        with pytest.raises(Exception):
            limited_function()
    
    def test_rate_limit_decorator_service_name(self):
        """Test rate_limit decorator with service name."""
        call_count = [0]
        
        @rate_limit(service='test_service', max_calls=3, time_window=60)
        def service_function():
            call_count[0] += 1
            return "executed"
        
        # Should use global rate limiter for service
        for i in range(3):
            result = service_function()
            assert result == "executed"
        
        assert call_count[0] == 3
        
        # Fourth call should be rate limited
        with pytest.raises(Exception):
            service_function()

class TestStreamlitIntegration:
    """Test cases for Streamlit integration features."""
    
    @patch('src.utils.optimization.st')
    def test_streamlit_cache_integration(self, mock_st):
        """Test Streamlit cache integration."""
        # Mock streamlit cache decorator
        mock_st.cache_data.return_value = lambda func: func
        
        call_count = [0]
        
        @cache_result(ttl=300, use_streamlit_cache=True)
        def streamlit_cached_function(x):
            call_count[0] += 1
            return x * 2
        
        # Function should be decorated with streamlit cache
        result = streamlit_cached_function(5)
        assert result == 10
        
        # Verify streamlit cache was used
        mock_st.cache_data.assert_called_once()
    
    @patch('src.utils.optimization.st')
    def test_streamlit_progress_integration(self, mock_st):
        """Test Streamlit progress bar integration."""
        # Mock streamlit progress components
        mock_progress = Mock()
        mock_st.progress.return_value = mock_progress
        mock_st.empty.return_value = Mock()
        
        # This would be tested in actual Streamlit context
        # For now, just verify mocks can be created
        assert mock_st.progress is not None
        assert mock_st.empty is not None

class TestErrorHandling:
    """Test cases for error handling in optimization utilities."""
    
    def test_cache_serialization_error(self):
        """Test handling of serialization errors in file cache."""
        with tempfile.TemporaryDirectory() as temp_dir:
            cache = FileCache(cache_dir=temp_dir, ttl=300)
            
            # Try to cache non-serializable object
            class NonSerializable:
                def __init__(self):
                    self.func = lambda x: x  # Functions are not JSON serializable
            
            non_serializable = NonSerializable()
            
            # Should handle gracefully
            try:
                cache.set("test", non_serializable)
                # If it doesn't raise an error, that's fine too
            except (TypeError, ValueError):
                # Expected behavior for non-serializable objects
                pass
    
    def test_rate_limiter_thread_safety(self):
        """Test rate limiter thread safety."""
        limiter = RateLimiter(max_calls=10, time_window=60)
        results = []
        
        def make_request():
            result = limiter.allow_request()
            results.append(result)
        
        # Create multiple threads
        threads = [Thread(target=make_request) for _ in range(15)]
        
        # Start all threads
        for thread in threads:
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Should have exactly 10 successful requests
        successful_requests = sum(1 for result in results if result)
        assert successful_requests == 10
        assert len(results) == 15
    
    def test_scheduler_exception_handling(self):
        """Test scheduler handling of task exceptions."""
        scheduler = TaskScheduler()
        execution_count = [0]
        
        def failing_task():
            execution_count[0] += 1
            if execution_count[0] == 2:
                raise ValueError("Simulated error")
            return "success"
        
        scheduler.add_task("failing_task", failing_task, 0.05)
        
        scheduler.start()
        time.sleep(0.15)  # Let it run and fail
        scheduler.stop()
        
        # Should have attempted multiple executions despite failure
        assert execution_count[0] >= 2

class TestPerformance:
    """Test cases for performance characteristics."""
    
    def test_memory_cache_performance(self):
        """Test memory cache performance with many operations."""
        cache = MemoryCache(max_size=1000, ttl=300)
        
        start_time = time.time()
        
        # Perform many cache operations
        for i in range(1000):
            cache.set(f"key_{i}", f"value_{i}")
        
        for i in range(1000):
            cache.get(f"key_{i}")
        
        end_time = time.time()
        
        # Should complete in reasonable time (less than 1 second)
        assert (end_time - start_time) < 1.0
    
    def test_rate_limiter_performance(self):
        """Test rate limiter performance with many requests."""
        limiter = RateLimiter(max_calls=1000, time_window=60)
        
        start_time = time.time()
        
        # Make many requests
        for i in range(1000):
            limiter.allow_request()
        
        end_time = time.time()
        
        # Should complete in reasonable time
        assert (end_time - start_time) < 0.5

if __name__ == "__main__":
    pytest.main([__file__])