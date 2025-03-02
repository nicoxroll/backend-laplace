import weaviate
import os
import uuid
from typing import List, Dict, Any
import numpy as np
from datetime import datetime
from dotenv import load_dotenv

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

def hybrid_search(query: str, user_id: str, limit: int = 10, filters: Dict = None) -> List[Dict]:
    """
    Perform hybrid search (vector + keyword) on the knowledge base
    """
    # Create embedding for the query
    from api.services.file_processor import ROPEChunker
    chunker = ROPEChunker()
    query_embedding = chunker.embedding_model.embed_query(query)
    
    # Build filter
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
    
    # Execute hybrid search
    result = (
        client.query
        .get(KNOWLEDGE_CLASS, ["content", "filename", "content_type", "page", "processed_at"])
        .with_hybrid(
            query=query,
            vector=query_embedding,
            alpha=0.5  # Balance between vector and keyword search (0.0-1.0)
        )
        .with_where(where_filter)
        .with_limit(limit)
        .do()
    )
    
    # Extract and return results
    if result and "data" in result and "Get" in result["data"]:
        return result["data"]["Get"][KNOWLEDGE_CLASS]
    return []
