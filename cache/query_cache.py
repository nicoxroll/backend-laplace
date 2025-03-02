import time
import hashlib
import json
from typing import Dict, List, Any, Optional, Tuple, Union
import numpy as np

class QueryCache:
    """
    Implements caching for search queries to improve response time for frequently
    used searches.
    """
    
    def __init__(self, max_size: int = 1000, ttl: int = 3600):
        """
        Initialize the query cache.
        
        Args:
            max_size: Maximum number of queries to cache
            ttl: Time-to-live for cache entries in seconds (default 1 hour)
        """
        self.max_size = max_size
        self.ttl = ttl
        self.vector_cache: Dict[str, Tuple[float, np.ndarray]] = {}  # {query_hash: (timestamp, embedding)}
        self.results_cache: Dict[str, Tuple[float, List[Dict[str, Any]]]] = {}  # {cache_key: (timestamp, results)}
        self.usage_stats: Dict[str, int] = {}  # {cache_key: access_count}
    
    def get_vector(self, query: str) -> Optional[np.ndarray]:
        """Retrieve cached vector embedding for a query"""
        query_hash = self._hash_query(query)
        if query_hash in self.vector_cache:
            timestamp, vector = self.vector_cache[query_hash]
            if time.time() - timestamp <= self.ttl:
                self.usage_stats[query_hash] = self.usage_stats.get(query_hash, 0) + 1
                return vector
            else:
                # Expired entry
                del self.vector_cache[query_hash]
        return None
    
    def cache_vector(self, query: str, vector: np.ndarray) -> None:
        """Store vector embedding for a query"""
        query_hash = self._hash_query(query)
        self._ensure_cache_size(self.vector_cache)
        self.vector_cache[query_hash] = (time.time(), vector)
        
    def get_results(self, query: str, params: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
        """Retrieve cached search results for a query with specific parameters"""
        cache_key = self._create_cache_key(query, params)
        if cache_key in self.results_cache:
            timestamp, results = self.results_cache[cache_key]
            if time.time() - timestamp <= self.ttl:
                self.usage_stats[cache_key] = self.usage_stats.get(cache_key, 0) + 1
                return results
            else:
                # Expired entry
                del self.results_cache[cache_key]
        return None
    
    def cache_results(self, query: str, params: Dict[str, Any], results: List[Dict[str, Any]]) -> None:
        """Store search results for a query with specific parameters"""
        cache_key = self._create_cache_key(query, params)
        self._ensure_cache_size(self.results_cache)
        self.results_cache[cache_key] = (time.time(), results)
    
    def _hash_query(self, query: str) -> str:
        """Create a hash for a query string"""
        return hashlib.md5(query.lower().strip().encode()).hexdigest()
    
    def _create_cache_key(self, query: str, params: Dict[str, Any]) -> str:
        """Create a unique cache key based on query and search parameters"""
        # Sort params to ensure consistent key generation
        sorted_params = {k: params[k] for k in sorted(params.keys())}
        param_str = json.dumps(sorted_params, sort_keys=True)
        key_material = f"{query.lower().strip()}|{param_str}"
        return hashlib.md5(key_material.encode()).hexdigest()
    
    def _ensure_cache_size(self, cache_dict: Dict) -> None:
        """Ensure the cache doesn't exceed maximum size by removing least used entries"""
        if len(cache_dict) >= self.max_size:
            # Remove least recently accessed items
            to_remove = len(cache_dict) - self.max_size + 1  # +1 to make room for new entry
            
            # Sort keys by usage count (ascending) and then by age (oldest first)
            keys_to_remove = sorted(
                cache_dict.keys(),
                key=lambda k: (self.usage_stats.get(k, 0), -cache_dict[k][0])
            )[:to_remove]
            
            for key in keys_to_remove:
                del cache_dict[key]
                if key in self.usage_stats:
                    del self.usage_stats[key]
    
    def clear_expired(self) -> int:
        """Clear expired entries and return number of entries removed"""
        current_time = time.time()
        expired_count = 0
        
        # Clear expired vectors
        expired_vectors = [k for k, (ts, _) in self.vector_cache.items() 
                          if current_time - ts > self.ttl]
        for k in expired_vectors:
            del self.vector_cache[k]
            if k in self.usage_stats:
                del self.usage_stats[k]
        expired_count += len(expired_vectors)
        
        # Clear expired results
        expired_results = [k for k, (ts, _) in self.results_cache.items() 
                           if current_time - ts > self.ttl]
        for k in expired_results:
            del self.results_cache[k]
            if k in self.usage_stats:
                del self.usage_stats[k]
        expired_count += len(expired_results)
        
        return expired_count
