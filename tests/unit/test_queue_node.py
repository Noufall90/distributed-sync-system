import pytest
import asyncio
from src.nodes.queue_node import QueueNode

@pytest.mark.asyncio
async def test_queue_operations():
    # Initialize queue node
    node = QueueNode("test_node", "localhost", 8000)
    
    # Test message enqueue
    result = await node.enqueue("test_queue", "test_message", "producer1")
    assert result == True
    
    # Test message dequeue
    message = await node.dequeue("test_queue", "consumer1")
    assert message == "test_message"
    
    # Test at-least-once delivery
    # Message should still be available until acknowledged
    message = await node.dequeue("test_queue", "consumer1")
    assert message == "test_message"
    
    # Test message acknowledgment
    result = await node.ack_message("test_queue", "test_queue:producer1:0")
    assert result == True
    
    # Message should now be gone
    message = await node.dequeue("test_queue", "consumer1")
    assert message is None

@pytest.mark.asyncio
async def test_consistent_hashing():
    nodes = [
        QueueNode("node1", "localhost", 8001),
        QueueNode("node2", "localhost", 8002),
        QueueNode("node3", "localhost", 8003)
    ]
    
    # Initialize consistent hashing ring
    for node in nodes:
        node.start()
        
    # Test message distribution
    messages = [f"message{i}" for i in range(100)]
    message_distribution = {}
    
    for message in messages:
        for node in nodes:
            if await node.enqueue("test_queue", message, "producer1"):
                node_id = node.node_id
                message_distribution[node_id] = message_distribution.get(node_id, 0) + 1
                break
    
    # Check if messages are relatively evenly distributed
    distribution_values = list(message_distribution.values())
    max_diff = max(distribution_values) - min(distribution_values)
    assert max_diff < len(messages) * 0.4  # Allow up to 40% variance