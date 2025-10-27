import time
from typing import Dict, List
from prometheus_client import Counter, Gauge, Histogram

class Metrics:
    def __init__(self):
        # Lock metrics
        self.lock_acquisitions = Counter(
            'lock_acquisitions_total',
            'Total number of lock acquisitions',
            ['lock_type']
        )
        self.lock_acquisition_time = Histogram(
            'lock_acquisition_seconds',
            'Time taken to acquire locks',
            ['lock_type']
        )
        self.active_locks = Gauge(
            'active_locks',
            'Number of currently held locks',
            ['lock_type']
        )
        
        # Queue metrics
        self.messages_enqueued = Counter(
            'messages_enqueued_total',
            'Total number of messages enqueued'
        )
        self.messages_dequeued = Counter(
            'messages_dequeued_total',
            'Total number of messages dequeued'
        )
        self.queue_size = Gauge(
            'queue_size',
            'Current size of queues',
            ['queue_name']
        )
        self.message_latency = Histogram(
            'message_latency_seconds',
            'Time between message enqueue and dequeue'
        )
        
        # Cache metrics
        self.cache_hits = Counter(
            'cache_hits_total',
            'Total number of cache hits'
        )
        self.cache_misses = Counter(
            'cache_misses_total',
            'Total number of cache misses'
        )
        self.cache_size = Gauge(
            'cache_size',
            'Current size of cache',
            ['node_id']
        )
        self.cache_operations = Histogram(
            'cache_operation_seconds',
            'Time taken for cache operations',
            ['operation']
        )
        
        # Node metrics
        self.node_uptime = Gauge(
            'node_uptime_seconds',
            'Time since node startup'
        )
        self.node_status = Gauge(
            'node_status',
            'Current status of node',
            ['node_id']
        )
        
        self.start_time = time.time()
        
    def record_lock_acquisition(self, lock_type: str, duration: float):
        """Record a lock acquisition"""
        self.lock_acquisitions.labels(lock_type=lock_type).inc()
        self.lock_acquisition_time.labels(lock_type=lock_type).observe(duration)
        self.active_locks.labels(lock_type=lock_type).inc()
        
    def record_lock_release(self, lock_type: str):
        """Record a lock release"""
        self.active_locks.labels(lock_type=lock_type).dec()
        
    def record_message_enqueue(self, queue_name: str):
        """Record a message being enqueued"""
        self.messages_enqueued.inc()
        self.queue_size.labels(queue_name=queue_name).inc()
        
    def record_message_dequeue(self, queue_name: str, latency: float):
        """Record a message being dequeued"""
        self.messages_dequeued.inc()
        self.queue_size.labels(queue_name=queue_name).dec()
        self.message_latency.observe(latency)
        
    def record_cache_operation(self, operation: str, duration: float):
        """Record a cache operation"""
        self.cache_operations.labels(operation=operation).observe(duration)
        
    def record_cache_hit(self):
        """Record a cache hit"""
        self.cache_hits.inc()
        
    def record_cache_miss(self):
        """Record a cache miss"""
        self.cache_misses.inc()
        
    def update_node_metrics(self, node_id: str, status: str):
        """Update node status metrics"""
        self.node_uptime.set(time.time() - self.start_time)
        self.node_status.labels(node_id=node_id).set(1 if status == "alive" else 0)
        
    def get_summary(self) -> Dict[str, Dict[str, float]]:
        """Get summary of metrics"""
        return {
            "locks": {
                "acquisitions": self.lock_acquisitions._value.sum(),
                "active": self.active_locks._value.sum()
            },
            "queue": {
                "enqueued": self.messages_enqueued._value.sum(),
                "dequeued": self.messages_dequeued._value.sum()
            },
            "cache": {
                "hits": self.cache_hits._value.sum(),
                "misses": self.cache_misses._value.sum(),
                "hit_ratio": (
                    self.cache_hits._value.sum() /
                    (self.cache_hits._value.sum() + self.cache_misses._value.sum())
                    if (self.cache_hits._value.sum() + self.cache_misses._value.sum()) > 0
                    else 0
                )
            }
        }