"""
URL Shortener (bit.ly-like)
===========================

Core Design: Service that shortens URLs and redirects.

Design Patterns & Strategies Used:
1. Factory Pattern - Generate short codes
2. Strategy Pattern - Different encoding strategies (Base62, Hash, Random)
3. Singleton Pattern - URL service instance
4. Cache Pattern - LRU cache for hot URLs
5. Observer Pattern - Analytics tracking

Strategies:
- Base62 encoding: Converts number to base-62 string
- Hash-based: MD5/SHA256 hash with collision handling
- Random: Random alphanumeric string
- Custom encoding: Sequential with custom alphabet

Scaling:
- Distributed ID generation (Snowflake, UUID)
- Database sharding by short code
- CDN for redirects
- Bloom filter for existence check
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict
import hashlib
import random
import string
from collections import OrderedDict


class EncodingStrategy(ABC):
    """Encoding strategy interface"""
    
    @abstractmethod
    def encode(self, url_id: int) -> str:
        """Encode URL ID to short code"""
        pass
    
    @abstractmethod
    def decode(self, short_code: str) -> Optional[int]:
        """Decode short code to URL ID"""
        pass


class Base62Strategy(EncodingStrategy):
    """Base62 encoding strategy"""
    
    ALPHABET = string.ascii_letters + string.digits  # 62 characters
    
    def encode(self, url_id: int) -> str:
        """Encode number to base-62"""
        if url_id == 0:
            return self.ALPHABET[0]
        
        result = []
        base = len(self.ALPHABET)
        
        while url_id > 0:
            result.append(self.ALPHABET[url_id % base])
            url_id //= base
        
        return ''.join(reversed(result))
    
    def decode(self, short_code: str) -> Optional[int]:
        """Decode base-62 to number"""
        base = len(self.ALPHABET)
        result = 0
        
        for char in short_code:
            if char not in self.ALPHABET:
                return None
            result = result * base + self.ALPHABET.index(char)
        
        return result


class HashStrategy(EncodingStrategy):
    """Hash-based encoding strategy"""
    
    def __init__(self, length: int = 6):
        self.length = length
    
    def encode(self, url_id: int) -> str:
        """Generate hash-based short code"""
        # Use URL ID as seed for hash
        hash_obj = hashlib.md5(str(url_id).encode())
        hash_hex = hash_obj.hexdigest()
        
        # Take first N characters
        return hash_hex[:self.length]
    
    def decode(self, short_code: str) -> Optional[int]:
        """Hash is one-way, cannot decode"""
        return None


class RandomStrategy(EncodingStrategy):
    """Random string strategy"""
    
    def __init__(self, length: int = 6):
        self.length = length
        self.characters = string.ascii_letters + string.digits
        self.generated: Dict[str, int] = {}
    
    def encode(self, url_id: int) -> str:
        """Generate random code"""
        while True:
            code = ''.join(random.choices(self.characters, k=self.length))
            if code not in self.generated:
                self.generated[code] = url_id
                return code
    
    def decode(self, short_code: str) -> Optional[int]:
        """Decode using lookup table"""
        return self.generated.get(short_code)


class URLShortener:
    """URL shortener service"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(URLShortener, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self.urls: Dict[str, str] = {}  # short_code -> long_url
        self.url_to_code: Dict[str, str] = {}  # long_url -> short_code
        self.url_ids: Dict[str, int] = {}  # short_code -> url_id
        self.next_id = 1
        self.encoding_strategy: EncodingStrategy = Base62Strategy()
        self.cache: OrderedDict = OrderedDict()  # LRU cache
        self.cache_size = 100
        self.analytics: Dict[str, int] = {}  # short_code -> hit count
        self._initialized = True
    
    def set_encoding_strategy(self, strategy: EncodingStrategy):
        """Set encoding strategy"""
        self.encoding_strategy = strategy
    
    def shorten(self, long_url: str) -> str:
        """Shorten URL"""
        # Check if already shortened
        if long_url in self.url_to_code:
            return self.url_to_code[long_url]
        
        # Generate short code
        url_id = self.next_id
        self.next_id += 1
        
        short_code = self.encoding_strategy.encode(url_id)
        
        # Store mappings
        self.urls[short_code] = long_url
        self.url_to_code[long_url] = short_code
        self.url_ids[short_code] = url_id
        self.analytics[short_code] = 0
        
        return short_code
    
    def expand(self, short_code: str) -> Optional[str]:
        """Expand short code to long URL"""
        # Check cache first
        if short_code in self.cache:
            self.cache.move_to_end(short_code)
            self.analytics[short_code] = self.analytics.get(short_code, 0) + 1
            return self.cache[short_code]
        
        # Check database
        if short_code in self.urls:
            long_url = self.urls[short_code]
            
            # Update cache
            if len(self.cache) >= self.cache_size:
                self.cache.popitem(last=False)
            self.cache[short_code] = long_url
            
            # Update analytics
            self.analytics[short_code] = self.analytics.get(short_code, 0) + 1
            
            return long_url
        
        return None
    
    def get_analytics(self, short_code: str) -> Optional[Dict]:
        """Get analytics for short code"""
        if short_code not in self.analytics:
            return None
        
        return {
            "short_code": short_code,
            "long_url": self.urls.get(short_code),
            "hit_count": self.analytics[short_code],
            "created_at": "timestamp"  # Would have actual timestamp
        }
    
    def delete_url(self, short_code: str) -> bool:
        """Delete shortened URL"""
        if short_code in self.urls:
            long_url = self.urls[short_code]
            del self.urls[short_code]
            if long_url in self.url_to_code:
                del self.url_to_code[long_url]
            if short_code in self.url_ids:
                del self.url_ids[short_code]
            if short_code in self.cache:
                del self.cache[short_code]
            if short_code in self.analytics:
                del self.analytics[short_code]
            return True
        return False


