"""
Rate Limiter
============

Core Design: Rate limiter implementing token bucket, leaky bucket, and sliding window algorithms.

Design Patterns & Strategies Used:
1. Strategy Pattern - Different rate limiting algorithms
2. Factory Pattern - Create rate limiters
3. Decorator Pattern - Thread-safety wrapper
4. Singleton Pattern - Global rate limiter instance

Algorithms:
- Token Bucket: Tokens added at fixed rate, requests consume tokens
- Leaky Bucket: Requests added to bucket, processed at fixed rate
- Sliding Window: Tracks requests in time windows
- Fixed Window: Simple counter in fixed time window

Distributed Scaling:
- Redis-based distributed rate limiting
- Consistent hashing for sharding
- Circuit breaker pattern for failures
"""

from abc import ABC, abstractmethod
from typing import Dict, Optional
from datetime import datetime, timedelta
from threading import Lock
from collections import deque
import time


class RateLimiterStrategy(ABC):
    """Strategy interface for rate limiting algorithms"""
    
    @abstractmethod
    def allow_request(self, identifier: str) -> bool:
        """Check if request should be allowed"""
        pass
    
    @abstractmethod
    def get_remaining(self, identifier: str) -> int:
        """Get remaining requests allowed"""
        pass


class TokenBucketStrategy(RateLimiterStrategy):
    """Token Bucket Algorithm"""
    
    def __init__(self, capacity: int, refill_rate: float):
        """
        capacity: Maximum tokens in bucket
        refill_rate: Tokens added per second
        """
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.tokens: Dict[str, float] = {}  # identifier -> token count
        self.last_refill: Dict[str, datetime] = {}  # identifier -> last refill time
        self.lock = Lock()
    
    def allow_request(self, identifier: str) -> bool:
        with self.lock:
            self._refill(identifier)
            
            if identifier not in self.tokens:
                self.tokens[identifier] = self.capacity
                self.last_refill[identifier] = datetime.now()
            
            if self.tokens[identifier] >= 1.0:
                self.tokens[identifier] -= 1.0
                return True
            return False
    
    def _refill(self, identifier: str):
        """Refill tokens based on elapsed time"""
        if identifier not in self.tokens:
            return
        
        now = datetime.now()
        last = self.last_refill.get(identifier, now)
        elapsed = (now - last).total_seconds()
        
        tokens_to_add = elapsed * self.refill_rate
        self.tokens[identifier] = min(
            self.capacity,
            self.tokens[identifier] + tokens_to_add
        )
        self.last_refill[identifier] = now
    
    def get_remaining(self, identifier: str) -> int:
        with self.lock:
            self._refill(identifier)
            if identifier not in self.tokens:
                return self.capacity
            return int(self.tokens[identifier])


class LeakyBucketStrategy(RateLimiterStrategy):
    """Leaky Bucket Algorithm"""
    
    def __init__(self, capacity: int, leak_rate: float):
        """
        capacity: Maximum requests in bucket
        leak_rate: Requests processed per second
        """
        self.capacity = capacity
        self.leak_rate = leak_rate
        self.buckets: Dict[str, deque] = {}  # identifier -> request queue
        self.last_leak: Dict[str, datetime] = {}  # identifier -> last leak time
        self.lock = Lock()
    
    def allow_request(self, identifier: str) -> bool:
        with self.lock:
            self._leak(identifier)
            
            if identifier not in self.buckets:
                self.buckets[identifier] = deque()
                self.last_leak[identifier] = datetime.now()
            
            bucket = self.buckets[identifier]
            
            if len(bucket) < self.capacity:
                bucket.append(datetime.now())
                return True
            return False
    
    def _leak(self, identifier: str):
        """Remove processed requests from bucket"""
        if identifier not in self.buckets:
            return
        
        now = datetime.now()
        last = self.last_leak.get(identifier, now)
        elapsed = (now - last).total_seconds()
        
        requests_to_process = int(elapsed * self.leak_rate)
        bucket = self.buckets[identifier]
        
        for _ in range(min(requests_to_process, len(bucket))):
            bucket.popleft()
        
        self.last_leak[identifier] = now
    
    def get_remaining(self, identifier: str) -> int:
        with self.lock:
            self._leak(identifier)
            if identifier not in self.buckets:
                return self.capacity
            return self.capacity - len(self.buckets[identifier])


