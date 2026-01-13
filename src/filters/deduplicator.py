"""
Deduplicator - Prevents duplicate notifications using Redis or in-memory cache.
"""
import hashlib
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class Deduplicator:
    """Tracks seen items to prevent duplicate notifications."""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize deduplicator with configuration.
        
        Args:
            config: Deduplication settings (window_seconds, etc.)
        """
        self.window_seconds = config.get("window_seconds", 3600)
        self.similarity_threshold = config.get("similarity_threshold", 0.8)
        
        self._redis = None
        self._memory_cache: Dict[str, datetime] = {}
        
        # Try to connect to Redis
        self._init_redis()
    
    def _init_redis(self):
        """Initialize Redis connection if available."""
        redis_url = os.environ.get("REDIS_URL")
        if not redis_url:
            logger.info("No REDIS_URL configured, using in-memory cache")
            return
        
        try:
            import redis
            self._redis = redis.from_url(redis_url, decode_responses=True)
            self._redis.ping()
            logger.info("Connected to Redis for deduplication")
        except Exception as e:
            logger.warning(f"Failed to connect to Redis, using in-memory cache: {e}")
            self._redis = None
    
    def _generate_hash(self, item: Dict[str, Any]) -> str:
        """Generate a unique hash for an item."""
        # Use link as primary identifier, fallback to title + source
        link = item.get("link", "")
        if link:
            key = link
        else:
            key = f"{item.get('source', '')}:{item.get('title', '')}"
        
        return hashlib.sha256(key.encode()).hexdigest()[:16]
    
    async def is_duplicate(self, item: Dict[str, Any]) -> bool:
        """
        Check if an item has been seen before.
        
        Args:
            item: News item to check.
            
        Returns:
            True if item is a duplicate, False otherwise.
        """
        item_hash = self._generate_hash(item)
        
        if self._redis:
            return await self._check_redis(item_hash)
        else:
            return self._check_memory(item_hash)
    
    async def _check_redis(self, item_hash: str) -> bool:
        """Check Redis for duplicate."""
        try:
            key = f"crypto-alert:seen:{item_hash}"
            exists = self._redis.exists(key)
            return bool(exists)
        except Exception as e:
            logger.warning(f"Redis check failed: {e}")
            return self._check_memory(item_hash)
    
    def _check_memory(self, item_hash: str) -> bool:
        """Check in-memory cache for duplicate."""
        if item_hash not in self._memory_cache:
            return False
        
        # Check if within time window
        seen_time = self._memory_cache[item_hash]
        age = (datetime.now(timezone.utc) - seen_time).total_seconds()
        
        if age > self.window_seconds:
            # Expired, remove and allow
            del self._memory_cache[item_hash]
            return False
        
        return True
    
    async def mark_seen(self, item: Dict[str, Any]):
        """
        Mark an item as seen.
        
        Args:
            item: News item to mark as seen.
        """
        item_hash = self._generate_hash(item)
        
        if self._redis:
            await self._mark_redis(item_hash)
        else:
            self._mark_memory(item_hash)
    
    async def _mark_redis(self, item_hash: str):
        """Mark item as seen in Redis."""
        try:
            key = f"crypto-alert:seen:{item_hash}"
            self._redis.setex(key, self.window_seconds, "1")
        except Exception as e:
            logger.warning(f"Redis mark failed: {e}")
            self._mark_memory(item_hash)
    
    def _mark_memory(self, item_hash: str):
        """Mark item as seen in memory."""
        self._memory_cache[item_hash] = datetime.now(timezone.utc)
        
        # Cleanup old entries periodically
        self._cleanup_memory_cache()
    
    def _cleanup_memory_cache(self):
        """Remove expired entries from memory cache."""
        if len(self._memory_cache) < 100:
            return
        
        now = datetime.now(timezone.utc)
        expired = [
            k for k, v in self._memory_cache.items()
            if (now - v).total_seconds() > self.window_seconds
        ]
        
        for k in expired:
            del self._memory_cache[k]
        
        if expired:
            logger.debug(f"Cleaned up {len(expired)} expired cache entries")
    
    async def close(self):
        """Close Redis connection."""
        if self._redis:
            self._redis.close()
