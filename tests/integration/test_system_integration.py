import pytest
import asyncio
from src.nodes.lock_manager import LockManager
from src.nodes.queue_node import QueueNode
from src.nodes.cache_node import CacheNode

@pytest.mark.asyncio
async def test_full_system_integration():
    # Initialize components
    lock_managers = [
        LockManager(f"lock{i}", "localhost", 8001 + i) for i in range(3)
    ]
    queue_nodes = [
        QueueNode(f"queue{i}", "localhost", 8011 + i) for i in range(3)
    ]
    cache_nodes = [
        CacheNode(f"cache{i}", "localhost", 8021 + i) for i in range(3)
    ]
    
    # Set up peer relationships
    for i, manager in enumerate(lock_managers):
        for j, other in enumerate(lock_managers):
            if i != j:
                manager.add_peer(other.node_id, other.host, other.port)
                
    for i, node in enumerate(queue_nodes):
        for j, other in enumerate(queue_nodes):
            if i != j:
                node.add_peer(other.node_id, other.host, other.port)
                
    for i, node in enumerate(cache_nodes):
        for j, other in enumerate(cache_nodes):
            if i != j:
                node.add_peer(other.node_id, other.host, other.port)
    
    # Test distributed locking with queue operations
    # 1. Acquire lock
    lock_result = await lock_managers[0].acquire_lock("queue1", "exclusive", "producer1")
    assert lock_result == True
    
    # 2. Enqueue messages
    queue_result = await queue_nodes[0].enqueue("queue1", "test_message", "producer1")
    assert queue_result == True
    
    # 3. Release lock
    release_result = await lock_managers[0].release_lock("queue1", "producer1")
    assert release_result == True
    
    # 4. Cache the message
    cache_result = await cache_nodes[0].write("queue1_latest", "test_message")
    assert cache_result == True
    
    # 5. Read cached message from different node
    cached_value = await cache_nodes[1].read("queue1_latest")
    assert cached_value == "test_message"
    
    # 6. Verify queue message
    message = await queue_nodes[1].dequeue("queue1", "consumer1")
    assert message == "test_message"