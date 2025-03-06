import redis
import json
import os
from typing import Dict, Any, Optional
from datetime import datetime
from dotenv import load_dotenv
import logging

load_dotenv()

logger = logging.getLogger(__name__)

# Usar la variable de entorno correctamente
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")

# Inicializar cliente Redis con la URL correcta
redis_client = redis.from_url(REDIS_URL)

# Key prefixes
PROCESSING_STATUS_PREFIX = "knowledge:processing:"
CACHE_PREFIX = "knowledge:cache:"

# Default TTLs (in seconds)
PROCESSING_STATUS_TTL = 60 * 60 * 24  # 24 hours
CACHE_TTL = 60 * 60 * 24 * 7  # 7 days

def update_processing_status(job_id: str, status_data: Dict[str, Any]) -> bool:
    """
    Update processing status in Redis
    
    Args:
        job_id: ID of the processing job
        status_data: Status information to store
        
    Returns:
        bool: True if successful
    """
    try:
        # Convert datetime objects to ISO format strings
        for key, value in status_data.items():
            if isinstance(value, datetime):
                status_data[key] = value.isoformat()
        
        key = f"{PROCESSING_STATUS_PREFIX}{job_id}"
        redis_client.setex(key, PROCESSING_STATUS_TTL, json.dumps(status_data))
        return True
    except Exception as e:
        logger.error(f"Error updating processing status: {str(e)}")
        return False

def get_processing_status(job_id: str) -> Optional[Dict[str, Any]]:
    """
    Get processing status from Redis
    
    Args:
        job_id: ID of the processing job
        
    Returns:
        Dict or None: Status data if exists
    """
    try:
        key = f"{PROCESSING_STATUS_PREFIX}{job_id}"
        data = redis_client.get(key)
        
        if data:
            status_data = json.loads(data)
            
            # Convert ISO datetime strings back to datetime objects
            for field in ["created_at", "completed_at"]:
                if field in status_data and status_data[field]:
                    try:
                        status_data[field] = datetime.fromisoformat(status_data[field])
                    except (ValueError, TypeError):
                        pass
                        
            return status_data
        
        return None
    except Exception as e:
        logger.error(f"Error getting processing status: {str(e)}")
        return None

def cache_chunks(user_id: str, file_id: str, chunks: list) -> bool:
    """
    Cache processed chunks for faster retrieval
    
    Args:
        user_id: ID of the user
        file_id: ID of the file
        chunks: Processed chunks to cache
        
    Returns:
        bool: True if successful
    """
    try:
        key = f"{CACHE_PREFIX}{user_id}:{file_id}"
        redis_client.set(key, json.dumps(chunks))
        redis_client.expire(key, CACHE_TTL)
        return True
    except Exception as e:
        logger.error(f"Error caching chunks: {str(e)}")
        return False

def get_cached_chunks(user_id: str, file_id: str) -> Optional[list]:
    """
    Retrieve cached chunks
    
    Args:
        user_id: ID of the user
        file_id: ID of the file
        
    Returns:
        list or None: Cached chunks if available
    """
    try:
        key = f"{CACHE_PREFIX}{user_id}:{file_id}"
        cached_data = redis_client.get(key)
        
        if cached_data:
            return json.loads(cached_data)
        return None
    except Exception as e:
        logger.error(f"Error retrieving cached chunks: {str(e)}")
        return None

def list_user_jobs(user_id: str, limit: int = 20) -> list:
    """
    List all processing jobs for a user
    """
    # Scan Redis for keys with the prefix
    cursor = 0
    jobs = []
    
    while True:
        cursor, keys = redis_client.scan(cursor, f"{PROCESSING_STATUS_PREFIX}*", limit)
        
        for key in keys:
            data = redis_client.get(key)
            if data:
                job_data = json.loads(data)
                if job_data.get("user_id") == user_id:
                    job_id = key.replace(PROCESSING_STATUS_PREFIX, "")
                    jobs.append({
                        "job_id": job_id,
                        "filename": job_data.get("filename", ""),
                        "status": job_data.get("status", "unknown"),
                        "progress": job_data.get("progress", 0),
                        "created_at": job_data.get("created_at"),
                        "completed_at": job_data.get("completed_at")
                    })
                    
        if cursor == 0 or len(jobs) >= limit:
            break
            
    # Sort by created_at (newest first)
    return sorted(jobs, key=lambda x: x.get("created_at", ""), reverse=True)
