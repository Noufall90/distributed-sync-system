import asyncio
import os
import logging
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
    logger = None
    try:
        # Configure logging first
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        logger = logging.getLogger('distributed-sync')
        
        # Get configuration from environment
        node_type = os.environ.get("NODE_TYPE")
        if not node_type:
            raise ValueError("NODE_TYPE environment variable is required")
            
        node_id = os.environ.get("NODE_ID")
        if not node_id:
            raise ValueError("NODE_ID environment variable is required")
            
        host = os.environ.get("HOST", "0.0.0.0")
        
        try:
            port = int(os.environ.get("PORT", "8000"))
        except ValueError as e:
            raise ValueError(f"Invalid PORT value: {e}")
        
        # Create node instance
        NodeClass = NODE_TYPES.get(node_type)
        if NodeClass is None:
            raise ValueError(f"Invalid node type: {node_type}. Valid types are: {list(NODE_TYPES.keys())}")
            
        logger.info(f"Starting {node_type} node with ID {node_id} on {host}:{port}")
        node = NodeClass(node_id, host, port)
        
        # Start the node
        await node.start()
        
    except KeyboardInterrupt:
        if logger:
            logger.info("Received shutdown signal, cleaning up...")
        # Add cleanup logic here if needed
        
    except ValueError as e:
        if logger:
            logger.error(f"Configuration error: {e}")
        raise SystemExit(1)
        
    except Exception as e:
        if logger:
            logger.error(f"Unexpected error: {e}", exc_info=True)
        raise
        
    finally:
        if logger:
            logger.info("Node shutdown complete")

if __name__ == "__main__":
    asyncio.run(main())