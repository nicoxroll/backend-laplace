from typing import List
import numpy as np
import os
from dotenv import load_dotenv
import logging
import requests

load_dotenv()

logger = logging.getLogger(__name__)

# Configure embedding service - CORREGIDO para usar bert-service en la red Docker
EMBEDDING_API_URL = os.getenv("EMBEDDING_API_URL", "http://bert-service:5000")
EMBEDDING_DIM = int(os.getenv("EMBEDDING_DIM", "384"))  # Default to BERT dimension

# Initialize model once at module level for efficiency
_model = None

def _get_model():
    """Get or initialize the embedding model singleton"""
    global _model
    if _model is None:
        try:
            from sentence_transformers import SentenceTransformer
            model_name = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
            logger.info(f"Loading embedding model: {model_name}")
            _model = SentenceTransformer(model_name)
            # Verify embedding dimension matches configured value
            test_embedding = _model.encode(["test"])
            actual_dim = len(test_embedding[0])
            if actual_dim != EMBEDDING_DIM:
                logger.warning(f"Model dimension ({actual_dim}) doesn't match configured EMBEDDING_DIM ({EMBEDDING_DIM})")
        except ImportError:
            logger.error("sentence_transformers not installed. Install with: pip install sentence_transformers")
            raise
        except Exception as e:
            logger.error(f"Error initializing model: {str(e)}")
            raise
    return _model

def generate_embeddings(texts: List[str]) -> List[List[float]]:
    """
    Generate embeddings for a list of texts
    
    Args:
        texts: List of text strings to embed
        
    Returns:
        List of embedding vectors
    """
    try:
        # Validate input
        if not texts:
            logger.warning("Empty text list provided for embedding")
            return []
            
        # Filter out empty strings which can cause issues with some models
        filtered_texts = [text for text in texts if text.strip()]
        if len(filtered_texts) != len(texts):
            logger.warning(f"Filtered out {len(texts) - len(filtered_texts)} empty strings")
            
        if not filtered_texts:
            logger.warning("No valid texts to embed after filtering")
            return [[] for _ in texts]  # Return empty vectors matching original count
            
        # Check if we're using local or remote embedding service
        if os.getenv("USE_LOCAL_EMBEDDINGS", "false").lower() == "true":
            embeddings = generate_embeddings_local(filtered_texts)
        else:
            embeddings = generate_embeddings_remote(filtered_texts)
            
        # If we filtered texts, need to align results with original input
        if len(filtered_texts) != len(texts):
            # Create a mapping to put embeddings back in original positions
            result = []
            filtered_idx = 0
            for text in texts:
                if text.strip():
                    result.append(embeddings[filtered_idx])
                    filtered_idx += 1
                else:
                    result.append([0.0] * EMBEDDING_DIM)  # Add zero vector for empty texts
            return result
        return embeddings
    except Exception as e:
        logger.error(f"Error generating embeddings: {str(e)}")
        # Don't silently use random vectors in production
        if os.getenv("ENVIRONMENT", "development").lower() == "production":
            raise
        # Fall back to random embeddings in case of failure (for testing only)
        logger.warning("Falling back to random embeddings - THIS SHOULD ONLY HAPPEN IN DEVELOPMENT")
        return [np.random.rand(EMBEDDING_DIM).tolist() for _ in texts]

def generate_embeddings_local(texts: List[str]) -> List[List[float]]:
    """
    Generate embeddings using local BERT model
    
    Args:
        texts: List of text strings to embed
        
    Returns:
        List of embedding vectors
    """
    try:
        # Use singleton model instead of loading each time
        model = _get_model()
        
        # Process in batches if the list is large
        batch_size = int(os.getenv("EMBEDDING_BATCH_SIZE", "32"))
        if len(texts) > batch_size:
            logger.info(f"Processing {len(texts)} texts in batches of {batch_size}")
            all_embeddings = []
            for i in range(0, len(texts), batch_size):
                batch_texts = texts[i:i+batch_size]
                batch_embeddings = model.encode(batch_texts)
                all_embeddings.extend(batch_embeddings.tolist())
            return all_embeddings
        
        # Generate embeddings
        embeddings = model.encode(texts)
        
        # Ensure we have the right format regardless of what the model returns
        if not isinstance(embeddings, np.ndarray):
            logger.warning(f"Model returned {type(embeddings)} instead of numpy array")
            # Try to convert to numpy array if possible
            embeddings = np.array(embeddings)
            
        return embeddings.tolist()
    except Exception as e:
        logger.error(f"Error generating local embeddings: {str(e)}")
        raise

def generate_embeddings_remote(texts: List[str]) -> List[List[float]]:
    """
    Generate embeddings using remote API service
    
    Args:
        texts: List of text strings to embed
        
    Returns:
        List of embedding vectors
    """
    try:
        # Process in batches for remote API too
        batch_size = int(os.getenv("API_EMBEDDING_BATCH_SIZE", "100"))
        timeout = int(os.getenv("API_EMBEDDING_TIMEOUT", "60"))  # Increase default timeout
        
        if len(texts) > batch_size:
            logger.info(f"Processing {len(texts)} texts in API batches of {batch_size}")
            all_embeddings = []
            for i in range(0, len(texts), batch_size):
                batch_texts = texts[i:i+batch_size]
                logger.debug(f"Enviando lote {i//batch_size + 1} a API: {EMBEDDING_API_URL}")
                response = requests.post(
                    EMBEDDING_API_URL,
                    json={"texts": batch_texts},
                    headers={
                        "Content-Type": "application/json",
                        "User-Agent": "backend-laplace-embeddings-client/1.0"
                    },
                    timeout=timeout
                )
                response.raise_for_status()
                result = response.json()
                if "embeddings" not in result:
                    raise ValueError(f"Invalid API response format: missing 'embeddings' key")
                all_embeddings.extend(result["embeddings"])
            return all_embeddings
            
        # Make API request to embedding service
        logger.debug(f"Enviando petición a API de embeddings: {EMBEDDING_API_URL}")
        response = requests.post(
            EMBEDDING_API_URL,
            json={"texts": texts},
            headers={
                "Content-Type": "application/json", 
                "User-Agent": "backend-laplace-embeddings-client/1.0"
            },
            timeout=timeout
        )
        
        # Check for successful response
        response.raise_for_status()
        result = response.json()
        
        # Validate response format
        if "embeddings" not in result:
            error_msg = f"Invalid response format from embedding API: missing 'embeddings' key"
            logger.error(f"{error_msg}. Response: {result}")
            raise ValueError(error_msg)
            
        embeddings = result["embeddings"]
        
        # Additional validation of embeddings structure
        if not isinstance(embeddings, list):
            raise ValueError(f"API returned non-list embeddings type: {type(embeddings)}")
            
        if embeddings and not isinstance(embeddings[0], list):
            raise ValueError(f"API returned incorrect embedding format: {type(embeddings[0])}")
            
        # Check dimensions if we got results
        if embeddings and len(texts) != len(embeddings):
            logger.warning(f"API returned {len(embeddings)} embeddings for {len(texts)} texts")
            
        return embeddings
    except requests.RequestException as e:
        logger.error(f"Error calling embedding API: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Error processing embedding API response: {str(e)}")
        raise