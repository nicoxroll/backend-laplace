from typing import List, Dict, Any
import numpy as np
import logging
from sklearn.decomposition import PCA
from ..db.embeddings_client import generate_embeddings

logger = logging.getLogger(__name__)

class VectorOptimizer:
    """
    Optimizes vectors through batch processing and compression techniques
    """
    def __init__(self, batch_size: int = 16, compression_dimensions: int = None):
        self.batch_size = batch_size
        self.compression_dimensions = compression_dimensions
        self.pca = None
    
    def batch_process(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Process chunks in batches to generate embeddings more efficiently
        """
        processed_chunks = []
        
        # Process in batches
        for i in range(0, len(chunks), self.batch_size):
            batch = chunks[i:i + self.batch_size]
            batch_texts = [chunk["text"] for chunk in batch]
            
            # Generate embeddings for the batch
            embeddings = generate_embeddings(batch_texts)
            
            # Add embeddings to chunks
            for j, embedding in enumerate(embeddings):
                batch[j]["embedding"] = embedding
                processed_chunks.append(batch[j])
        
        return processed_chunks
    
    def compress_vectors(self, chunks_with_embeddings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Compress vectors to reduce dimensionality while preserving information
        """
        if not self.compression_dimensions:
            # No compression needed
            return chunks_with_embeddings
        
        # Extract embeddings
        embeddings = np.array([chunk["embedding"] for chunk in chunks_with_embeddings])
        
        # Initialize PCA if not already done
        if self.pca is None:
            self.pca = PCA(n_components=self.compression_dimensions)
            self.pca.fit(embeddings)
        
        # Compress embeddings
        compressed_embeddings = self.pca.transform(embeddings)
        
        # Replace original embeddings with compressed ones
        for i, chunk in enumerate(chunks_with_embeddings):
            chunk["embedding"] = compressed_embeddings[i].tolist()
            chunk["compressed"] = True
            chunk["original_dim"] = len(embeddings[i])
            chunk["compressed_dim"] = self.compression_dimensions
        
        return chunks_with_embeddings

def optimize_vectors(chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Optimize vectors for efficient storage and retrieval:
    1. Normalize vectors
    2. Optionally apply dimensionality reduction if needed
    3. Prepare for batch processing
    """
    if not chunks:
        return []
    
    # Extract embeddings for processing
    embeddings = [np.array(chunk["embedding"]) for chunk in chunks]
    
    # Check if we have enough vectors for meaningful dimensionality reduction
    if len(embeddings) > 50:
        # Apply dimensionality reduction if we have many vectors
        original_dim = len(embeddings[0])
        target_dim = min(original_dim, 384)  # Cap at 384 dimensions
        
        if original_dim > target_dim:
            # Apply PCA for dimensionality reduction
            pca = PCA(n_components=target_dim)
            reduced_embeddings = pca.fit_transform(embeddings)
            
            # Update chunks with reduced embeddings
            for i, chunk in enumerate(chunks):
                chunk["embedding"] = reduced_embeddings[i].tolist()
                chunk["embedding_type"] = "reduced_pca"
    
    # Normalize all vectors for cosine similarity
    for i, chunk in enumerate(chunks):
        embedding = np.array(chunk["embedding"])
        norm = np.linalg.norm(embedding)
        if norm > 0:
            normalized = embedding / norm
            chunk["embedding"] = normalized.tolist()
            
    # Add batch identifiers for efficient processing
    batch_size = 100
    for i, chunk in enumerate(chunks):
        chunk["batch_id"] = i // batch_size
    
    return chunks
