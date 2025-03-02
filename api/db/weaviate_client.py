import weaviate
import os
import uuid
from typing import List, Dict, Any
import numpy as np
from datetime import datetime
from dotenv import load_dotenv
from api.db.embeddings_client import generate_embeddings
from api.db.query_expansion import expand_query  # Import expand_query function

load_dotenv()

logger = logging.getLogger(__name__)

# Get Weaviate credentials from environment variables
WEAVIATE_URL = os.getenv("WEAVIATE_URL", "http://localhost:8080")
WEAVIATE_API_KEY = os.getenv("WEAVIATE_API_KEY", None)

# Create a Weaviate client
auth_config = weaviate.auth.AuthApiKey(api_key=WEAVIATE_API_KEY) if WEAVIATE_API_KEY else None
client = weaviate.Client(url=WEAVIATE_URL, auth_client_secret=auth_config)

# Define class name for knowledge chunks
KNOWLEDGE_CLASS = "KnowledgeChunk"

# Initialize schema if not already created
def init_schema():
    if not client.schema.exists(KNOWLEDGE_CLASS):
        class_obj = {
            "class": KNOWLEDGE_CLASS,
            "vectorizer": "none",  # We'll provide our own vectors
            "vectorIndexConfig": {
                "distance": "cosine",
                "ef": 256,
                "efConstruction": 512,
                "maxConnections": 128,
            },
            "properties": [
                {
                    "name": "content",
                    "dataType": ["text"],
                    "description": "The textual content of the chunk",
                    "indexSearchable": True,
                    "tokenization": "word"
                },
                {
                    "name": "user_id",
                    "dataType": ["string"],
                    "description": "ID of the user who uploaded the document",
                    "indexFilterable": True
                },
                {
                    "name": "filename",
                    "dataType": ["string"],
                    "description": "Original filename",
                    "indexFilterable": True
                },
                {
                    "name": "job_id",
                    "dataType": ["string"],
                    "description": "Processing job ID",
                    "indexFilterable": True
                },
                {
                    "name": "content_type",
                    "dataType": ["string"],
                    "description": "Original file content type",
                    "indexFilterable": True
                },
                {
                    "name": "page",
                    "dataType": ["int"],
                    "description": "Page number for PDF documents",
                    "indexFilterable": True
                },
                {
                    "name": "batch_id",
                    "dataType": ["int"],
                    "description": "Batch identifier for processing",
                    "indexFilterable": True
                },
                {
                    "name": "processed_at",
                    "dataType": ["date"],
                    "description": "When the chunk was processed",
                    "indexFilterable": True
                }
            ]
        }
        client.schema.create_class(class_obj)
        return True
    return False

def store_vectors_in_weaviate(vectors: List[Dict[str, Any]], metadata: Dict[str, Any]):
    """
    Store vector embeddings in Weaviate
    """
    # Initialize schema if needed
    init_schema()
    
    # Prepare batch processing
    with client.batch as batch:
        batch.batch_size = 100
        
        for i, vector in enumerate(vectors):
            # Prepare properties
            properties = {
                "content": vector["content"],
                "user_id": metadata["user_id"],
                "filename": metadata["filename"],
                "job_id": metadata["job_id"],
                "content_type": metadata["content_type"],
                "processed_at": metadata["processed_at"],
                "batch_id": vector.get("batch_id", 0)
            }
            
            # Add page number if available
            if "page" in vector.get("metadata", {}):
                properties["page"] = vector["metadata"]["page"]
            
            # Add embedding vector
            embedding = np.array(vector["embedding"])
            
            # Generate a UUID based on content to avoid duplicates
            object_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"{metadata['user_id']}-{vector['content']}"))
            
            # Add object to batch
            batch.add_data_object(
                data_object=properties,
                class_name=KNOWLEDGE_CLASS,
                uuid=object_id,
                vector=embedding.tolist()
            )

def reciprocal_rank_fusion(results: list, k: int = 60):
    """
    Combine multiple result lists using Reciprocal Rank Fusion.
    
    Args:
        results: List of result sets, each containing documents with "id" field
        k: Constant to prevent high rankings in a single list from dominating (default: 60)
        
    Returns:
        List of document IDs sorted by combined relevance score
    """
    scores = {}
    for idx, doc_list in enumerate(results):
        for rank, doc in enumerate(doc_list):
            doc_id = doc["id"]
            scores[doc_id] = scores.get(doc_id, 0) + 1/(rank + k + 1)
    return sorted(scores.items(), key=lambda x: x[1], reverse=True)