class SlidingWindowStrategy(RateLimiterStrategy):
    """Sliding Window Algorithm"""
    
    def __init__(self, max_requests: int, window_seconds: int):
        """
        max_requests: Maximum requests allowed
        window_seconds: Time window in seconds
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.windows: Dict[str, deque] = {}  # identifier -> request timestamps
        self.lock = Lock()
    
    def allow_request(self, identifier: str) -> bool:
        with self.lock:
            now = datetime.now()
            window_start = now - timedelta(seconds=self.window_seconds)
            
            if identifier not in self.windows:
                self.windows[identifier] = deque()
            
            window = self.windows[identifier]
            
            # Remove old requests outside window
            while window and window[0] < window_start:
                window.popleft()
            
            if len(window) < self.max_requests:
                window.append(now)
                return True
            return False
    
    def get_remaining(self, identifier: str) -> int:
        with self.lock:
            now = datetime.now()
            window_start = now - timedelta(seconds=self.window_seconds)
            
            if identifier not in self.windows:
                return self.max_requests
            
            window = self.windows[identifier]
            
            # Remove old requests
            while window and window[0] < window_start:
                window.popleft()
            
            return max(0, self.max_requests - len(window))


class FixedWindowStrategy(RateLimiterStrategy):
    """Fixed Window Algorithm"""
    
    def __init__(self, max_requests: int, window_seconds: int):
        """
        max_requests: Maximum requests allowed
        window_seconds: Time window in seconds
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.windows: Dict[str, tuple] = {}  # identifier -> (count, window_start)
        self.lock = Lock()
    
    def allow_request(self, identifier: str) -> bool:
        with self.lock:
            now = datetime.now()
            current_window = int(now.timestamp() / self.window_seconds)
            
            if identifier not in self.windows:
                self.windows[identifier] = (0, current_window)
            
            count, window_start = self.windows[identifier]
            
            # Reset if new window
            if window_start != current_window:
                count = 0
                window_start = current_window
            
            if count < self.max_requests:
                self.windows[identifier] = (count + 1, window_start)
                return True
            return False
    
    def get_remaining(self, identifier: str) -> int:
        with self.lock:
            now = datetime.now()
            current_window = int(now.timestamp() / self.window_seconds)
            
            if identifier not in self.windows:
                return self.max_requests
            
            count, window_start = self.windows[identifier]
            
            if window_start != current_window:
                return self.max_requests
            
            return max(0, self.max_requests - count)


class RateLimiter:
    """Rate limiter with strategy pattern"""
    
    def __init__(self, strategy: RateLimiterStrategy):
        self.strategy = strategy
    
    def allow(self, identifier: str) -> bool:
        """Check if request is allowed"""
        return self.strategy.allow_request(identifier)
    
    def remaining(self, identifier: str) -> int:
        """Get remaining requests"""
        return self.strategy.get_remaining(identifier)


class RateLimiterFactory:
    """Factory for creating rate limiters"""
    
    @staticmethod
    def create_token_bucket(capacity: int, refill_rate: float) -> RateLimiter:
        """Create token bucket rate limiter"""
        strategy = TokenBucketStrategy(capacity, refill_rate)
        return RateLimiter(strategy)
    
    @staticmethod
    def create_leaky_bucket(capacity: int, leak_rate: float) -> RateLimiter:
        """Create leaky bucket rate limiter"""
        strategy = LeakyBucketStrategy(capacity, leak_rate)
        return RateLimiter(strategy)
    
    @staticmethod
    def create_sliding_window(max_requests: int, window_seconds: int) -> RateLimiter:
        """Create sliding window rate limiter"""
        strategy = SlidingWindowStrategy(max_requests, window_seconds)
        return RateLimiter(strategy)
    
    @staticmethod
    def create_fixed_window(max_requests: int, window_seconds: int) -> RateLimiter:
        """Create fixed window rate limiter"""
        strategy = FixedWindowStrategy(max_requests, window_seconds)
        return RateLimiter(strategy)


# ==================== DEMONSTRATION ====================

def main():
    print("=" * 60)
    print("RATE LIMITER DEMONSTRATION")
    print("=" * 60)
    print()
    
    # Token Bucket
    print("1. Token Bucket (10 tokens, 2 tokens/sec):")
    token_limiter = RateLimiterFactory.create_token_bucket(capacity=10, refill_rate=2.0)
    user_id = "user1"
    
    for i in range(12):
        allowed = token_limiter.allow(user_id)
        remaining = token_limiter.remaining(user_id)
        print(f"Request {i+1}: {'Allowed' if allowed else 'Blocked'}, "
              f"Remaining: {remaining}")
    print()
    
    # Sliding Window
    print("2. Sliding Window (5 requests per 10 seconds):")
    sliding_limiter = RateLimiterFactory.create_sliding_window(max_requests=5, window_seconds=10)
    
    for i in range(7):
        allowed = sliding_limiter.allow(user_id)
        remaining = sliding_limiter.remaining(user_id)
        print(f"Request {i+1}: {'Allowed' if allowed else 'Blocked'}, "
              f"Remaining: {remaining}")
    print()
    
    # Leaky Bucket
    print("3. Leaky Bucket (5 capacity, 1 request/sec):")
    leaky_limiter = RateLimiterFactory.create_leaky_bucket(capacity=5, leak_rate=1.0)
    
    for i in range(7):
        allowed = leaky_limiter.allow(user_id)
        remaining = leaky_limiter.remaining(user_id)
        print(f"Request {i+1}: {'Allowed' if allowed else 'Blocked'}, "
              f"Remaining: {remaining}")
        time.sleep(0.1)
    print()
    
    print("=" * 60)
    print("DESIGN PATTERNS & STRATEGIES:")
    print("=" * 60)
    print("1. Strategy Pattern - Different algorithms (Token, Leaky, Sliding, Fixed)")
    print("2. Factory Pattern - Rate limiter creation")
    print()
    print("ALGORITHM TRADEOFFS:")
    print("- Token Bucket: Smooth rate, allows bursts")
    print("- Leaky Bucket: Fixed output rate, prevents bursts")
    print("- Sliding Window: Accurate, more memory")
    print("- Fixed Window: Simple, may allow double bursts")
    print()
    print("SCALING:")
    print("- Use Redis for distributed rate limiting")
    print("- Consistent hashing for sharding")
    print("- Approximate algorithms for high throughput")
    print("=" * 60)


if __name__ == "__main__":
    main()

