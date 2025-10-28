import asyncio
import logging
from typing import Dict, Set, Optional, Union
from fastapi import FastAPI, HTTPException
import uvicorn
from pydantic import BaseModel

class BaseNode:
    def __init__(self, node_id: str, host: str, port: int):
        self.node_id = node_id
        self.host = host
        self.port = port
        self.peers: Dict[str, tuple] = {}  # node_id -> (host, port)
        self.state = "follower"
        self.current_term = 0
        self.voted_for: Optional[str] = None
        self.leader_id: Optional[str] = None
        self.logger = logging.getLogger(f"Node-{node_id}")
        self.app = FastAPI()
        self.setup_routes()

    def setup_routes(self):
        """Setup FastAPI routes - to be implemented by specific node types"""
        @self.app.get("/health")
        async def health_check():
            return {"status": "healthy", "node_id": self.node_id}
        
    async def start(self):
        """Start the node server"""
        self.logger.info(f"Starting node {self.node_id} at {self.host}:{self.port}")
        config = uvicorn.Config(self.app, host=self.host, port=self.port)
        server = uvicorn.Server(config)
        await server.serve()
            
    async def handle_connection(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        """Handle incoming connections"""
        try:
            data = await reader.read(1024)
            message = data.decode()
            try:
                import json
                message_dict = json.loads(message)
                response = await self.handle_message(message_dict)
                writer.write(json.dumps(response).encode())
            except json.JSONDecodeError:
                self.logger.error("Invalid JSON received")
                writer.write(json.dumps({"error": "Invalid JSON format"}).encode())
            await writer.drain()
        except Exception as e:
            self.logger.error(f"Error handling connection: {e}")
            try:
                writer.write(json.dumps({"error": str(e)}).encode())
                await writer.drain()
            except:
                pass
        finally:
            writer.close()
            await writer.wait_closed()
            
    async def handle_message(self, message: str) -> str:
        """Handle incoming messages - to be implemented by specific node types"""
        raise NotImplementedError
        
    async def send_message(self, node_id: str, message: str) -> Union[bool, dict, None]:
        """Send message to another node"""
        if node_id not in self.peers:
            raise HTTPException(
                status_code=404,
                detail=f"Unknown node {node_id}"
            )
            
        host, port = self.peers[node_id]
        try:
            reader, writer = await asyncio.open_connection(host, port)
            writer.write(message.encode())
            await writer.drain()
            
            response = await reader.read(1024)
            writer.close()
            await writer.wait_closed()
            
            if not response:
                return None
                
            try:
                import json
                return json.loads(response.decode())
            except json.JSONDecodeError:
                response_str = response.decode()
                if response_str.lower() == "true":
                    return True
                elif response_str.lower() == "false":
                    return False
                return response_str
                
        except ConnectionRefusedError:
            raise HTTPException(
                status_code=503,
                detail=f"Node {node_id} is not accessible"
            )
        except asyncio.TimeoutError:
            raise HTTPException(
                status_code=504,
                detail=f"Timeout while connecting to node {node_id}"
            )
        except Exception as e:
            self.logger.error(f"Error sending message to {node_id}: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to communicate with node {node_id}: {str(e)}"
            )
            
    def add_peer(self, node_id: str, host: str, port: int):
        """Add a peer node"""
        self.peers[node_id] = (host, port)
        self.logger.info(f"Added peer {node_id} at {host}:{port}")
        
    def remove_peer(self, node_id: str):
        """Remove a peer node"""
        if node_id in self.peers:
            del self.peers[node_id]
            self.logger.info(f"Removed peer {node_id}")
            
    async def forward_to_leader(self, action: str, params: Dict) -> Union[bool, dict]:
        """Forward a request to the leader node"""
        if not hasattr(self, 'raft') or not self.raft.leader_id:
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
            response = await self.send_message(self.raft.leader_id, str(message))
            if response is None:
                raise HTTPException(
                    status_code=503,
                    detail=f"Failed to communicate with leader node {self.raft.leader_id}"
                )
            return response
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=503,
                detail=f"Error forwarding request to leader: {str(e)}"
            )