# ==================== DEMONSTRATION ====================

def main():
    print("=" * 60)
    print("URL SHORTENER DEMONSTRATION")
    print("=" * 60)
    print()
    
    shortener = URLShortener()
    
    print("1. Shortening URLs with Base62:")
    url1 = "https://www.example.com/very/long/url/path"
    url2 = "https://www.google.com/search?q=python"
    url3 = "https://github.com/user/repo"
    
    code1 = shortener.shorten(url1)
    code2 = shortener.shorten(url2)
    code3 = shortener.shorten(url3)
    
    print(f"URL1: {url1[:40]}... -> {code1}")
    print(f"URL2: {url2[:40]}... -> {code2}")
    print(f"URL3: {url3[:40]}... -> {code3}")
    print()
    
    print("2. Expanding short codes:")
    expanded1 = shortener.expand(code1)
    expanded2 = shortener.expand(code2)
    print(f"Code {code1} -> {expanded1}")
    print(f"Code {code2} -> {expanded2}")
    print()
    
    print("3. Analytics:")
    shortener.expand(code1)  # Another hit
    analytics = shortener.get_analytics(code1)
    print(f"Analytics for {code1}: {analytics}")
    print()
    
    print("4. Testing Hash strategy:")
    shortener.set_encoding_strategy(HashStrategy(length=8))
    code4 = shortener.shorten("https://test.com")
    print(f"Hash code: {code4}")
    print()
    
    print("=" * 60)
    print("DESIGN PATTERNS & STRATEGIES:")
    print("=" * 60)
    print("1. Strategy Pattern - Different encoding (Base62, Hash, Random)")
    print("2. Singleton Pattern - Single URL service instance")
    print("3. Factory Pattern - Generate short codes")
    print("4. Cache Pattern - LRU cache for hot URLs")
    print("5. Observer Pattern - Analytics tracking")
    print()
    print("SCALING STRATEGIES:")
    print("- Distributed ID generation (Snowflake)")
    print("- Database sharding")
    print("- CDN for redirects")
    print("- Bloom filter for existence")
    print("- Horizontal scaling")
    print("=" * 60)


if __name__ == "__main__":
    main()

