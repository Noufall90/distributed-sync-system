import asyncio
import random
import time
from enum import Enum
from typing import Dict, List, Optional, Set

class NodeState(Enum):
    FOLLOWER = "follower"
    CANDIDATE = "candidate"
    LEADER = "leader"

class RaftConsensus:
    def __init__(self, node_id: str):
        self.node_id = node_id
        self.current_term = 0
        self.voted_for: Optional[str] = None
        self.state = NodeState.FOLLOWER
        self.leader_id: Optional[str] = None
        
        # Raft timing constants
        self.election_timeout_min = 150  # ms
        self.election_timeout_max = 300  # ms
        self.heartbeat_interval = 50  # ms
        
        # Log entries
        self.log: List[Dict] = []
        self.commit_index = -1
        self.last_applied = -1
        
        # Leader state
        self.next_index: Dict[str, int] = {}
        self.match_index: Dict[str, int] = {}
        
        # Timer for election timeout
        self.last_heartbeat = time.time() * 1000
        self.election_timeout = self._get_random_timeout()
        
    def _get_random_timeout(self) -> float:
        """Get a random election timeout"""
        return random.uniform(self.election_timeout_min, self.election_timeout_max)
        
    async def start(self, peers: Set[str]):
        """Start the Raft consensus process"""
        self.peers = peers
        self._reset_leader_state()
        asyncio.create_task(self._election_timer())
        
    def _reset_leader_state(self):
        """Reset leader state when transitioning to leader"""
        last_log_index = len(self.log) - 1
        self.next_index = {peer: last_log_index + 1 for peer in self.peers}
        self.match_index = {peer: -1 for peer in self.peers}
        
    async def _election_timer(self):
        """Monitor election timeout and trigger election if needed"""
        while True:
            await asyncio.sleep(0.01)  # 10ms check interval
            
            current_time = time.time() * 1000
            if (self.state != NodeState.LEADER and 
                current_time - self.last_heartbeat > self.election_timeout):
                await self.start_election()
                
    async def start_election(self):
        """Start a new election"""
        self.state = NodeState.CANDIDATE
        self.current_term += 1
        self.voted_for = self.node_id
        self.election_timeout = self._get_random_timeout()
        self.last_heartbeat = time.time() * 1000
        
        votes_received = 1  # Vote for self
        
        # Request votes from all peers
        for peer in self.peers:
            try:
                vote_granted = await self._request_vote(peer)
                if vote_granted:
                    votes_received += 1
            except Exception:
                continue
                
            # Check if we have majority
            if votes_received > (len(self.peers) + 1) // 2:
                await self.become_leader()
                break
                
    async def become_leader(self):
        """Transition to leader state"""
        if self.state == NodeState.CANDIDATE:
            self.state = NodeState.LEADER
            self.leader_id = self.node_id
            self._reset_leader_state()
            
            # Start sending heartbeats
            asyncio.create_task(self._send_heartbeats())
            
    async def _send_heartbeats(self):
        """Send heartbeats to all peers periodically"""
        while self.state == NodeState.LEADER:
            for peer in self.peers:
                try:
                    await self._append_entries(peer)
                except Exception:
                    continue
            await asyncio.sleep(self.heartbeat_interval / 1000)
            
    async def _request_vote(self, peer: str) -> bool:
        """Send RequestVote RPC to a peer"""
        # Implementation would make RPC call to peer
        # Returns whether vote was granted
        pass
        
    async def _append_entries(self, peer: str) -> bool:
        """Send AppendEntries RPC to a peer"""
        # Implementation would make RPC call to peer
        # Returns whether entries were accepted
        pass
        
    def handle_append_entries(self, term: int, leader_id: str, entries: List[Dict]) -> bool:
        """Handle incoming AppendEntries RPC"""
        if term < self.current_term:
            return False
            
        self.last_heartbeat = time.time() * 1000
        
        if term > self.current_term:
            self.current_term = term
            self.state = NodeState.FOLLOWER
            self.voted_for = None
            
        self.leader_id = leader_id
        
        # Handle log entries...
        return True
        
    def handle_request_vote(self, term: int, candidate_id: str) -> bool:
        """Handle incoming RequestVote RPC"""
        if term < self.current_term:
            return False
            
        if term > self.current_term:
            self.current_term = term
            self.state = NodeState.FOLLOWER
            self.voted_for = None
            
        if (self.voted_for is None or self.voted_for == candidate_id):
            self.voted_for = candidate_id
            self.last_heartbeat = time.time() * 1000
            return True
            
        return False