import asyncio
import time
import random
from locust import HttpUser, task, between
from typing import List, Dict, Any

class LoadTestScenarios:
    def __init__(self, host: str, port: int):
        self.base_url = f"http://{host}:{port}"
        
    async def lock_contention_scenario(self, num_clients: int, duration: int):
        """Test lock contention with multiple clients"""
        async def client_routine(client_id: str):
            start_time = time.time()
            locks_acquired = 0
            
            while time.time() - start_time < duration:
                resource = f"resource_{random.randint(1, 10)}"
                try:
                    response = await self.acquire_lock(resource, "exclusive", client_id)
                    if response.get("success"):
                        locks_acquired += 1
                        await asyncio.sleep(0.1)  # Hold lock briefly
                        await self.release_lock(resource, client_id)
                except Exception:
                    continue
            return locks_acquired
            
        tasks = [client_routine(f"client_{i}") for i in range(num_clients)]
        results = await asyncio.gather(*tasks)
        
        return {
            "total_locks_acquired": sum(results),
            "locks_per_client": results,
            "avg_locks_per_client": sum(results) / len(results)
        }
        
    async def queue_throughput_scenario(self, num_producers: int, num_consumers: int, 
                                     duration: int):
        """Test queue throughput with multiple producers and consumers"""
        messages: List[Dict[str, Any]] = []
        
        async def producer_routine(producer_id: str):
            start_time = time.time()
            messages_sent = 0
            
            while time.time() - start_time < duration:
                message = {
                    "id": f"{producer_id}_{messages_sent}",
                    "timestamp": time.time()
                }
                try:
                    response = await self.enqueue_message("test_queue", message)
                    if response.get("success"):
                        messages_sent += 1
                        messages.append(message)
                except Exception:
                    continue
            return messages_sent
            
        async def consumer_routine(consumer_id: str):
            start_time = time.time()
            messages_received = 0
            
            while time.time() - start_time < duration:
                try:
                    message = await self.dequeue_message("test_queue")
                    if message:
                        messages_received += 1
                        latency = time.time() - message["timestamp"]
                        await self.ack_message("test_queue", message["id"])
                except Exception:
                    continue
            return messages_received
            
        producer_tasks = [producer_routine(f"producer_{i}") 
                         for i in range(num_producers)]
        consumer_tasks = [consumer_routine(f"consumer_{i}") 
                         for i in range(num_consumers)]
        
        all_tasks = producer_tasks + consumer_tasks
        results = await asyncio.gather(*all_tasks)
        
        total_produced = sum(results[:num_producers])
        total_consumed = sum(results[num_producers:])
        
        return {
            "messages_produced": total_produced,
            "messages_consumed": total_consumed,
            "throughput_per_second": total_produced / duration
        }
        
    async def cache_performance_scenario(self, num_clients: int, duration: int,
                                      read_write_ratio: float = 0.8):
        """Test cache performance with different read/write ratios"""
        async def client_routine(client_id: str):
            start_time = time.time()
            operations = {"reads": 0, "writes": 0, "hits": 0, "misses": 0}
            
            while time.time() - start_time < duration:
                key = f"key_{random.randint(1, 1000)}"
                
                if random.random() < read_write_ratio:
                    # Read operation
                    try:
                        result = await self.read_cache(key)
                        operations["reads"] += 1
                        if result:
                            operations["hits"] += 1
                        else:
                            operations["misses"] += 1
                    except Exception:
                        continue
                else:
                    # Write operation
                    try:
                        value = f"value_{random.randint(1, 1000)}"
                        await self.write_cache(key, value)
                        operations["writes"] += 1
                    except Exception:
                        continue
                        
            return operations
            
        tasks = [client_routine(f"client_{i}") for i in range(num_clients)]
        results = await asyncio.gather(*tasks)
        
        totals = {
            "reads": sum(r["reads"] for r in results),
            "writes": sum(r["writes"] for r in results),
            "hits": sum(r["hits"] for r in results),
            "misses": sum(r["misses"] for r in results)
        }
        
        return {
            **totals,
            "hit_ratio": totals["hits"] / totals["reads"] if totals["reads"] > 0 else 0,
            "operations_per_second": (totals["reads"] + totals["writes"]) / duration
        }
        
class LoadTestUser(HttpUser):
    wait_time = between(1, 2)
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.scenarios = LoadTestScenarios(self.host, self.port)
        
    @task(3)
    def test_lock_contention(self):
        asyncio.run(self.scenarios.lock_contention_scenario(10, 60))
        
    @task(2)
    def test_queue_throughput(self):
        asyncio.run(self.scenarios.queue_throughput_scenario(5, 5, 60))
        
    @task(1)
    def test_cache_performance(self):
        asyncio.run(self.scenarios.cache_performance_scenario(10, 60))