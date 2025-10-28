# Tutorial Testing Distributed Sync System dengan Bruno API

## 1. Testing Distributed Lock Manager

### 1.1 Acquire Lock (POST)
```http
POST http://localhost:8001/lock
Content-Type: application/json

{
    "resourceId": "resource1",
    "lockType": "exclusive",
    "requesterId": "client1"
}
```

### 1.2 Release Lock (DELETE)
```http
DELETE http://localhost:8001/lock?resourceId=resource1&requesterId=client1
```

### 1.3 Check Lock Status (GET)
```http
GET http://localhost:8001/lock/status?resourceId=resource1
```

## 2. Testing Distributed Queue System

### 2.1 Enqueue Message (POST)
```http
POST http://localhost:8011/queue/testQueue
Content-Type: application/json

{
    "message": "test message",
    "producerId": "producer1"
}
```

### 2.2 Dequeue Message (GET)
```http
GET http://localhost:8011/queue/testQueue?consumerId=consumer1
```

### 2.3 Acknowledge Message (POST)
```http
POST http://localhost:8011/queue/testQueue/ack
Content-Type: application/json

{
    "messageId": "testQueue:producer1:timestamp",
    "consumerId": "consumer1"
}
```

## 3. Testing Cache System

### 3.1 Write to Cache (PUT)
```http
PUT http://localhost:8021/cache/testKey
Content-Type: application/json

{
    "value": "test value"
}
```

### 3.2 Read from Cache (GET)
```http
GET http://localhost:8021/cache/testKey
```

## 4. Test Scenarios

### 4.1 Lock Manager Testing

1. Test Shared Locks:
```http
POST http://localhost:8001/lock
Content-Type: application/json

{
    "resourceId": "sharedResource",
    "lockType": "shared",
    "requesterId": "client1"
}
```

2. Test Lock Conflicts:
   - Acquire shared lock with client1
   - Attempt to acquire exclusive lock with client2 (should fail)
   - Release shared lock
   - Acquire exclusive lock (should succeed)

### 4.2 Queue System Testing

1. Test Message Persistence:
   - Enqueue multiple messages
   - Stop and restart queue node
   - Verify messages are still available

2. Test At-least-once Delivery:
   - Enqueue message
   - Dequeue without acknowledgment
   - Dequeue again (should receive same message)
   - Acknowledge message
   - Dequeue again (should receive nothing)

### 4.3 Cache Testing

1. Test Cache Coherence:
   - Write value to cache-node-1
   - Read from cache-node-2 (should get same value)
   - Update value in cache-node-2
   - Read from cache-node-1 (should get updated value)

2. Test Cache Invalidation:
   - Write value to multiple nodes
   - Update value in one node
   - Verify other nodes show invalidated state

## 5. Performance Testing

### 5.1 Lock Manager Performance:
```http
GET http://localhost:8001/metrics/locks
```

### 5.2 Queue Performance:
```http
GET http://localhost:8011/metrics/queue
```

### 5.3 Cache Performance:
```http
GET http://localhost:8021/metrics/cache
```

## 6. Common Headers for All Requests

```
{
    "Accept": "application/json",
    "Content-Type": "application/json"
}
```

## 7. Error Handling Testing

### 7.1 Invalid Lock Request:
```http
POST http://localhost:8001/lock
Content-Type: application/json

{
    "resourceId": "resource1",
    "lockType": "invalid_type",  // Should return 400 Bad Request
    "requesterId": "client1"
}
```

### 7.2 Non-existent Queue:
```http
GET http://localhost:8011/queue/nonexistent?consumerId=consumer1
```

### 7.3 Invalid Cache Operation:
```http
PUT http://localhost:8021/cache/   // Missing key, should return 400
Content-Type: application/json

{
    "value": "test"
}
```

## 8. Network Partition Testing

1. Test Leader Election:
   - Stop current leader node
   - Verify new leader is elected
   - Check system continues to function

2. Test Queue Distribution:
   - Stop primary queue node
   - Verify messages are rerouted to backup nodes
   - Check no messages are lost

## 9. Testing Environment Setup

1. Start the system:
```bash
cd docker
docker-compose up --build
```

2. Verify all nodes are running:
```http
GET http://localhost:8001/health
GET http://localhost:8011/health
GET http://localhost:8021/health
```

## 10. Monitoring Points

- Watch for deadlocks in lock manager
- Monitor queue length and message latency
- Track cache hit/miss ratios
- Observe node status changes