async def hybrid_search(query: str, user_id: str, limit: int = 10, params: Dict = None, filters: Dict = None) -> List[Dict]:
    """
    Enhanced hybrid search with query expansion and configurable parameters
    """
    # Expand query with BERT
    
    expanded_query = await expand_query({"text": query})
    expanded_text = expanded_query.get("expanded_query", query)
    
    # Create embedding for the expanded query
    from api.db.embeddings_client import generate_embeddings
    query_embedding = await generate_embeddings([expanded_text])[0]
    
    # Build filter for user security
    where_filter = {
        "path": ["user_id"],
        "operator": "Equal",
        "valueString": user_id
    }
    
    # Add additional filters if provided
    if filters:
        additional_filters = []
        
        for key, value in filters.items():
            if key == "filename" and value:
                additional_filters.append({
                    "path": ["filename"],
                    "operator": "Equal",
                    "valueString": value
                })
            elif key == "content_type" and value:
                additional_filters.append({
                    "path": ["content_type"],
                    "operator": "Equal", 
                    "valueString": value
                })
        
        if additional_filters:
            where_filter = {
                "operator": "And",
                "operands": [where_filter] + additional_filters
            }
    
    # Get parameters with defaults
    params = params or {}
    alpha = params.get('alpha', 0.5)
    fusion_type = params.get('fusion_type', 'ranked')
    
    # Execute hybrid search
    result = (
        client.query
        .get(KNOWLEDGE_CLASS, [
            "content", "filename", "content_type", "page", "processed_at", 
            "_additional {score certainty explainScore}"
        ])
        .with_hybrid(
            query=expanded_text,
            vector=query_embedding,
            alpha=alpha,
            fusion_type=fusion_type,
            properties=["content^2", "filename^1.2"]
        )
        .with_where(where_filter)
        .with_limit(limit)
        .with_autocut(params.get('autocut', 3)) 
        .do()
    )
    
    # Extract and return results
    if result and "data" in result and "Get" in result["data"]:
        return result["data"]["Get"][KNOWLEDGE_CLASS]
    return []

async def multi_strategy_search(query: str, user_id: str, limit: int = 10, params: Dict = None, filters: Dict = None) -> List[Dict]:
    """
    Advanced search using multiple strategies combined with Reciprocal Rank Fusion
    """
    # Expand query with BERT
    
    expanded_query = await expand_query({"text": query})
    expanded_text = expanded_query.get("expanded_query", query)
    
    # Create embedding for the expanded query
    
    query_embedding = await generate_embeddings([expanded_text])[0]
    
    # Build security filter
    where_filter = {"path": ["user_id"], "operator": "Equal", "valueString": user_id}
    if filters:
        additional_filters = []
        
        for key, value in filters.items():
            if key == "filename" and value:
                additional_filters.append({
                    "path": ["filename"],
                    "operator": "Equal",
                    "valueString": value
                })
            elif key == "content_type" and value:
                additional_filters.append({
                    "path": ["content_type"],
                    "operator": "Equal", 
                    "valueString": value
                })
        
        if additional_filters:
            where_filter = {
                "operator": "And",
                "operands": [where_filter] + additional_filters
            }

    # Get more results than needed for better fusion
    search_limit = limit * 3
    result_sets = []
    
    # Strategy 1: Hybrid search (balanced)
    hybrid_results = (
        client.query.get(KNOWLEDGE_CLASS, ["id", "content", "filename", "_additional {score}"])
        .with_hybrid(
            query=expanded_text,
            vector=query_embedding,
            alpha=0.5,  # Equal weight to keywords and vectors
            properties=["content^2", "filename^1.2"]
        )
        .with_where(where_filter)
        .with_limit(search_limit)
        .do()
    )
    if hybrid_results and "data" in hybrid_results and "Get" in hybrid_results["data"]:
        result_sets.append(hybrid_results["data"]["Get"][KNOWLEDGE_CLASS])
    
    # Strategy 2: Vector-focused search
    vector_results = (
        client.query.get(KNOWLEDGE_CLASS, ["id", "content", "filename", "_additional {score}"])
        .with_hybrid(
            query=expanded_text,
            vector=query_embedding,
            alpha=0.8,  # Heavy bias toward vectors
            properties=["content"]
        )
        .with_where(where_filter)
        .with_limit(search_limit)
        .do()
    )
    if vector_results and "data" in vector_results and "Get" in vector_results["data"]:
        result_sets.append(vector_results["data"]["Get"][KNOWLEDGE_CLASS])
    
    # Strategy 3: Keyword-focused search
    keyword_results = (
        client.query.get(KNOWLEDGE_CLASS, ["id", "content", "filename", "_additional {score}"])
        .with_hybrid(
            query=expanded_text,
            vector=query_embedding,
            alpha=0.2,  # Heavy bias toward keywords
            properties=["content^3", "filename^2"]  # Stronger property weights
        )
        .with_where(where_filter)
        .with_limit(search_limit)
        .do()
    )
    if keyword_results and "data" in keyword_results and "Get" in keyword_results["data"]:
        result_sets.append(keyword_results["data"]["Get"][KNOWLEDGE_CLASS])
    
    # Apply RRF if we have multiple result sets
    if len(result_sets) > 1:
        # Get fused document IDs
        fused_items = reciprocal_rank_fusion(result_sets)
        doc_ids = [doc_id for doc_id, _ in fused_items[:limit]]
        
        # Fetch complete documents by ID
        final_results = []
        for doc_id in doc_ids:
            # Find the document in our result sets
            for result_set in result_sets:
                for doc in result_set:
                    if doc["id"] == doc_id:
                        final_results.append(doc)
                        break
                        
        return final_results[:limit]
    elif len(result_sets) == 1:
        return result_sets[0][:limit]
    else:
        return []
