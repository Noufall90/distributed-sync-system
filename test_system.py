#!/usr/bin/env python3
"""
Quick test script to verify the distributed sync system
"""
import asyncio
import httpx
import time
import sys
import uuid

BASE_URL = "http://localhost:8001"
QUEUE_URL = "http://localhost:8011"
CACHE_URL = "http://localhost:8021"

# Generate unique IDs for this test run
TEST_RUN_ID = str(uuid.uuid4())[:8]
RESOURCE_ID = f"test_resource_{TEST_RUN_ID}"
REQUESTER_ID = f"test_client_{TEST_RUN_ID}"

async def test_health_check():
    """Test if nodes are healthy"""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{BASE_URL}/health", timeout=5.0)
            print(f"✅ Health check: {response.status_code}")
            return response.status_code == 200
        except Exception as e:
            print(f"❌ Health check failed: {e}")
            return False

async def test_acquire_lock():
    """Test lock acquisition"""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{BASE_URL}/lock",
                json={
                    "resource_id": RESOURCE_ID,
                    "lock_type": "exclusive",
                    "requester_id": REQUESTER_ID
                },
                timeout=5.0
            )
            print(f"✅ Acquire lock: {response.status_code}")
            print(f"   Response: {response.json()}")
            return response.status_code == 200
        except Exception as e:
            print(f"❌ Acquire lock failed: {e}")
            return False

async def test_release_lock():
    """Test lock release"""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.delete(
                f"{BASE_URL}/lock",
                params={
                    "resource_id": RESOURCE_ID,
                    "requester_id": REQUESTER_ID
                },
                timeout=5.0
            )
            print(f"✅ Release lock: {response.status_code}")
            print(f"   Response: {response.json()}")
            return response.status_code == 200
        except Exception as e:
            print(f"❌ Release lock failed: {e}")
            return False

async def test_enqueue_message():
    """Test message enqueueing"""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{QUEUE_URL}/queue/test_queue",
                json={
                    "message": "Test message",
                    "producerId": "test_producer"
                },
                timeout=5.0
            )
            print(f"✅ Enqueue message: {response.status_code}")
            print(f"   Response: {response.json()}")
            return response.status_code == 200
        except Exception as e:
            print(f"❌ Enqueue message failed: {e}")
            return False

async def test_cache_write():
    """Test cache write"""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{CACHE_URL}/cache/test_key",
                json={"value": "test_value"},
                timeout=5.0
            )
            print(f"✅ Cache write: {response.status_code}")
            print(f"   Response: {response.json()}")
            return response.status_code == 200
        except Exception as e:
            print(f"❌ Cache write failed: {e}")
            return False

async def test_cache_read():
    """Test cache read"""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{CACHE_URL}/cache/test_key",
                timeout=5.0
            )
            print(f"✅ Cache read: {response.status_code}")
            print(f"   Response: {response.json()}")
            return response.status_code == 200
        except Exception as e:
            print(f"❌ Cache read failed: {e}")
            return False

async def run_tests():
    """Run all tests"""
    print("=" * 50)
    print("Starting Distributed Sync System Tests")
    print("=" * 50)
    print()
    
    print("Waiting 5 seconds for services to be ready...")
    await asyncio.sleep(5)
    print()
    
    tests = [
        ("Health Check", test_health_check),
        ("Acquire Lock", test_acquire_lock),
        ("Release Lock", test_release_lock),
        ("Enqueue Message", test_enqueue_message),
        ("Cache Write", test_cache_write),
        ("Cache Read", test_cache_read),
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n[TEST] {test_name}")
        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            results.append((test_name, False))
    
    print()
    print("=" * 50)
    print("Test Summary")
    print("=" * 50)
    passed = sum(1 for _, result in results if result)
    total = len(results)
    print(f"Passed: {passed}/{total}")
    for test_name, result in results:
        status = "✅" if result else "❌"
        print(f"{status} {test_name}")
    
    if passed == total:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(run_tests())
    sys.exit(exit_code)
