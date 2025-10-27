import asyncio
import time
from typing import Dict, Set

class FailureDetector:
    def __init__(self, node_id: str, timeout: float = 5.0):
        self.node_id = node_id
        self.timeout = timeout
        self.last_heartbeat: Dict[str, float] = {}
        self.suspected_nodes: Set[str] = set()
        self.alive_nodes: Set[str] = set()
        
    def heartbeat(self, node_id: str):
        """Record heartbeat from a node"""
        self.last_heartbeat[node_id] = time.time()
        if node_id in self.suspected_nodes:
            self.suspected_nodes.remove(node_id)
        self.alive_nodes.add(node_id)
        
    def suspect(self, node_id: str):
        """Mark a node as suspected of failure"""
        self.suspected_nodes.add(node_id)
        if node_id in self.alive_nodes:
            self.alive_nodes.remove(node_id)
        
    async def start_monitoring(self):
        """Start monitoring nodes for failures"""
        while True:
            current_time = time.time()
            
            # Check each node's last heartbeat
            for node_id, last_time in self.last_heartbeat.items():
                if current_time - last_time > self.timeout:
                    self.suspect(node_id)
                    
            await asyncio.sleep(1)  # Check every second
            
    def get_alive_nodes(self) -> Set[str]:
        """Get list of nodes considered alive"""
        return self.alive_nodes.copy()
        
    def get_suspected_nodes(self) -> Set[str]:
        """Get list of nodes suspected of failure"""
        return self.suspected_nodes.copy()
        
    def is_node_alive(self, node_id: str) -> bool:
        """Check if a node is considered alive"""
        return node_id in self.alive_nodes