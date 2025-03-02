import numpy as np
from typing import Optional, Union, Tuple
import logging

# Import optional libraries with fallbacks
try:
    import umap
    UMAP_AVAILABLE = True
except ImportError:
    UMAP_AVAILABLE = False
    
try:
    from sklearn.manifold import TSNE
    TSNE_AVAILABLE = True
except ImportError:
    TSNE_AVAILABLE = False
    
from sklearn.decomposition import PCA

logger = logging.getLogger(__name__)

class DimensionalityReducer:
    """
    Advanced dimensionality reduction techniques for vector embeddings
    to optimize search performance and efficiency.
    """
    
    def __init__(self, 
                method: str = "auto",
                target_dim: int = 128,
                random_state: int = 42):
        """
        Initialize dimensionality reducer.
        
        Args:
            method: Reduction method - "pca", "umap", "tsne", or "auto"
            target_dim: Target dimensionality
            random_state: Random seed for reproducibility
        """
        self.method = method
        self.target_dim = target_dim
        self.random_state = random_state
        self.model = None
        self.is_fitted = False
        
        # Validate method and dependencies
        if method == "umap" and not UMAP_AVAILABLE:
            logger.warning("UMAP not available, falling back to PCA. Install umap-learn package.")
            self.method = "pca"
            
        if method == "tsne" and not TSNE_AVAILABLE:
            logger.warning("t-SNE not available, falling back to PCA. Install scikit-learn package.")
            self.method = "pca"
    
    def fit(self, embeddings: np.ndarray, min_samples: int = 50) -> bool:
        """
        Fit the dimensionality reduction model.
        
        Args:
            embeddings: Array of embeddings (n_samples, n_dimensions)
            min_samples: Minimum number of samples required to fit
            
        Returns:
            bool: Whether fitting was successful
        """
        if len(embeddings) < min_samples:
            logger.info(f"Not enough samples ({len(embeddings)}) to fit dimensionality reducer")
            return False
        
        # Choose best method based on data size if 'auto' specified
        method = self._select_method(embeddings) if self.method == "auto" else self.method
        
        target_dim = min(self.target_dim, embeddings.shape[1] - 1)  # Can't exceed original dimensions - 1
        
        try:
            if method == "pca":
                self.model = PCA(n_components=target_dim, random_state=self.random_state)
                
            elif method == "umap":
                # UMAP parameters tuned for semantic similarity preservation
                self.model = umap.UMAP(
                    n_components=target_dim,
                    n_neighbors=min(30, len(embeddings) // 2),  # Adaptive neighbor count
                    min_dist=0.1,
                    metric='cosine',
                    random_state=self.random_state
                )
                
            elif method == "tsne":
                # t-SNE with parameters for embedding spaces
                self.model = TSNE(
                    n_components=target_dim,
                    perplexity=min(30, len(embeddings) // 2),
                    learning_rate='auto',
                    metric='cosine',
                    random_state=self.random_state,
                    n_jobs=-1  # Use all available cores
                )
            
            # Fit the model
            self.model.fit(embeddings)
            self.is_fitted = True
            logger.info(f"Dimensionality reducer fitted using {method}: {embeddings.shape[1]}D → {target_dim}D")
            return True
            
        except Exception as e:
            logger.error(f"Error fitting dimensionality reducer: {str(e)}")
            self.is_fitted = False
            return False
    
    def transform(self, embeddings: np.ndarray) -> np.ndarray:
        """
        Transform embeddings to lower dimensionality.
        
        Args:
            embeddings: Array of embeddings to transform
            
        Returns:
            Transformed lower-dimensional embeddings
        """
        if not self.is_fitted:
            logger.warning("Dimensionality reducer not fitted, returning original embeddings")
            return embeddings
        
        try:
            return self.model.transform(embeddings)
        except Exception as e:
            logger.error(f"Error transforming embeddings: {str(e)}")
            return embeddings
    
    def fit_transform(self, embeddings: np.ndarray, min_samples: int = 50) -> np.ndarray:
        """
        Fit the model and transform embeddings in one step.
        
        Args:
            embeddings: Array of embeddings
            min_samples: Minimum number of samples required to fit
            
        Returns:
            Transformed embeddings or original if fitting fails
        """
        if len(embeddings) < min_samples:
            return embeddings
            
        if self.fit(embeddings, min_samples):
            return self.transform(embeddings)
        return embeddings
    
    def _select_method(self, embeddings: np.ndarray) -> str:
        """
        Automatically select best reduction method based on data.
        
        Args:
            embeddings: Input embedding array
            
        Returns:
            Selected method name
        """
        n_samples = len(embeddings)
        
        # For very small datasets, PCA is best
        if n_samples < 200:
            return "pca"
            
        # For medium datasets with UMAP available
        if n_samples < 10000 and UMAP_AVAILABLE:
            return "umap"
            
        # For larger datasets, PCA is more efficient
        return "pca"
    
    def get_explained_variance(self) -> Optional[float]:
        """Get explained variance ratio for PCA model"""
        if not self.is_fitted or not isinstance(self.model, PCA):
            return None
            
        return float(sum(self.model.explained_variance_ratio_))
