import asyncio
from typing import Dict, Set
from consensus.raft import RaftConsensus
from nodes.base_node import BaseNode

class LockType:
    SHARED = "shared"
    EXCLUSIVE = "exclusive"

class Lock:
    def __init__(self, resource_id: str, lock_type: str, owner: str):
        self.resource_id = resource_id
        self.lock_type = lock_type
        self.owner = owner
        self.timestamp = asyncio.get_event_loop().time()

class LockManager(BaseNode):
    def __init__(self, node_id: str, host: str, port: int):
        super().__init__(node_id, host, port)
        self.raft = RaftConsensus(node_id)
        self.locks: Dict[str, Lock] = {}  # resource_id -> Lock
        self.waiting: Dict[str, Set[str]] = {}  # resource_id -> set of waiting nodes
        
    async def start(self):
        """Start the lock manager node"""
        await self.raft.start(set(self.peers.keys()))
        await super().start()
        
    async def acquire_lock(self, resource_id: str, lock_type: str, requester: str) -> bool:
        """Try to acquire a lock on a resource"""
        if not self.is_leader():
            # Forward request to leader
            return await self.forward_to_leader("acquire_lock", {
                "resource_id": resource_id,
                "lock_type": lock_type,
                "requester": requester
            })
            
        if resource_id not in self.locks:
            # Resource is free
            self.locks[resource_id] = Lock(resource_id, lock_type, requester)
            return True
            
        existing_lock = self.locks[resource_id]
        
        if lock_type == LockType.SHARED and existing_lock.lock_type == LockType.SHARED:
            # Can share the lock
            existing_lock.owner = f"{existing_lock.owner},{requester}"
            return True
            
        # Add to waiting list
        if resource_id not in self.waiting:
            self.waiting[resource_id] = set()
        self.waiting[resource_id].add(requester)
        
        return False
        
    async def release_lock(self, resource_id: str, requester: str) -> bool:
        """Release a lock on a resource"""
        if not self.is_leader():
            # Forward request to leader
            return await self.forward_to_leader("release_lock", {
                "resource_id": resource_id,
                "requester": requester
            })
            
        if resource_id not in self.locks:
            return False
            
        lock = self.locks[resource_id]
        owners = lock.owner.split(",")
        
        if requester not in owners:
            return False
            
        if len(owners) == 1:
            # Last owner, remove the lock
            del self.locks[resource_id]
            
            # Process waiting requests
            if resource_id in self.waiting and self.waiting[resource_id]:
                next_requester = self.waiting[resource_id].pop()
                # Try to acquire lock for waiting requester
                await self.acquire_lock(resource_id, LockType.EXCLUSIVE, next_requester)
        else:
            # Remove requester from shared lock
            owners.remove(requester)
            lock.owner = ",".join(owners)
            
        return True
        
    def is_leader(self) -> bool:
        """Check if this node is the leader"""
        return self.raft.state == "leader"
        
    async def forward_to_leader(self, action: str, params: Dict) -> bool:
        """Forward a request to the leader node"""
        if not self.raft.leader_id or self.raft.leader_id not in self.peers:
            return False
            
        message = {
            "action": action,
            "params": params
        }
        
        try:
            response = await self.send_message(self.raft.leader_id, str(message))
            return response == "True"
        except Exception:
            return False
            
    async def detect_deadlocks(self):
        """Detect deadlocks in the system"""
        # Implementation of deadlock detection algorithm
        # This could use a wait-for graph to detect cycles
        pass
        
    async def handle_message(self, message: str) -> str:
        """Handle incoming messages"""
        try:
            msg = eval(message)  # In production, use proper serialization
            action = msg["action"]
            params = msg["params"]
            
            if action == "acquire_lock":
                result = await self.acquire_lock(
                    params["resource_id"],
                    params["lock_type"],
                    params["requester"]
                )
            elif action == "release_lock":
                result = await self.release_lock(
                    params["resource_id"],
                    params["requester"]
                )
            else:
                result = False
                
            return str(result)
        except Exception as e:
            self.logger.error(f"Error handling message: {e}")
            return str(False)