"""Concurrency limiting and rate limiting utilities."""

import asyncio
import time
from typing import Dict, Optional, Callable, Any
from dataclasses import dataclass
from collections import defaultdict, deque
import structlog

logger = structlog.get_logger(__name__)


@dataclass
class RateLimitConfig:
    """Rate limiting configuration."""
    requests_per_second: float = 10.0
    burst_size: int = 20
    window_size: float = 60.0  # seconds


class ConcurrencyLimiter:
    """Limits concurrent operations using semaphores."""
    
    def __init__(self, max_concurrent: int = 10):
        self.max_concurrent = max_concurrent
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self._active_count = 0
        self._total_requests = 0
        self._completed_requests = 0
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.semaphore.acquire()
        self._active_count += 1
        self._total_requests += 1
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        self._active_count -= 1
        self._completed_requests += 1
        self.semaphore.release()
    
    async def acquire(self):
        """Acquire the semaphore."""
        await self.semaphore.acquire()
        self._active_count += 1
        self._total_requests += 1
    
    def release(self):
        """Release the semaphore."""
        self._active_count -= 1
        self._completed_requests += 1
        self.semaphore.release()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get concurrency statistics."""
        return {
            "max_concurrent": self.max_concurrent,
            "active_count": self._active_count,
            "total_requests": self._total_requests,
            "completed_requests": self._completed_requests,
            "utilization": self._active_count / self.max_concurrent
        }
    
    def resize(self, new_limit: int):
        """Resize the concurrency limit."""
        if new_limit <= 0:
            raise ValueError("Concurrency limit must be positive")
        
        old_limit = self.max_concurrent
        self.max_concurrent = new_limit
        
        # Create new semaphore with updated limit
        current_available = self.semaphore._value
        new_available = current_available + (new_limit - old_limit)
        
        self.semaphore = asyncio.Semaphore(max(0, new_available))
        
        logger.info("Concurrency limit resized", 
                   old_limit=old_limit, 
                   new_limit=new_limit)


class TokenBucketRateLimiter:
    """Token bucket rate limiter implementation."""
    
    def __init__(self, config: RateLimitConfig):
        self.config = config
        self.tokens = float(config.burst_size)
        self.last_refill = time.time()
        self._lock = asyncio.Lock()
        self._requests_count = 0
        self._rejected_count = 0
    
    async def acquire(self, tokens: int = 1) -> bool:
        """Acquire tokens from the bucket."""
        async with self._lock:
            now = time.time()
            
            # Refill tokens based on time elapsed
            time_elapsed = now - self.last_refill
            tokens_to_add = time_elapsed * self.config.requests_per_second
            
            self.tokens = min(
                self.config.burst_size, 
                self.tokens + tokens_to_add
            )
            self.last_refill = now
            
            # Check if we have enough tokens
            if self.tokens >= tokens:
                self.tokens -= tokens
                self._requests_count += 1
                return True
            else:
                self._rejected_count += 1
                return False
    
    async def wait_for_tokens(self, tokens: int = 1, timeout: Optional[float] = None):
        """Wait until tokens are available."""
        start_time = time.time()
        
        while True:
            if await self.acquire(tokens):
                return
            
            if timeout and (time.time() - start_time) > timeout:
                raise asyncio.TimeoutError("Rate limit timeout")
            
            # Calculate wait time until next token is available
            async with self._lock:
                tokens_needed = tokens - self.tokens
                wait_time = tokens_needed / self.config.requests_per_second
                wait_time = min(wait_time, 1.0)  # Cap at 1 second
            
            await asyncio.sleep(wait_time)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get rate limiter statistics."""
        return {
            "requests_per_second": self.config.requests_per_second,
            "burst_size": self.config.burst_size,
            "current_tokens": self.tokens,
            "requests_count": self._requests_count,
            "rejected_count": self._rejected_count,
            "rejection_rate": (
                self._rejected_count / max(1, self._requests_count + self._rejected_count)
            )
        }


