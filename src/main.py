import asyncio
import os
from typing import Dict, Type
from nodes.base_node import BaseNode
from nodes.lock_manager import LockManager
from nodes.queue_node import QueueNode
from nodes.cache_node import CacheNode

NODE_TYPES: Dict[str, Type[BaseNode]] = {
    "lock_manager": LockManager,
    "queue": QueueNode,
    "cache": CacheNode
}

async def main():
    # Get configuration from environment
    node_type = os.environ.get("NODE_TYPE", "base")
    node_id = os.environ.get("NODE_ID", "node1")
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "8000"))
    
    # Create node instance
    NodeClass = NODE_TYPES.get(node_type, BaseNode)
    node = NodeClass(node_id, host, port)
    
    # Start the node
    try:
        await node.start()
    except KeyboardInterrupt:
        print(f"Node {node_id} shutting down...")
    except Exception as e:
        print(f"Error in node {node_id}: {e}")

if __name__ == "__main__":
    asyncio.run(main())