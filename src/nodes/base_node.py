import asyncio
import logging
import json
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
            data = await asyncio.wait_for(reader.read(4096), timeout=10.0)
            message = data.decode()
            try:
                message_dict = json.loads(message)
                response = await self.handle_message(message_dict)
                # Ensure response is JSON string
                if isinstance(response, str):
                    writer.write(response.encode())
                else:
                    writer.write(json.dumps(response).encode())
            except json.JSONDecodeError:
                self.logger.error("Invalid JSON received")
                writer.write(json.dumps({"error": "Invalid JSON format"}).encode())
            await writer.drain()
        except asyncio.TimeoutError:
            self.logger.error("Connection timeout")
            try:
                writer.write(json.dumps({"error": "Connection timeout"}).encode())
                await writer.drain()
            except:
                pass
        except Exception as e:
            self.logger.error(f"Error handling connection: {e}")
            try:
                writer.write(json.dumps({"error": str(e)}).encode())
                await writer.drain()
            except:
                pass
        finally:
            try:
                writer.close()
                await writer.wait_closed()
            except:
                pass
            
    async def handle_message(self, message: str) -> str:
        """Handle incoming messages - to be implemented by specific node types"""
        raise NotImplementedError
        
    async def send_message(self, node_id: str, message: str) -> Union[bool, dict, None, str]:
        """Send message to another node"""
        if node_id not in self.peers:
            raise HTTPException(
                status_code=404,
                detail=f"Unknown node {node_id}"
            )
            
        host, port = self.peers[node_id]
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(host, port),
                timeout=5.0
            )
            
            # If message is dict, convert to JSON
            if isinstance(message, dict):
                message = json.dumps(message)
                
            writer.write(message.encode())
            await writer.drain()
            
            response = await asyncio.wait_for(reader.read(4096), timeout=5.0)
            writer.close()
            await writer.wait_closed()
            
            if not response:
                return None
                
            try:
                # Try to parse as JSON first
                response_str = response.decode()
                return json.loads(response_str)
            except (json.JSONDecodeError, UnicodeDecodeError):
                response_str = response.decode()
                # Return as string if not JSON
                if response_str.lower() == "true":
                    return True
                elif response_str.lower() == "false":
                    return False
                return response_str
                
        except asyncio.TimeoutError:
            self.logger.error(f"Timeout while connecting to node {node_id}")
            return None
        except ConnectionRefusedError:
            self.logger.error(f"Node {node_id} is not accessible at {host}:{port}")
            return None
        except Exception as e:
            self.logger.error(f"Error sending message to {node_id}: {e}")
            return None
            
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