import asyncio
from typing import Dict, Optional, List
from collections import OrderedDict
from enum import Enum
from nodes.base_node import BaseNode

class CacheLineState(Enum):
    MODIFIED = "M"
    EXCLUSIVE = "E"
    SHARED = "S"
    INVALID = "I"

class CacheLine:
    def __init__(self, key: str, value: str):
        self.key = key
        self.value = value
        self.state = CacheLineState.EXCLUSIVE
        self.timestamp = asyncio.get_event_loop().time()

class LRUCache:
    def __init__(self, capacity: int):
        self.capacity = capacity
        self.cache: OrderedDict[str, CacheLine] = OrderedDict()
        
    def get(self, key: str) -> Optional[CacheLine]:
        """Get an item from cache"""
        if key not in self.cache:
            return None
            
        # Move to end (most recently used)
        self.cache.move_to_end(key)
        return self.cache[key]
        
    def put(self, key: str, value: str) -> None:
        """Put an item in cache"""
        if key in self.cache:
            self.cache.move_to_end(key)
            self.cache[key].value = value
            return
            
        if len(self.cache) >= self.capacity:
            # Remove least recently used item
            self.cache.popitem(last=False)
            
        self.cache[key] = CacheLine(key, value)
        
    def invalidate(self, key: str) -> None:
        """Invalidate a cache entry"""
        if key in self.cache:
            self.cache[key].state = CacheLineState.INVALID

class CacheNode(BaseNode):
    def __init__(self, node_id: str, host: str, port: int, capacity: int = 1000):
        super().__init__(node_id, host, port)
        self.cache = LRUCache(capacity)
        self.metrics: Dict[str, int] = {
            "hits": 0,
            "misses": 0,
            "invalidations": 0
        }
        
    async def read(self, key: str) -> Optional[str]:
        """Read a value from cache"""
        cache_line = self.cache.get(key)
        
        if not cache_line or cache_line.state == CacheLineState.INVALID:
            self.metrics["misses"] += 1
            # Need to fetch from other nodes
            value = await self.fetch_from_peers(key)
            if value:
                self.cache.put(key, value)
                cache_line = self.cache.get(key)
                cache_line.state = CacheLineState.SHARED
            return value
            
        self.metrics["hits"] += 1
        return cache_line.value
        
    async def write(self, key: str, value: str) -> bool:
        """Write a value to cache"""
        cache_line = self.cache.get(key)
        
        if cache_line:
            if cache_line.state == CacheLineState.MODIFIED:
                # Already have exclusive access
                cache_line.value = value
                return True
            elif cache_line.state in [CacheLineState.EXCLUSIVE, CacheLineState.SHARED]:
                # Need to invalidate other copies
                await self.invalidate_peers(key)
                
        # Get exclusive access
        if await self.get_exclusive_access(key):
            self.cache.put(key, value)
            cache_line = self.cache.get(key)
            cache_line.state = CacheLineState.MODIFIED
            return True
            
        return False
        
    async def invalidate_peers(self, key: str) -> None:
        """Invalidate key in peer caches"""
        message = {
            "action": "invalidate",
            "params": {"key": key}
        }
        
        for peer_id in self.peers:
            try:
                await self.send_message(peer_id, str(message))
            except Exception:
                continue
                
    async def fetch_from_peers(self, key: str) -> Optional[str]:
        """Fetch value from peer nodes"""
        message = {
            "action": "fetch",
            "params": {"key": key}
        }
        
        for peer_id in self.peers:
            try:
                response = await self.send_message(peer_id, str(message))
                if response != "None":
                    return response
            except Exception:
                continue
                
        return None
        
    async def get_exclusive_access(self, key: str) -> bool:
        """Get exclusive access to a key"""
        message = {
            "action": "request_exclusive",
            "params": {"key": key}
        }
        
        success = True
        for peer_id in self.peers:
            try:
                response = await self.send_message(peer_id, str(message))
                if response != "True":
                    success = False
                    break
            except Exception:
                success = False
                break
                
        return success
        
    async def handle_message(self, message: str) -> str:
        """Handle incoming messages"""
        try:
            msg = eval(message)  # In production, use proper serialization
            action = msg["action"]
            params = msg["params"]
            
            if action == "invalidate":
                self.cache.invalidate(params["key"])
                self.metrics["invalidations"] += 1
                return "True"
            elif action == "fetch":
                cache_line = self.cache.get(params["key"])
                if cache_line and cache_line.state != CacheLineState.INVALID:
                    cache_line.state = CacheLineState.SHARED
                    return cache_line.value
            elif action == "request_exclusive":
                key = params["key"]
                cache_line = self.cache.get(key)
                if cache_line:
                    cache_line.state = CacheLineState.INVALID
                return "True"
                
            return "None"
        except Exception as e:
            self.logger.error(f"Error handling message: {e}")
            return "None"
            
    def get_metrics(self) -> Dict[str, int]:
        """Get cache performance metrics"""
        return self.metrics.copy()