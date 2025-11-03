"""
Cache System (LRU/LFU Cache)
=============================

Core Design: In-memory cache with get() and put() operations in O(1) time complexity.

Design Patterns & Strategies Used:
1. Strategy Pattern - For different eviction policies (LRU, LFU)
2. Template Method Pattern - For common cache operations
3. Decorator Pattern - For thread-safety wrapper
4. Factory Pattern - For creating different cache types

Data Structures:
- LRU: HashMap + Doubly Linked List (O(1) get/put)
- LFU: HashMap + MinHeap + Frequency HashMap (O(1) get, O(log n) put)

Why LinkedHashMap/Deque/OrderedDict?
- OrderedDict in Python maintains insertion order
- Doubly Linked List allows O(1) removal from middle
- Enables O(1) access and O(1) removal for LRU
"""

from abc import ABC, abstractmethod
from collections import OrderedDict
from typing import Optional, Any, Dict
from threading import Lock
import heapq
from datetime import datetime


# ==================== STRATEGY PATTERN ====================
# Different eviction policies (LRU, LFU)

class EvictionStrategy(ABC):
    """Strategy interface for eviction policies"""
    
    @abstractmethod
    def get(self, key: str) -> Optional[Any]:
        pass
    
    @abstractmethod
    def put(self, key: str, value: Any) -> Optional[str]:
        """Returns evicted key if capacity exceeded"""
        pass
    
    @abstractmethod
    def remove(self, key: str) -> bool:
        pass


class LRUStrategy(EvictionStrategy):
    """Least Recently Used eviction strategy"""
    
    def __init__(self, capacity: int):
        self.capacity = capacity
        # OrderedDict maintains insertion order, last item is most recently used
        self.cache: OrderedDict = OrderedDict()
    
    def get(self, key: str) -> Optional[Any]:
        if key not in self.cache:
            return None
        # Move to end (most recently used)
        self.cache.move_to_end(key)
        return self.cache[key]
    
    def put(self, key: str, value: Any) -> Optional[str]:
        evicted = None
        
        if key in self.cache:
            self.cache[key] = value
            self.cache.move_to_end(key)
        else:
            if len(self.cache) >= self.capacity:
                # Remove least recently used (first item)
                evicted = self.cache.popitem(last=False)[0]
            self.cache[key] = value
        
        return evicted
    
    def remove(self, key: str) -> bool:
        if key in self.cache:
            del self.cache[key]
            return True
        return False
    
    def size(self) -> int:
        return len(self.cache)


class LFUStrategy(EvictionStrategy):
    """Least Frequently Used eviction strategy"""
    
    def __init__(self, capacity: int):
        self.capacity = capacity
        self.cache: Dict[str, Any] = {}  # key -> value
        self.freq: Dict[str, int] = {}  # key -> frequency
        self.min_heap = []  # (frequency, timestamp, key) for tie-breaking
        self.access_time = {}  # key -> last access timestamp
    
    def get(self, key: str) -> Optional[Any]:
        if key not in self.cache:
            return None
        
        # Update frequency and access time
        self.freq[key] = self.freq.get(key, 0) + 1
        self.access_time[key] = datetime.now()
        
        # Rebuild heap
        self._rebuild_heap()
        
        return self.cache[key]
    
    def put(self, key: str, value: Any) -> Optional[str]:
        evicted = None
        
        if key in self.cache:
            self.cache[key] = value
            self.freq[key] = self.freq.get(key, 0) + 1
            self.access_time[key] = datetime.now()
        else:
            if len(self.cache) >= self.capacity:
                # Evict least frequently used
                if self.min_heap:
                    _, _, evicted = heapq.heappop(self.min_heap)
                    del self.cache[evicted]
                    del self.freq[evicted]
                    del self.access_time[evicted]
            
            self.cache[key] = value
            self.freq[key] = 1
            self.access_time[key] = datetime.now()
        
        self._rebuild_heap()
        return evicted
    
    def _rebuild_heap(self):
        """Rebuild min heap based on frequency and access time"""
        self.min_heap = []
        for key in self.cache:
            heapq.heappush(self.min_heap, 
                         (self.freq[key], self.access_time[key], key))
    
    def remove(self, key: str) -> bool:
        if key in self.cache:
            del self.cache[key]
            del self.freq[key]
            del self.access_time[key]
            self._rebuild_heap()
            return True
        return False
    
    def size(self) -> int:
        return len(self.cache)


# ==================== DECORATOR PATTERN ====================
# Thread-safe wrapper for cache

class ThreadSafeCache:
    """Decorator Pattern - Adds thread-safety to cache operations"""
    
    def __init__(self, cache: 'Cache'):
        self.cache = cache
        self.lock = Lock()
    
    def get(self, key: str) -> Optional[Any]:
        with self.lock:
            return self.cache.get(key)
    
    def put(self, key: str, value: Any) -> Optional[str]:
        with self.lock:
            return self.cache.put(key, value)
    
    def remove(self, key: str) -> bool:
        with self.lock:
            return self.cache.remove(key)
    
    def size(self) -> int:
        with self.lock:
            return self.cache.size()
    
    def clear(self):
        with self.lock:
            self.cache.clear()


# ==================== TEMPLATE METHOD PATTERN ====================
# Base cache class with template methods

