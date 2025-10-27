# Deployment Guide

## Prerequisites

- Docker and Docker Compose
- Python 3.8 or higher
- Redis
- Network connectivity between nodes

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/distributed-sync-system.git
cd distributed-sync-system
```

2. Create .env file:
```bash
cp .env.example .env
```

3. Configure environment variables in .env file

4. Install dependencies:
```bash
pip install -r requirements.txt
```

## Deployment Options

### Local Development

1. Start Redis:
```bash
docker run -d -p 6379:6379 redis:6-alpine
```

2. Start nodes:
```bash
python -m src.main
```

### Docker Deployment

1. Build and start all services:
```bash
docker-compose up --build
```

2. Scale specific components:
```bash
docker-compose up --scale lock-manager=5
```

## Configuration

### Lock Manager
- ELECTION_TIMEOUT_MIN: Minimum election timeout (ms)
- ELECTION_TIMEOUT_MAX: Maximum election timeout (ms)
- HEARTBEAT_INTERVAL: Leader heartbeat interval (ms)

### Queue System
- QUEUE_REPLICAS: Number of message replicas
- MESSAGE_RETENTION_PERIOD: How long to keep messages (seconds)

### Cache System
- CACHE_CAPACITY: Number of entries to keep in cache
- CACHE_PROTOCOL: Cache coherence protocol (MESI/MOSI/MOESI)

## Troubleshooting

### Common Issues

1. Node Connection Issues
   - Check network connectivity
   - Verify port configurations
   - Ensure Redis is running

2. Leader Election Problems
   - Check election timeouts
   - Verify node communication
   - Check for network partitions

3. Message Loss
   - Verify Redis connection
   - Check message persistence
   - Validate queue configuration

4. Cache Inconsistency
   - Check coherence protocol logs
   - Verify invalidation messages
   - Monitor cache states

### Monitoring

1. Check node status:
```bash
docker-compose ps
```

2. View logs:
```bash
docker-compose logs -f [service_name]
```

3. Monitor Redis:
```bash
redis-cli monitor
```

### Recovery Procedures

1. Node Failure
   - Restart failed node
   - Check logs for errors
   - Verify state recovery

2. Network Partition
   - Check network connectivity
   - Verify leader election
   - Monitor log replication

3. Data Inconsistency
   - Force cache invalidation
   - Verify message queues
   - Check lock states

## Performance Optimization

1. Tune Parameters:
   - Adjust election timeouts
   - Configure message batch sizes
   - Set appropriate cache sizes

2. Network Optimization:
   - Use appropriate network mode in Docker
   - Configure proper DNS resolution
   - Monitor network latency

3. Resource Allocation:
   - Adjust container resources
   - Monitor CPU and memory usage
   - Scale nodes as needed