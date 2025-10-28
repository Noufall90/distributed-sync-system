# 🧩 Sistem Sinkronisasi Terdistribusi

Proyek ini mengimplementasikan **sistem sinkronisasi terdistribusi** yang mensimulasikan bagaimana beberapa node dalam sistem terdistribusi dapat **berkomunikasi dan menjaga konsistensi data** melalui beberapa komponen inti:  
- **Distributed Lock Manager (Raft Consensus)**  
- **Distributed Queue System (Consistent Hashing)**  
- **Distributed Cache Coherence (MESI Protocol)**  

Sistem ini dijalankan dalam lingkungan **Docker** dengan dukungan **Redis** sebagai penyimpanan status global.  
Tujuannya adalah untuk mensimulasikan skenario real-world dari sistem terdistribusi dengan fokus pada konsistensi, fault tolerance, dan performa.

## ⚙️ Teknologi yang Digunakan

| Komponen | Teknologi |
|-----------|------------|
| Bahasa | Python 3.11+ |
| Komunikasi | `asyncio`, `aiohttp` |
| Penyimpanan status | Redis 6 |
| Orkestrasi | Docker & Docker Compose |
| Load Testing | Locust / Python Benchmark Script |
| Monitoring | Metrics internal (latency, throughput) |

### Install Dependency
```bash
pip install -e .
```

### Jalankan Redis

```bash
docker run -d -p 6379:6379 redis:6-alpine
```

### Build Docker Images
```bash
cd docker
docker-compose up --build
```

### Jalankan Sistem sudah build
```bash
cd docker
docker-compose up
```

### Setelah semua container berjalan, pastikan sistem aktif:
```bash
docker ps
```

## Video Youtube


```
https://youtu.be/_fCYRU0EJ78
```