class SlidingWindowRateLimiter:
    """Sliding window rate limiter implementation."""
    
    def __init__(self, config: RateLimitConfig):
        self.config = config
        self.requests = deque()
        self._lock = asyncio.Lock()
        self._requests_count = 0
        self._rejected_count = 0
    
    async def acquire(self) -> bool:
        """Check if request is allowed under rate limit."""
        async with self._lock:
            now = time.time()
            window_start = now - self.config.window_size
            
            # Remove old requests outside the window
            while self.requests and self.requests[0] < window_start:
                self.requests.popleft()
            
            # Check if we're under the limit
            if len(self.requests) < self.config.requests_per_second * self.config.window_size:
                self.requests.append(now)
                self._requests_count += 1
                return True
            else:
                self._rejected_count += 1
                return False
    
    async def wait_for_slot(self, timeout: Optional[float] = None):
        """Wait until a slot is available."""
        start_time = time.time()
        
        while True:
            if await self.acquire():
                return
            
            if timeout and (time.time() - start_time) > timeout:
                raise asyncio.TimeoutError("Rate limit timeout")
            
            # Calculate wait time until oldest request expires
            async with self._lock:
                if self.requests:
                    oldest_request = self.requests[0]
                    wait_time = oldest_request + self.config.window_size - time.time()
                    wait_time = max(0.1, min(wait_time, 1.0))
                else:
                    wait_time = 0.1
            
            await asyncio.sleep(wait_time)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get rate limiter statistics."""
        return {
            "window_size": self.config.window_size,
            "requests_per_second": self.config.requests_per_second,
            "current_requests": len(self.requests),
            "requests_count": self._requests_count,
            "rejected_count": self._rejected_count,
            "rejection_rate": (
                self._rejected_count / max(1, self._requests_count + self._rejected_count)
            )
        }


class AdaptiveRateLimiter:
    """Adaptive rate limiter that adjusts based on system performance."""
    
    def __init__(self, initial_config: RateLimitConfig):
        self.config = initial_config
        self.base_limiter = TokenBucketRateLimiter(initial_config)
        self.response_times = deque(maxlen=100)
        self.error_count = 0
        self.success_count = 0
        self.last_adjustment = time.time()
        self.adjustment_interval = 30.0  # seconds
    
    async def acquire_with_feedback(
        self, 
        response_time: Optional[float] = None,
        success: bool = True
    ) -> bool:
        """Acquire with performance feedback."""
        # Record performance metrics
        if response_time is not None:
            self.response_times.append(response_time)
        
        if success:
            self.success_count += 1
        else:
            self.error_count += 1
        
        # Adjust rate limit if needed
        await self._maybe_adjust_rate_limit()
        
        return await self.base_limiter.acquire()
    
    async def _maybe_adjust_rate_limit(self):
        """Adjust rate limit based on performance metrics."""
        now = time.time()
        
        if now - self.last_adjustment < self.adjustment_interval:
            return
        
        self.last_adjustment = now
        
        # Calculate performance metrics
        avg_response_time = (
            sum(self.response_times) / len(self.response_times)
            if self.response_times else 0
        )
        
        total_requests = self.success_count + self.error_count
        error_rate = self.error_count / max(1, total_requests)
        
        # Adjust rate based on performance
        current_rate = self.config.requests_per_second
        new_rate = current_rate
        
        # Decrease rate if high error rate or slow responses
        if error_rate > 0.1 or avg_response_time > 2.0:
            new_rate = current_rate * 0.8
            logger.warning("Decreasing rate limit due to poor performance", 
                         error_rate=error_rate,
                         avg_response_time=avg_response_time,
                         new_rate=new_rate)
        
        # Increase rate if performance is good
        elif error_rate < 0.01 and avg_response_time < 0.5:
            new_rate = current_rate * 1.1
            logger.info("Increasing rate limit due to good performance", 
                       error_rate=error_rate,
                       avg_response_time=avg_response_time,
                       new_rate=new_rate)
        
        # Update configuration
        if new_rate != current_rate:
            self.config.requests_per_second = max(1.0, min(100.0, new_rate))
            self.base_limiter = TokenBucketRateLimiter(self.config)
        
        # Reset counters
        self.error_count = 0
        self.success_count = 0
    
    def get_stats(self) -> Dict[str, Any]:
        """Get adaptive rate limiter statistics."""
        base_stats = self.base_limiter.get_stats()
        
        avg_response_time = (
            sum(self.response_times) / len(self.response_times)
            if self.response_times else 0
        )
        
        base_stats.update({
            "adaptive": True,
            "avg_response_time": avg_response_time,
            "recent_response_times": len(self.response_times),
            "error_count": self.error_count,
            "success_count": self.success_count
        })
        
        return base_stats


class ResourceLimiter:
    """Limits resource usage across multiple dimensions."""
    
    def __init__(self):
        self.limiters: Dict[str, ConcurrencyLimiter] = {}
        self.rate_limiters: Dict[str, TokenBucketRateLimiter] = {}
    
    def add_concurrency_limit(self, name: str, max_concurrent: int):
        """Add a concurrency limiter."""
        self.limiters[name] = ConcurrencyLimiter(max_concurrent)
        logger.info("Concurrency limiter added", name=name, limit=max_concurrent)
    
    def add_rate_limit(self, name: str, config: RateLimitConfig):
        """Add a rate limiter."""
        self.rate_limiters[name] = TokenBucketRateLimiter(config)
        logger.info("Rate limiter added", name=name, rps=config.requests_per_second)
    
    async def acquire_all(self, *limiter_names) -> 'ResourceAcquisition':
        """Acquire multiple limiters atomically."""
        return ResourceAcquisition(self, limiter_names)
    
    def get_all_stats(self) -> Dict[str, Any]:
        """Get statistics for all limiters."""
        return {
            "concurrency_limiters": {
                name: limiter.get_stats()
                for name, limiter in self.limiters.items()
            },
            "rate_limiters": {
                name: limiter.get_stats()
                for name, limiter in self.rate_limiters.items()
            }
        }


class ResourceAcquisition:
    """Context manager for acquiring multiple resources."""
    
    def __init__(self, resource_limiter: ResourceLimiter, limiter_names: tuple):
        self.resource_limiter = resource_limiter
        self.limiter_names = limiter_names
        self.acquired_limiters = []
    
    async def __aenter__(self):
        """Acquire all specified limiters."""
        for name in self.limiter_names:
            if name in self.resource_limiter.limiters:
                await self.resource_limiter.limiters[name].acquire()
                self.acquired_limiters.append(('concurrency', name))
            
            if name in self.resource_limiter.rate_limiters:
                await self.resource_limiter.rate_limiters[name].wait_for_tokens()
                self.acquired_limiters.append(('rate', name))
        
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Release all acquired limiters."""
        for limiter_type, name in self.acquired_limiters:
            if limiter_type == 'concurrency':
                self.resource_limiter.limiters[name].release()
        
        self.acquired_limiters.clear()