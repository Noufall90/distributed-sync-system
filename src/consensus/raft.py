import asyncio
import random
import time
from enum import Enum
from typing import Dict, List, Optional, Set
import logging

logger = logging.getLogger("Raft")

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
        
        # Peers and communication
        self.peers: Set[str] = set()
        self.peer_info: Dict[str, Dict[str, str]] = {}  # peer_id -> {host, port}
        self.send_message_func = None  # Will be set by node
        
    def _get_random_timeout(self) -> float:
        """Get a random election timeout"""
        return random.uniform(self.election_timeout_min, self.election_timeout_max)
        
    async def start(self, peers: Set[str], peer_info: Dict[str, Dict[str, str]] = None):
        """Start the Raft consensus process
        
        Args:
            peers: Set of peer node IDs (excluding self)
            peer_info: Dict mapping peer_id -> {host, port}
        """
        self.peers = peers
        self.peer_info = peer_info or {}
        self._reset_leader_state()
        self.last_heartbeat = time.time() * 1000
        self.election_timeout = self._get_random_timeout()
        
        logger.info(f"Raft consensus starting for node {self.node_id} with peers: {peers}")
        
        # For testing/demo: if no peers or in single-node mode, become leader immediately
        if not peers or len(peers) == 0:
            logger.info(f"Single-node mode: {self.node_id} becomes leader immediately")
            self.state = NodeState.LEADER
            self.leader_id = self.node_id
            asyncio.create_task(self._send_heartbeats())
        else:
            # Multi-node: start election after brief delay
            logger.info(f"Multi-node mode: starting election after delay")
            await asyncio.sleep(random.uniform(0.5, 1.5))
            await self.start_election()
        
    def _reset_leader_state(self):
        """Reset leader state when transitioning to leader"""
        last_log_index = len(self.log) - 1
        self.next_index = {peer: last_log_index + 1 for peer in self.peers}
        self.match_index = {peer: -1 for peer in self.peers}
        
    async def start_election(self):
        """Start a new election
        
        For demo: use sorted node IDs to deterministically elect leader
        First node (alphabetically) becomes leader
        """
        self.state = NodeState.CANDIDATE
        self.current_term += 1
        self.voted_for = self.node_id
        self.election_timeout = self._get_random_timeout()
        self.last_heartbeat = time.time() * 1000
        
        logger.info(f"Starting election in term {self.current_term} for node {self.node_id}")
        
        # Deterministic election: all nodes with lowest ID becomes leader
        all_nodes = {self.node_id} | self.peers
        sorted_nodes = sorted(list(all_nodes))
        leader_candidate = sorted_nodes[0]
        
        logger.info(f"Election: candidates are {sorted_nodes}, leader should be {leader_candidate}")
        
        if leader_candidate == self.node_id:
            logger.info(f"Election won: {self.node_id} is leader (lowest node ID)")
            await self.become_leader()
        else:
            logger.info(f"Election lost: {leader_candidate} is leader (lower node ID)")
            self.state = NodeState.FOLLOWER
            self.leader_id = leader_candidate
                
    async def become_leader(self):
        """Transition to leader state"""
        if self.state == NodeState.CANDIDATE:
            self.state = NodeState.LEADER
            self.leader_id = self.node_id
            self._reset_leader_state()
            logger.info(f"Node {self.node_id} became LEADER in term {self.current_term}")
            
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
        """Request a vote from a peer
        
        Returns True if peer votes for us, False otherwise
        """
        try:
            # For demo: every peer votes for any candidate
            # In real Raft, peer would check last log index/term
            logger.debug(f"Requesting vote from {peer} for term {self.current_term}")
            return True
        except Exception as e:
            logger.debug(f"Vote request to {peer} failed: {e}")
            return False
        
    async def _append_entries(self, peer: str) -> bool:
        """Send AppendEntries RPC to a peer"""
        # Simplified heartbeat: always succeeds
        # In real Raft, this would replicate log entries
        return True
        
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