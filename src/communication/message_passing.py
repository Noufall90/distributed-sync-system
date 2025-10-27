import asyncio
import json
import logging
from typing import Any, Dict, Optional

class MessagePassing:
    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port
        self.logger = logging.getLogger("MessagePassing")
        
    async def send_message(self, target_host: str, target_port: int, message: Dict[str, Any]) -> Optional[Dict]:
        """Send a message to another node and wait for response"""
        try:
            reader, writer = await asyncio.open_connection(target_host, target_port)
            
            # Send message
            data = json.dumps(message).encode()
            writer.write(data)
            await writer.drain()
            
            # Wait for response
            response_data = await reader.read(1024)
            response = json.loads(response_data.decode())
            
            writer.close()
            await writer.wait_closed()
            
            return response
        except Exception as e:
            self.logger.error(f"Error sending message to {target_host}:{target_port}: {e}")
            return None
            
    async def start_server(self, message_handler):
        """Start message passing server"""
        server = await asyncio.start_server(
            lambda r, w: self.handle_connection(r, w, message_handler),
            self.host,
            self.port
        )
        
        async with server:
            await server.serve_forever()
            
    async def handle_connection(self, reader: asyncio.StreamReader, 
                              writer: asyncio.StreamWriter,
                              message_handler):
        """Handle incoming connection"""
        try:
            data = await reader.read(1024)
            message = json.loads(data.decode())
            
            response = await message_handler(message)
            writer.write(json.dumps(response).encode())
            await writer.drain()
        except Exception as e:
            self.logger.error(f"Error handling connection: {e}")
            writer.write(json.dumps({"error": str(e)}).encode())
            await writer.drain()
        finally:
            writer.close()
            await writer.wait_closed()