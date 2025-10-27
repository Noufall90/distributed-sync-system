import asyncio
import hashlib
from typing import Dict, List, Optional
from nodes.base_node import BaseNode
from consensus.raft import RaftConsensus

class ConsistentHashing:
    def __init__(self, nodes: List[str], replicas: int = 3):
        self.replicas = replicas
        self.ring: Dict[int, str] = {}
        self.sorted_keys: List[int] = []
        
        for node in nodes:
            self.add_node(node)
            
    def add_node(self, node: str):
        """Add a node to the hash ring"""
        for i in range(self.replicas):
            key = self._hash(f"{node}:{i}")
            self.ring[key] = node
        self.sorted_keys = sorted(self.ring.keys())
        
    def remove_node(self, node: str):
        """Remove a node from the hash ring"""
        for i in range(self.replicas):
            key = self._hash(f"{node}:{i}")
            if key in self.ring:
                del self.ring[key]
        self.sorted_keys = sorted(self.ring.keys())
        
    def get_node(self, key: str) -> str:
        """Get the node responsible for a key"""
        if not self.ring:
            raise Exception("Hash ring is empty")
            
        hash_key = self._hash(key)
        
        for ring_key in self.sorted_keys:
            if hash_key <= ring_key:
                return self.ring[ring_key]
        return self.ring[self.sorted_keys[0]]
        
    def _hash(self, key: str) -> int:
        """Generate a hash for a key"""
        return int(hashlib.md5(key.encode()).hexdigest(), 16)

class QueueMessage:
    def __init__(self, message_id: str, content: str, producer: str):
        self.message_id = message_id
        self.content = content
        self.producer = producer
        self.timestamp = asyncio.get_event_loop().time()
        self.delivered = False
        self.delivery_attempts = 0

class QueueNode(BaseNode):
    def __init__(self, node_id: str, host: str, port: int):
        super().__init__(node_id, host, port)
        self.queues: Dict[str, List[QueueMessage]] = {}
        self.hash_ring: Optional[ConsistentHashing] = None
        self.message_store: Dict[str, QueueMessage] = {}  # For persistence
        
    async def start(self):
        """Start the queue node"""
        # Initialize consistent hashing with all peers
        self.hash_ring = ConsistentHashing([self.node_id] + list(self.peers.keys()))
        await super().start()
        
    async def enqueue(self, queue_name: str, message: str, producer: str) -> bool:
        """Add a message to a queue"""
        message_id = f"{queue_name}:{producer}:{asyncio.get_event_loop().time()}"
        
        # Determine which node should handle this message
        responsible_node = self.hash_ring.get_node(message_id)
        
        if responsible_node == self.node_id:
            # This node is responsible for the message
            if queue_name not in self.queues:
                self.queues[queue_name] = []
                
            queue_message = QueueMessage(message_id, message, producer)
            self.queues[queue_name].append(queue_message)
            self.message_store[message_id] = queue_message  # Persist message
            
            return True
        else:
            # Forward to responsible node
            return await self.forward_message("enqueue", {
                "queue_name": queue_name,
                "message": message,
                "producer": producer
            }, responsible_node)
            
    async def dequeue(self, queue_name: str, consumer: str) -> Optional[str]:
        """Get a message from a queue"""
        if queue_name not in self.queues or not self.queues[queue_name]:
            return None
            
        # Get the oldest non-delivered message
        for message in self.queues[queue_name]:
            if not message.delivered:
                message.delivered = True
                message.delivery_attempts += 1
                return message.content
                
        return None
        
    async def ack_message(self, queue_name: str, message_id: str) -> bool:
        """Acknowledge message processing"""
        responsible_node = self.hash_ring.get_node(message_id)
        
        if responsible_node == self.node_id:
            if message_id in self.message_store:
                del self.message_store[message_id]
                # Remove from queue
                self.queues[queue_name] = [
                    m for m in self.queues[queue_name]
                    if m.message_id != message_id
                ]
                return True
        else:
            return await self.forward_message("ack", {
                "queue_name": queue_name,
                "message_id": message_id
            }, responsible_node)
            
        return False
        
    async def forward_message(self, action: str, params: Dict, target_node: str) -> bool:
        """Forward a message to another node"""
        try:
            message = {
                "action": action,
                "params": params
            }
            response = await self.send_message(target_node, str(message))
            return response == "True"
        except Exception:
            return False
            
    async def handle_message(self, message: str) -> str:
        """Handle incoming messages"""
        try:
            msg = eval(message)  # In production, use proper serialization
            action = msg["action"]
            params = msg["params"]
            
            if action == "enqueue":
                result = await self.enqueue(
                    params["queue_name"],
                    params["message"],
                    params["producer"]
                )
            elif action == "dequeue":
                result = await self.dequeue(
                    params["queue_name"],
                    params["consumer"]
                )
            elif action == "ack":
                result = await self.ack_message(
                    params["queue_name"],
                    params["message_id"]
                )
            else:
                result = False
                
            return str(result)
        except Exception as e:
            self.logger.error(f"Error handling message: {e}")
            return str(False)
            
    def recover_messages(self):
        """Recover messages after node failure"""
        # Implement recovery from persistent storage
        pass