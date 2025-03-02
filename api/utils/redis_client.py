import redis
from config import settings
import json
import logging
from typing import Any, Dict, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RedisClient:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(RedisClient, cls).__new__(cls)
            try:
                cls._instance.client = redis.from_url(settings.REDIS_URL)
                logger.info("Connected to Redis at %s", settings.REDIS_URL)
            except Exception as e:
                logger.error(f"Failed to connect to Redis: {e}")
                cls._instance.client = None
        return cls._instance
    
    def get_client(self):
        return self.client
    
    def set(self, key: str, value: Any, expiry: Optional[int] = None):
        """Set a key with value in Redis with optional expiry in seconds"""
        if not self.client:
            logger.error("No Redis client available")
            return False
        
        try:
            if isinstance(value, (dict, list)):
                value = json.dumps(value)
            
            if expiry:
                self.client.setex(key, expiry, value)
            else:
                self.client.set(key, value)
            return True
        except Exception as e:
            logger.error(f"Failed to set key {key}: {e}")
            return False
    
    def get(self, key: str, as_json: bool = False):
        """Get a value from Redis"""
        if not self.client:
            logger.error("No Redis client available")
            return None
        
        try:
            value = self.client.get(key)
            if value and as_json:
                return json.loads(value)
            return value
        except Exception as e:
            logger.error(f"Failed to get key {key}: {e}")
            return None
    
    def delete(self, key: str):
        """Delete a key from Redis"""
        if not self.client:
            logger.error("No Redis client available")
            return False
        
        try:
            return self.client.delete(key)
        except Exception as e:
            logger.error(f"Failed to delete key {key}: {e}")
            return False

# Función de ayuda para obtener el cliente
def get_redis_client():
    return RedisClient().get_client()
