import numpy as np
from sklearn.cluster import KMeans
from typing import List, Tuple

class VectorQuantizer:
    """
    Vector Quantization for efficient embedding storage and retrieval.
    Implements both scalar quantization and product quantization methods.
    """
    
    def __init__(self, method: str = "product", n_subspaces: int = 8, bits: int = 8):
        """
        Initialize the vector quantizer.
        
        Args:
            method: "scalar" or "product" quantization
            n_subspaces: Number of subspaces for product quantization
            bits: Bit precision for quantization (8 = 256 centroids per subspace)
        """
        self.method = method
        self.n_subspaces = n_subspaces
        self.n_centroids = 2**bits
        self.codebooks = None
        self.min_val = None
        self.max_val = None
        self.subvector_size = None
        
    def fit(self, vectors: np.ndarray) -> None:
        """Train the quantizer on a set of vectors"""
        if self.method == "scalar":
            self.min_val = np.min(vectors, axis=0)
            self.max_val = np.max(vectors, axis=0)
        else:  # Product quantization
            dim = vectors.shape[1]
            self.subvector_size = dim // self.n_subspaces
            self.codebooks = []
            
            for i in range(self.n_subspaces):
                start_dim = i * self.subvector_size
                end_dim = start_dim + self.subvector_size
                subvectors = vectors[:, start_dim:end_dim]
                
                kmeans = KMeans(n_clusters=min(self.n_centroids, len(vectors)), 
                               random_state=42, n_init="auto")
                kmeans.fit(subvectors)
                self.codebooks.append(kmeans.cluster_centers_)
    
    def encode(self, vectors: np.ndarray) -> np.ndarray:
        """Encode vectors to their quantized representation"""
        if self.method == "scalar":
            # Simple linear scalar quantization
            normalized = (vectors - self.min_val) / (self.max_val - self.min_val)
            quantized = np.round(normalized * (self.n_centroids - 1)).astype(np.uint8)
            return quantized
        else:
            # Product quantization
            codes = np.zeros((vectors.shape[0], self.n_subspaces), dtype=np.uint8)
            
            for i in range(self.n_subspaces):
                start_dim = i * self.subvector_size
                end_dim = start_dim + self.subvector_size
                subvectors = vectors[:, start_dim:end_dim]
                
                for j, subvector in enumerate(subvectors):
                    distances = np.linalg.norm(self.codebooks[i] - subvector, axis=1)
                    codes[j, i] = np.argmin(distances)
                    
            return codes
    
    def decode(self, codes: np.ndarray) -> np.ndarray:
        """Decode quantized representations back to vector approximations"""
        if self.method == "scalar":
            # Reverse the scalar quantization
            normalized = codes / (self.n_centroids - 1)
            return normalized * (self.max_val - self.min_val) + self.min_val
        else:
            # Reconstruct from product quantization codes
            decoded = np.zeros((codes.shape[0], self.subvector_size * self.n_subspaces))
            
            for i in range(self.n_subspaces):
                start_dim = i * self.subvector_size
                end_dim = start_dim + self.subvector_size
                
                for j, code in enumerate(codes[:, i]):
                    decoded[j, start_dim:end_dim] = self.codebooks[i][code]
                    
            return decoded

    def memory_savings(self, original_vectors: np.ndarray) -> Tuple[float, float]:
        """Calculate memory savings from quantization"""
        original_bytes = original_vectors.nbytes
        if self.method == "scalar":
            quantized_bytes = len(original_vectors) * original_vectors.shape[1]  # uint8
        else:
            quantized_bytes = len(original_vectors) * self.n_subspaces  # uint8
            # Add codebook storage
            for codebook in self.codebooks:
                quantized_bytes += codebook.nbytes
        
        ratio = original_bytes / quantized_bytes
        savings_pct = (1 - quantized_bytes / original_bytes) * 100
        
        return ratio, savings_pct
