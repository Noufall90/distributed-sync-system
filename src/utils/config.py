import os
from typing import Any, Dict
from dotenv import load_dotenv

class Config:
    _instance = None
    _config: Dict[str, Any] = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Config, cls).__new__(cls)
            cls._instance._load_config()
        return cls._instance
        
    def _load_config(self):
        """Load configuration from environment variables"""
        load_dotenv()
        
        # Node configuration
        self._config["NODE_TYPE"] = os.getenv("NODE_TYPE", "base")
        self._config["NODE_ID"] = os.getenv("NODE_ID", "node1")
        self._config["HOST"] = os.getenv("HOST", "0.0.0.0")
        self._config["PORT"] = int(os.getenv("PORT", "8000"))
        
        # Redis configuration
        self._config["REDIS_HOST"] = os.getenv("REDIS_HOST", "localhost")
        self._config["REDIS_PORT"] = int(os.getenv("REDIS_PORT", "6379"))
        
        # Consensus configuration
        self._config["ELECTION_TIMEOUT_MIN"] = int(os.getenv("ELECTION_TIMEOUT_MIN", "150"))
        self._config["ELECTION_TIMEOUT_MAX"] = int(os.getenv("ELECTION_TIMEOUT_MAX", "300"))
        self._config["HEARTBEAT_INTERVAL"] = int(os.getenv("HEARTBEAT_INTERVAL", "50"))
        
        # Cache configuration
        self._config["CACHE_CAPACITY"] = int(os.getenv("CACHE_CAPACITY", "1000"))
        self._config["CACHE_PROTOCOL"] = os.getenv("CACHE_PROTOCOL", "MESI")
        
        # Queue configuration
        self._config["QUEUE_REPLICAS"] = int(os.getenv("QUEUE_REPLICAS", "3"))
        self._config["MESSAGE_RETENTION_PERIOD"] = int(os.getenv("MESSAGE_RETENTION_PERIOD", "3600"))
        
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value"""
        return self._config.get(key, default)
        
    def set(self, key: str, value: Any):
        """Set configuration value"""
        self._config[key] = value
        
    @property
    def all(self) -> Dict[str, Any]:
        """Get all configuration values"""
        return self._config.copy()