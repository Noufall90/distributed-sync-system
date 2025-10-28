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
        self.consumer = None  # Track which consumer has the message

from fastapi import HTTPException
from pydantic import BaseModel

class QueueMessage:
    def __init__(self, message_id: str, content: str, producer: str):
        self.message_id = message_id
        self.content = content
        self.producer = producer
        self.timestamp = asyncio.get_event_loop().time()
        self.delivered = False
        self.delivery_attempts = 0
        self.consumer = None  # Track which consumer has the message

class EnqueueRequest(BaseModel):
    message: str
    producerId: str

class AckRequest(BaseModel):
    messageId: str
    consumerId: str

class MessageResponse(BaseModel):
    message_id: str
    message: str
    queue: str
    consumerId: str

class QueueNode(BaseNode):
    def __init__(self, node_id: str, host: str, port: int):
        super().__init__(node_id, host, port)
        self.queues: Dict[str, List[QueueMessage]] = {}
        self.hash_ring: Optional[ConsistentHashing] = None
        self.message_store: Dict[str, QueueMessage] = {}  # For persistence
        
    def setup_routes(self):
        super().setup_routes()
        
        @self.app.post("/queue/{queue_name}")
        async def enqueue_message(queue_name: str, body: EnqueueRequest):
            if not body.message or not body.producerId:
                raise HTTPException(status_code=422, detail="message and producerId are required")
            try:
                result = await self.enqueue(queue_name, body.message, body.producerId)
                if not result:
                    raise HTTPException(status_code=409, detail="Failed to enqueue message")
                return {
                    "success": True,
                    "queue": queue_name,
                    "message_id": f"{queue_name}:{body.producerId}:{asyncio.get_event_loop().time()}"
                }
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
            
        @self.app.get("/queue/{queue_name}")
        async def dequeue_message(queue_name: str, consumerId: str):
            if not consumerId:
                raise HTTPException(status_code=422, detail="consumerId is required")
            try:
                message = await self.dequeue(queue_name, consumerId)
                if not message:
                    if not self.is_leader():
                        raise HTTPException(status_code=307, 
                            detail=f"Not leader. Please redirect to node {self.raft.leader_id}")
                    raise HTTPException(status_code=404, detail="No messages available")
                return {
                    "message_id": message.message_id,
                    "message": message.content,
                    "queue": queue_name,
                    "consumerId": consumerId
                }
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
            
        @self.app.post("/queue/{queue_name}/ack")
        async def ack_message(queue_name: str, body: AckRequest):
            if not body.messageId or not body.consumerId:
                raise HTTPException(status_code=422, detail="messageId and consumerId are required")
            try:
                result = await self.ack_message(queue_name, body.messageId, body.consumerId)
                if not result:
                    raise HTTPException(status_code=404, detail="Message not found or consumer mismatch")
                return {"success": True, "queue": queue_name, "messageId": body.messageId}
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
            
        @self.app.get("/metrics/queue")
        async def get_metrics():
            try:
                queue_stats = {}
                for queue_name, messages in self.queues.items():
                    delivered = sum(1 for m in messages if m.delivered)
                    total = len(messages)
                    queue_stats[queue_name] = {
                        "total": total,
                        "delivered": delivered,
                        "pending": total - delivered
                    }
                
                return {
                    "queues": len(self.queues),
                    "queue_stats": queue_stats,
                    "total_messages": sum(len(q) for q in self.queues.values()),
                    "stored_messages": len(self.message_store)
                }
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
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
            
    async def dequeue(self, queue_name: str, consumer: str) -> Optional[QueueMessage]:
        """Get a message from a queue"""
        if not self.is_leader():
            return None
            
        if queue_name not in self.queues or not self.queues[queue_name]:
            return None
            
        # Get the oldest non-delivered message
        for message in self.queues[queue_name]:
            if not message.delivered:
                message.delivered = True
                message.delivery_attempts += 1
                message.consumer = consumer  # Track who received the message
                return message
                
        return None
        
    async def ack_message(self, queue_name: str, message_id: str, consumer: str) -> bool:
        """Acknowledge message processing"""
        if not self.is_leader():
            return False
            
        responsible_node = self.hash_ring.get_node(message_id)
        
        if responsible_node == self.node_id:
            if message_id in self.message_store:
                message = self.message_store[message_id]
                # Verify consumer matches
                if not hasattr(message, 'consumer') or message.consumer != consumer:
                    return False
                    
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
                "message_id": message_id,
                "consumer": consumer
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
            
    async def handle_message(self, message: dict) -> dict:
        """Handle incoming messages"""
        try:
            action = message.get("action")
            params = message.get("params", {})
            
            if action == "enqueue":
                result = await self.enqueue(
                    params["queue_name"],
                    params["message"],
                    params["producer"]
                )
                return {"success": result}
            elif action == "dequeue":
                result = await self.dequeue(
                    params["queue_name"],
                    params["consumer"]
                )
                return {"success": True, "message": result} if result else {"success": False}
            elif action == "ack":
                result = await self.ack_message(
                    params["queue_name"],
                    params["message_id"]
                )
                return {"success": result}
            else:
                return {"success": False, "error": "Unknown action"}
                
        except Exception as e:
            self.logger.error(f"Error handling message: {e}")
            return {"error": str(e), "success": False}
            
    def recover_messages(self):
        """Recover messages after node failure"""
        # Implement recovery from persistent storage
        pass