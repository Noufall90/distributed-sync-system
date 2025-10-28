import asyncio
import time
from typing import Dict, Set
from consensus.raft import RaftConsensus, NodeState
from nodes.base_node import BaseNode
from fastapi import HTTPException
from pydantic import BaseModel
import json  # Tambahkan untuk JSON handling

class LockType:
    SHARED = "shared"
    EXCLUSIVE = "exclusive"

class Lock:
    def __init__(self, resource_id: str, lock_type: str, owner: str):
        self.resource_id = resource_id
        self.lock_type = lock_type
        self.owner = owner
        self.timestamp = asyncio.get_event_loop().time()

class LockRequest(BaseModel):
    resource_id: str
    lock_type: str
    requester_id: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "resource_id": "resource1",
                "lock_type": "exclusive",  # or "shared"
                "requester_id": "client1"
            }
        }
        
    def validate_lock_type(self):
        if self.lockType not in [LockType.SHARED, LockType.EXCLUSIVE]:
            raise ValueError(
                f"Invalid lock type '{self.lockType}'. Must be either '{LockType.SHARED}' or '{LockType.EXCLUSIVE}'"
            )

class LockManager(BaseNode):
    def __init__(self, node_id: str, host: str, port: int):
        super().__init__(node_id, host, port)
        self.raft = RaftConsensus(node_id)
        self.locks: Dict[str, Lock] = {}  # resource_id -> Lock
        self.waiting: Dict[str, Set[str]] = {}  # resource_id -> set of waiting nodes
        self._leader_election_timeout = 10.0  # Increased to 10 seconds for better reliability

    def setup_routes(self):
        super().setup_routes()

        @self.app.post("/lock")
        async def acquire_lock(request: LockRequest):
            # Validate request data
            if not request.resource_id:
                raise HTTPException(
                    status_code=422, 
                    detail={"error": "Validation Error", "field": "resource_id", "message": "Resource ID is required"}
                )
            if not request.lock_type:
                raise HTTPException(
                    status_code=422, 
                    detail={"error": "Validation Error", "field": "lock_type", "message": "Lock type is required"}
                )
            if not request.requester_id:
                raise HTTPException(
                    status_code=422, 
                    detail={"error": "Validation Error", "field": "requester_id", "message": "Requester ID is required"}
                )
            
            # Validate lock type
            try:
                request.validate_lock_type()
            except ValueError as e:
                raise HTTPException(
                    status_code=422,
                    detail={"error": "Validation Error", "field": "lock_type", "message": str(e)}
                )
            
            try:
                self.check_leader_availability()
                
                if not self.is_leader():
                    try:
                        result = await self.forward_to_leader("acquire_lock", {
                            "resource_id": request.resource_id,
                            "lock_type": request.lock_type,
                            "requester": request.requester_id
                        })
                        if result:
                            return {"success": True, "resourceId": request.resourceId}
                        raise HTTPException(status_code=409, detail="Lock acquisition failed on leader")
                    except HTTPException as he:
                        raise he
                    except Exception as e:
                        raise HTTPException(status_code=500, detail=f"Leader forwarding error: {str(e)}")
                        
                # We are the leader, handle the request using the unified method
                success = await self.acquire_lock(request.resourceId, request.lockType, request.requesterId)
                if success:
                    return {"success": True, "resourceId": request.resourceId}
                else:
                    raise HTTPException(status_code=409, detail="Lock acquisition failed (added to waiting queue)")
                
            except HTTPException:
                raise
            except Exception as e:
                self.logger.error(f"Error in acquire_lock: {str(e)}")
                raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

        @self.app.delete("/lock")
        async def release_lock(resourceId: str, requesterId: str):
            if not resourceId or not requesterId:
                raise HTTPException(status_code=422, detail="resourceId and requesterId are required")
                
            try:
                self.check_leader_availability()
                
                if not self.is_leader():
                    try:
                        result = await self.forward_to_leader("release_lock", {
                            "resource_id": resourceId,
                            "requester": requesterId
                        })
                        if result:
                            return {"success": True}
                        raise HTTPException(status_code=404, detail="Lock not found on leader")
                    except HTTPException as he:
                        raise he
                    except Exception as e:
                        raise HTTPException(status_code=500, detail=f"Leader forwarding error: {str(e)}")
                
                # We are the leader, handle the request using the unified method
                success = await self.release_lock(resourceId, requesterId)
                if success:
                    return {"success": True}
                else:
                    raise HTTPException(status_code=404, detail="Lock release failed")
                
            except HTTPException:
                raise
            except Exception as e:
                self.logger.error(f"Error in release_lock: {str(e)}")
                raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

        @self.app.get("/lock/status")
        async def lock_status(resourceId: str):
            if resourceId in self.locks:
                lock = self.locks[resourceId]
                return {
                    "resourceId": lock.resource_id,
                    "lockType": lock.lock_type,
                    "owner": lock.owner,
                    "status": "locked"
                }
            return {"resourceId": resourceId, "status": "unlocked"}

        @self.app.get("/metrics/locks")
        async def get_metrics():
            return {
                "active_locks": len(self.locks),
                "waiting_requests": sum(len(waiting) for waiting in self.waiting.values()),
                "leader": self.is_leader(),
                "term": getattr(self, 'current_term', None)
            }

        @self.app.get("/metrics/health")
        async def health_check():
            return {
                "status": "healthy",
                "node_id": self.node_id,
                "is_leader": self.is_leader()
            }
        
    async def start(self):
        """Start the lock manager node"""
        await super().start()
        await self.raft.start(set(self.peers.keys()))
        
        # Handle single-node mode: If no peers, set self as leader
        if not self.peers:
            self.raft.leader_id = self.node_id
            self.raft.state = NodeState.LEADER
            self.logger.info(f"Single-node mode: Set {self.node_id} as leader")
            return
        
        # Wait for initial leader election
        start_time = time.time()
        while not self.raft.leader_id:
            if time.time() - start_time > self._leader_election_timeout:
                self.logger.warning("Initial leader election timed out")
                break
            await asyncio.sleep(0.1)
        
    async def acquire_lock(self, resource_id: str, lock_type: str, requester: str) -> bool:
        """Try to acquire a lock on a resource"""
        if not resource_id or not lock_type or not requester:
            raise HTTPException(status_code=422, detail="Resource ID, lock type, and requester are required")
            
        if lock_type not in [LockType.SHARED, LockType.EXCLUSIVE]:
            raise HTTPException(status_code=422, detail=f"Invalid lock type. Must be either '{LockType.SHARED}' or '{LockType.EXCLUSIVE}'")
            
        if not self.is_leader():
            return await self.forward_to_leader("acquire_lock", {
                "resource_id": resource_id,
                "lock_type": lock_type,
                "requester": requester
            })
            
        try:
            if resource_id not in self.locks:
                # Resource is free
                self.locks[resource_id] = Lock(resource_id, lock_type, requester)
                return True
                
            existing_lock = self.locks[resource_id]
            owners = existing_lock.owner.split(',')
            
            # Check if requester already holds the lock
            if requester in owners:
                raise HTTPException(status_code=409, detail="You already hold this lock")
                
            if lock_type == LockType.SHARED and existing_lock.lock_type == LockType.SHARED:
                # Can share the lock
                existing_lock.owner = f"{existing_lock.owner},{requester}"
                return True
                
            # Add to waiting list
            if resource_id not in self.waiting:
                self.waiting[resource_id] = set()
            self.waiting[resource_id].add(requester)
            
            return False
        except HTTPException:
            raise
        except Exception as e:
            self.logger.error(f"Error acquiring lock: {e}")
            raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
        
    async def release_lock(self, resource_id: str, requester: str) -> bool:
        """Release a lock on a resource"""
        if not resource_id or not requester:
            raise HTTPException(status_code=422, detail="Resource ID and requester are required")
            
        if not self.is_leader():
            return await self.forward_to_leader("release_lock", {
                "resource_id": resource_id,
                "requester": requester
            })
            
        try:
            if resource_id not in self.locks:
                self.logger.warning(f"Attempt to release non-existent lock: {resource_id}")
                raise HTTPException(status_code=404, detail="Lock not found")
                
            lock = self.locks[resource_id]
            owners = lock.owner.split(",")
            
            if requester not in owners:
                self.logger.warning(f"Requester {requester} does not own lock {resource_id}")
                raise HTTPException(status_code=403, detail="You don't own this lock")
                
            if len(owners) == 1:
                # Last owner, remove the lock
                del self.locks[resource_id]
                
                # Process waiting requests (grant to next in queue as exclusive)
                if resource_id in self.waiting and self.waiting[resource_id]:
                    try:
                        next_requester = self.waiting[resource_id].pop()
                        await self.acquire_lock(resource_id, LockType.EXCLUSIVE, next_requester)
                    except Exception as e:
                        self.logger.error(f"Error processing waiting request: {e}")
            else:
                # Remove requester from shared lock
                owners.remove(requester)
                lock.owner = ",".join(owners)
                
            return True
        except HTTPException:
            raise
        except Exception as e:
            self.logger.error(f"Error releasing lock: {e}")
            raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
        
    def is_leader(self) -> bool:
        """Check if this node is the leader"""
        return self.raft.state == NodeState.LEADER
        
    def check_leader_availability(self):
        """Check if a leader is available and raise appropriate exception if not"""
        if not self.raft.leader_id:
            raise HTTPException(
                status_code=503,
                detail="No leader available. The cluster is currently electing a leader."
            )
        if not self.is_leader() and not self.peers.get(self.raft.leader_id):
            raise HTTPException(
                status_code=503,
                detail=f"Leader node {self.raft.leader_id} is not in peer list"
            )
        
    async def forward_to_leader(self, action: str, params: Dict) -> bool:
        """Forward a request to the leader node"""
        if not self.raft.leader_id:
            raise HTTPException(
                status_code=503,
                detail="No leader available. The cluster is currently electing a leader."
            )
            
        if self.raft.leader_id not in self.peers:
            raise HTTPException(
                status_code=503,
                detail=f"Leader node {self.raft.leader_id} is not in peers list"
            )
            
        message = {
            "action": action,
            "params": params
        }
        
        try:
            response = await self.send_message(self.raft.leader_id, json.dumps(message))  # Send as JSON string
            if response is None:
                raise HTTPException(
                    status_code=503,
                    detail=f"Failed to communicate with leader node {self.raft.leader_id}"
                )
            # Parse response as JSON and check success
            response_data = json.loads(response)
            return response_data.get("success", False)
        except Exception as e:
            raise HTTPException(
                status_code=503,
                detail=f"Error forwarding request to leader: {str(e)}"
            )
            
    async def detect_deadlocks(self):
        """Detect deadlocks in the system"""
        # Implementation of deadlock detection algorithm
        # This could use a wait-for graph to detect cycles
        pass
        
    async def handle_message(self, message: dict) -> str:  # Changed return type to str for JSON
        """Handle incoming messages"""
        try:
            if not isinstance(message, dict):
                raise ValueError("Invalid message format")
                
            action = message.get("action")
            params = message.get("params", {})
            
            if not action:
                raise ValueError("Action is required")
                
            if not params:
                raise ValueError("Parameters are required")
                
            if action == "acquire_lock":
                if not all(k in params for k in ["resource_id", "lock_type", "requester"]):
                    raise ValueError("Missing required parameters for acquire_lock")
                    
                result = await self.acquire_lock(
                    params["resource_id"],
                    params["lock_type"],
                    params["requester"]
                )
            elif action == "release_lock":
                if not all(k in params for k in ["resource_id", "requester"]):
                    raise ValueError("Missing required parameters for release_lock")
                    
                result = await self.release_lock(
                    params["resource_id"],
                    params["requester"]
                )
            else:
                raise ValueError(f"Unknown action: {action}")
                
            return json.dumps({"success": result})  # Return as JSON string
        except ValueError as e:
            self.logger.warning(f"Invalid message format or parameters: {e}")
            return json.dumps({"error": str(e), "success": False})
        except Exception as e:
            self.logger.error(f"Error handling message: {e}")
            return json.dumps({"error": str(e), "success": False})
