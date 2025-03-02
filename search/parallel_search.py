import asyncio
import numpy as np
from typing import List, Dict, Any, Callable, Optional, Tuple, Union
import time
import logging

logger = logging.getLogger(__name__)

class ParallelSearchExecutor:
    """
    Implements parallel search across multiple shards or indices
    for improved search performance on large collections.
    """
    
    def __init__(self, max_workers: int = 8):
        """
        Initialize the parallel search executor.
        
        Args:
            max_workers: Maximum number of concurrent search operations
        """
        self.max_workers = max_workers
    
    async def search_shards(self, 
                           query_vector: np.ndarray,
                           shards: List[Any],
                           search_func: Callable,
                           limit: int = 20,
                           search_params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Execute search in parallel across multiple shards.
        
        Args:
            query_vector: The query embedding
            shards: List of shard objects to search
            search_func: Async function to execute per shard with signature:
                         (shard, query_vector, limit, params) -> results
            limit: Number of results to return per shard
            search_params: Additional search parameters
            
        Returns:
            List of merged and ranked search results
        """
        if search_params is None:
            search_params = {}
            
        # Create search tasks - enforce concurrency limit
        semaphore = asyncio.Semaphore(self.max_workers)
        
        async def bounded_search(shard, shard_id):
            async with semaphore:
                start_time = time.time()
                try:
                    # Increase per-shard limit to ensure we have enough candidates after merging
                    shard_limit = min(limit * 2, limit + 20)
                    results = await search_func(shard, query_vector, shard_limit, search_params)
                    duration = time.time() - start_time
                    logger.debug(f"Shard {shard_id} search completed in {duration:.3f}s")
                    return results
                except Exception as e:
                    logger.error(f"Error searching shard {shard_id}: {str(e)}")
                    return []
        
        # Execute all searches in parallel
        tasks = [bounded_search(shard, i) for i, shard in enumerate(shards)]
        all_results = await asyncio.gather(*tasks)
        
        # Merge and rank results
        merged_results = self._merge_results(all_results, limit)
        return merged_results
    
    def _merge_results(self, 
                      shard_results: List[List[Dict[str, Any]]], 
                      limit: int) -> List[Dict[str, Any]]:
        """
        Merge results from multiple shards, handling duplicates and re-ranking.
        
        Args:
            shard_results: List of result lists from each shard
            limit: Maximum number of results to return after merging
            
        Returns:
            List of merged and ranked results
        """
        # Flatten results from all shards
        all_results = []
        seen_ids = set()
        
        for results in shard_results:
            for result in results:
                # Use a consistent ID field from the result
                result_id = result.get("id") or result.get("_id")
                
                if result_id and result_id not in seen_ids:
                    seen_ids.add(result_id)
                    all_results.append(result)
        
        # Sort results by score, descending
        sorted_results = sorted(
            all_results, 
            key=lambda x: x.get("score", 0.0) if x.get("score") is not None else 0.0,
            reverse=True
        )
        
        # Return top results
        return sorted_results[:limit]
    
    async def search_with_fallback(self,
                                  primary_search: Callable,
                                  fallback_search: Callable,
                                  query: str,
                                  params: Dict[str, Any],
                                  timeout: float = 2.0) -> Tuple[List[Dict[str, Any]], str]:
        """
        Execute search with automatic fallback if primary search fails or times out.
        
        Args:
            primary_search: Primary async search function
            fallback_search: Fallback async search function
            query: Search query
            params: Search parameters
            timeout: Timeout in seconds for primary search
            
        Returns:
            Tuple of (search results, source)
        """
        try:
            # Try primary search with timeout
            primary_task = asyncio.create_task(primary_search(query, params))
            results = await asyncio.wait_for(primary_task, timeout=timeout)
            return results, "primary"
        except asyncio.TimeoutError:
            logger.warning(f"Primary search timed out after {timeout}s, using fallback")
            # Cancel primary search task
            primary_task.cancel()
            # Use fallback search
            results = await fallback_search(query, params)
            return results, "fallback_timeout"
        except Exception as e:
            logger.error(f"Primary search failed: {str(e)}, using fallback")
            # Use fallback search
            results = await fallback_search(query, params)
            return results, "fallback_error"