class Cache:
    """Template Method Pattern - Base cache with common operations"""
    
    def __init__(self, capacity: int, strategy: EvictionStrategy):
        self.capacity = capacity
        self.strategy = strategy
        self.stats = {"hits": 0, "misses": 0}
    
    def get(self, key: str) -> Optional[Any]:
        """Template method for get operation"""
        value = self.strategy.get(key)
        if value is not None:
            self.stats["hits"] += 1
        else:
            self.stats["misses"] += 1
        return value
    
    def put(self, key: str, value: Any) -> Optional[str]:
        """Template method for put operation"""
        evicted = self.strategy.put(key, value)
        if evicted:
            # Can add hook for eviction notification
            pass
        return evicted
    
    def remove(self, key: str) -> bool:
        """Remove a key from cache"""
        return self.strategy.remove(key)
    
    def size(self) -> int:
        """Get current cache size"""
        return self.strategy.size()
    
    def clear(self):
        """Clear all cache entries"""
        while self.strategy.size() > 0:
            if hasattr(self.strategy, 'cache'):
                keys = list(self.strategy.cache.keys())
                for key in keys:
                    self.strategy.remove(key)
        self.stats = {"hits": 0, "misses": 0}
    
    def get_stats(self) -> Dict:
        """Get cache statistics"""
        total = self.stats["hits"] + self.stats["misses"]
        hit_rate = self.stats["hits"] / total if total > 0 else 0
        return {
            **self.stats,
            "hit_rate": hit_rate,
            "size": self.size(),
            "capacity": self.capacity
        }


# ==================== FACTORY PATTERN ====================
# Create different cache types

class CacheFactory:
    """Factory Pattern - Creates different cache implementations"""
    
    @staticmethod
    def create_lru_cache(capacity: int, thread_safe: bool = False) -> Cache:
        """Create LRU cache"""
        strategy = LRUStrategy(capacity)
        cache = Cache(capacity, strategy)
        return ThreadSafeCache(cache) if thread_safe else cache
    
    @staticmethod
    def create_lfu_cache(capacity: int, thread_safe: bool = False) -> Cache:
        """Create LFU cache"""
        strategy = LFUStrategy(capacity)
        cache = Cache(capacity, strategy)
        return ThreadSafeCache(cache) if thread_safe else cache


# ==================== CACHE STAMPEDE PREVENTION ====================
# Using lock per key to prevent thundering herd

class CacheStampedePrevention:
    """Prevents cache stampede using per-key locks"""
    
    def __init__(self, cache: Cache):
        self.cache = cache
        self.key_locks: Dict[str, Lock] = {}
        self.global_lock = Lock()
    
    def get_or_compute(self, key: str, compute_func):
        """Get from cache or compute if missing, preventing stampede"""
        # Try cache first
        value = self.cache.get(key)
        if value is not None:
            return value
        
        # Get or create lock for this key
        with self.global_lock:
            if key not in self.key_locks:
                self.key_locks[key] = Lock()
            lock = self.key_locks[key]
        
        # Only one thread computes for this key
        with lock:
            # Double-check after acquiring lock
            value = self.cache.get(key)
            if value is not None:
                return value
            
            # Compute value
            value = compute_func(key)
            self.cache.put(key, value)
            
            # Clean up lock if no longer needed
            with self.global_lock:
                if key in self.key_locks:
                    del self.key_locks[key]
            
            return value


# ==================== DEMONSTRATION ====================

def main():
    print("=" * 60)
    print("CACHE SYSTEM DEMONSTRATION")
    print("=" * 60)
    print()
    
    # LRU Cache
    print("1. LRU Cache:")
    lru_cache = CacheFactory.create_lru_cache(capacity=3)
    lru_cache.put("a", 1)
    lru_cache.put("b", 2)
    lru_cache.put("c", 3)
    print(f"After adding a, b, c: {lru_cache.size()} items")
    
    lru_cache.get("a")  # Access 'a' to make it recently used
    lru_cache.put("d", 4)  # Should evict 'b' (least recently used)
    print(f"After adding 'd', 'b' should be evicted")
    print(f"Get 'b': {lru_cache.get('b')} (should be None)")
    print(f"Get 'a': {lru_cache.get('a')} (should be 1)")
    print()
    
    # LFU Cache
    print("2. LFU Cache:")
    lfu_cache = CacheFactory.create_lfu_cache(capacity=3)
    lfu_cache.put("x", 10)
    lfu_cache.put("y", 20)
    lfu_cache.put("z", 30)
    
    lfu_cache.get("x")
    lfu_cache.get("x")  # x accessed twice
    lfu_cache.get("y")  # y accessed once
    lfu_cache.get("z")  # z accessed once
    
    lfu_cache.put("w", 40)  # Should evict y or z (least frequently used)
    print(f"After adding 'w', least frequent item evicted")
    print(f"Get 'x': {lfu_cache.get('x')} (should be 10)")
    print()
    
    # Thread-Safe Cache
    print("3. Thread-Safe Cache:")
    thread_safe = CacheFactory.create_lru_cache(capacity=5, thread_safe=True)
    thread_safe.put("thread1", "value1")
    thread_safe.put("thread2", "value2")
    print(f"Thread-safe cache size: {thread_safe.size()}")
    print()
    
    # Cache Statistics
    print("4. Cache Statistics:")
    stats = lru_cache.get_stats()
    print(f"Cache Stats: {stats}")
    print()
    
    print("=" * 60)
    print("DESIGN PATTERNS & STRATEGIES:")
    print("=" * 60)
    print("1. Strategy Pattern - LRU/LFU eviction strategies")
    print("2. Template Method - Common cache operations")
    print("3. Decorator Pattern - Thread-safety wrapper")
    print("4. Factory Pattern - Cache creation")
    print()
    print("TIME COMPLEXITY:")
    print("- LRU: O(1) for get() and put()")
    print("- LFU: O(1) for get(), O(log n) for put()")
    print()
    print("THREAD SAFETY:")
    print("- Uses Lock per operation")
    print("- Cache stampede prevention with per-key locks")
    print("=" * 60)


if __name__ == "__main__":
    main()

