import pytest
import asyncio
from src.nodes.cache_node import CacheNode, CacheLineState

@pytest.mark.asyncio
async def test_cache_operations():
    # Initialize cache node
    node = CacheNode("test_node", "localhost", 8000)
    
    # Test write operation
    result = await node.write("key1", "value1")
    assert result == True
    
    # Test read operation
    value = await node.read("key1")
    assert value == "value1"
    
    # Test cache line state
    cache_line = node.cache.get("key1")
    assert cache_line.state == CacheLineState.MODIFIED
    
    # Test LRU eviction
    # Fill cache to capacity
    node = CacheNode("test_node", "localhost", 8000, capacity=2)
    await node.write("key1", "value1")
    await node.write("key2", "value2")
    await node.write("key3", "value3")
    
    # key1 should be evicted
    value = await node.read("key1")
    assert value is None
    
    # key2 and key3 should still be there
    value = await node.read("key2")
    assert value == "value2"
    value = await node.read("key3")
    assert value == "value3"

@pytest.mark.asyncio
async def test_cache_coherence():
    # Create multiple cache nodes
    node1 = CacheNode("node1", "localhost", 8001)
    node2 = CacheNode("node2", "localhost", 8002)
    
    # Add them as peers
    node1.add_peer("node2", "localhost", 8002)
    node2.add_peer("node1", "localhost", 8001)
    
    # Write to node1
    await node1.write("key1", "value1")
    
    # Read from node2 should get the value
    value = await node2.read("key1")
    assert value == "value1"
    
    # Modify in node2
    await node2.write("key1", "value2")
    
    # Node1's copy should be invalidated
    cache_line = node1.cache.get("key1")
    assert cache_line.state == CacheLineState.INVALID
    
    # Read from node1 should get updated value
    value = await node1.read("key1")
    assert value == "value2"