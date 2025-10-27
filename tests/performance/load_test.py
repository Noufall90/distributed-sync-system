import asyncio
import time
from locust import HttpUser, task, between
from src.nodes.lock_manager import LockManager
from src.nodes.queue_node import QueueNode
from src.nodes.cache_node import CacheNode

class DistributedSystemUser(HttpUser):
    wait_time = between(1, 2)
    
    def on_start(self):
        self.lock_manager = LockManager("test_lock", "localhost", 8001)
        self.queue_node = QueueNode("test_queue", "localhost", 8011)
        self.cache_node = CacheNode("test_cache", "localhost", 8021)
    
    @task(3)
    def test_lock_performance(self):
        resource_id = f"resource_{int(time.time())}"
        start_time = time.time()
        
        # Acquire and release lock
        self.lock_manager.acquire_lock(resource_id, "exclusive", "test_client")
        self.lock_manager.release_lock(resource_id, "test_client")
        
        total_time = time.time() - start_time
        self.environment.events.request_success.fire(
            request_type="Lock",
            name="acquire_release",
            response_time=total_time * 1000,
            response_length=0
        )
    
    @task(2)
    def test_queue_performance(self):
        start_time = time.time()
        
        # Enqueue and dequeue message
        self.queue_node.enqueue("test_queue", "test_message", "test_producer")
        self.queue_node.dequeue("test_queue", "test_consumer")
        
        total_time = time.time() - start_time
        self.environment.events.request_success.fire(
            request_type="Queue",
            name="enqueue_dequeue",
            response_time=total_time * 1000,
            response_length=0
        )
    
    @task(1)
    def test_cache_performance(self):
        key = f"key_{int(time.time())}"
        start_time = time.time()
        
        # Write and read from cache
        self.cache_node.write(key, "test_value")
        self.cache_node.read(key)
        
        total_time = time.time() - start_time
        self.environment.events.request_success.fire(
            request_type="Cache",
            name="write_read",
            response_time=total_time * 1000,
            response_length=0
        )