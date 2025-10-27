import pytest
import asyncio
from src.nodes.lock_manager import LockManager, LockType

@pytest.mark.asyncio
async def test_lock_acquisition():
    # Initialize lock manager
    manager = LockManager("test_node", "localhost", 8000)
    
    # Test shared lock acquisition
    result = await manager.acquire_lock("resource1", LockType.SHARED, "client1")
    assert result == True
    
    # Test another shared lock acquisition on same resource
    result = await manager.acquire_lock("resource1", LockType.SHARED, "client2")
    assert result == True
    
    # Test exclusive lock fails when shared locks exist
    result = await manager.acquire_lock("resource1", LockType.EXCLUSIVE, "client3")
    assert result == False
    
    # Release shared locks
    await manager.release_lock("resource1", "client1")
    await manager.release_lock("resource1", "client2")
    
    # Now exclusive lock should succeed
    result = await manager.acquire_lock("resource1", LockType.EXCLUSIVE, "client3")
    assert result == True

@pytest.mark.asyncio
async def test_deadlock_detection():
    manager = LockManager("test_node", "localhost", 8000)
    
    # Create a deadlock scenario
    await manager.acquire_lock("resource1", LockType.EXCLUSIVE, "client1")
    await manager.acquire_lock("resource2", LockType.EXCLUSIVE, "client2")
    
    # Try to create deadlock
    result1 = await manager.acquire_lock("resource2", LockType.EXCLUSIVE, "client1")
    result2 = await manager.acquire_lock("resource1", LockType.EXCLUSIVE, "client2")
    
    # At least one should be false to prevent deadlock
    assert not (result1 and result2)