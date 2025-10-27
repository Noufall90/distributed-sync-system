import asyncio
import logging
from typing import Dict, Set, Optional

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
        
    async def start(self):
        """Start the node server"""
        self.logger.info(f"Starting node {self.node_id} at {self.host}:{self.port}")
        server = await asyncio.start_server(
            self.handle_connection, self.host, self.port
        )
        async with server:
            await server.serve_forever()
            
    async def handle_connection(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        """Handle incoming connections"""
        try:
            data = await reader.read(1024)
            message = data.decode()
            response = await self.handle_message(message)
            writer.write(response.encode())
            await writer.drain()
        except Exception as e:
            self.logger.error(f"Error handling connection: {e}")
        finally:
            writer.close()
            await writer.wait_closed()
            
    async def handle_message(self, message: str) -> str:
        """Handle incoming messages - to be implemented by specific node types"""
        raise NotImplementedError
        
    async def send_message(self, node_id: str, message: str) -> str:
        """Send message to another node"""
        if node_id not in self.peers:
            raise ValueError(f"Unknown node {node_id}")
            
        host, port = self.peers[node_id]
        try:
            reader, writer = await asyncio.open_connection(host, port)
            writer.write(message.encode())
            await writer.drain()
            
            response = await reader.read(1024)
            writer.close()
            await writer.wait_closed()
            
            return response.decode()
        except Exception as e:
            self.logger.error(f"Error sending message to {node_id}: {e}")
            raise
            
    def add_peer(self, node_id: str, host: str, port: int):
        """Add a peer node"""
        self.peers[node_id] = (host, port)
        self.logger.info(f"Added peer {node_id} at {host}:{port}")
        
    def remove_peer(self, node_id: str):
        """Remove a peer node"""
        if node_id in self.peers:
            del self.peers[node_id]
            self.logger.info(f"Removed peer {node_id}")