import weaviate
import os
import uuid
import logging
from typing import List, Dict, Any
import numpy as np
from datetime import datetime
from dotenv import load_dotenv
from db.embeddings_client import generate_embeddings
from db.query_expansion import expand_query

load_dotenv()

logger = logging.getLogger(__name__)

# Get Weaviate credentials from environment variables
WEAVIATE_URL = os.getenv("WEAVIATE_URL", "http://localhost:8080")
WEAVIATE_API_KEY = os.getenv("WEAVIATE_API_KEY", None)

# Create a Weaviate client with version compatibility
try:
    # Determine Weaviate client version
    import pkg_resources
    weaviate_version = pkg_resources.get_distribution("weaviate-client").version
    logger.info(f"Detected weaviate-client version: {weaviate_version}")
    
    if weaviate_version.startswith("4."):
        # Weaviate Client v4.x
        from weaviate.client import WeaviateClient
        from weaviate.connect import ConnectionParams

        # Create connection params WITHOUT auth (remove auth_client_secret)
        from urllib.parse import urlparse
        parsed_url = urlparse(WEAVIATE_URL)
        host = parsed_url.netloc.split(':')[0] if ':' in parsed_url.netloc else parsed_url.netloc
        http_port = int(parsed_url.netloc.split(':')[1]) if ':' in parsed_url.netloc else 8080
        grpc_port = http_port + 1  # Typically gRPC is HTTP + 1

        # Create connection params without auth_client_secret
        connection_params = ConnectionParams.from_url(
            url=WEAVIATE_URL,
            grpc_port=grpc_port
        )
        
        # Create client (auth will be handled by docker-compose environment variables)
        client = WeaviateClient(connection_params)
        logger.info("Connected to Weaviate using v4 client")
    else:
        # Older Weaviate client
        client = weaviate.Client(WEAVIATE_URL)
        logger.info("Connected to Weaviate using legacy client")
except Exception as e:
    logger.error(f"Error connecting to Weaviate: {e}")
    # Create a basic client as fallback
    try:
        client = weaviate.Client(WEAVIATE_URL) 
        logger.warning("Connected with basic client after error")
    except:
        raise RuntimeError(f"Cannot connect to Weaviate: {e}")

# Define class name for knowledge chunks
KNOWLEDGE_CLASS = "KnowledgeChunk"

# Corregir error de indentación

def init_schema():
    """Initialize schema if not already created"""
    try:
        # Intentar obtener el esquema con diferentes métodos según versión
        try:
            # Método para v3
            schema = client.schema.get()
        except (AttributeError, TypeError):
            try:
                # Método para v4
                schema = client.get_schema()
            except (AttributeError, TypeError):
                try:
                    # Método para otras versiones
                    schema = client.schema().get()
                except Exception as e:
                    logger.error(f"Error accessing schema: {e}")
                    raise RuntimeError(f"No se puede determinar la versión del cliente Weaviate: {e}")
        
        # Verificar si la clase ya existe
        existing_classes = [cls["class"] for cls in schema.get("classes", [])]
        
        # Esta es probablemente la línea 112 donde falta el bloque indentado
        if KNOWLEDGE_CLASS not in existing_classes:
            # Añadir código aquí para crear la clase
            class_obj = {
                "class": KNOWLEDGE_CLASS,
                "vectorizer": "none", 
                "vectorIndexConfig": {
                    "distance": "cosine",
                    "ef": 256,
                    "efConstruction": 512
                },
                "properties": [
                    {"name": "content", "dataType": ["text"]},
                    {"name": "user_id", "dataType": ["string"]},
                    {"name": "filename", "dataType": ["string"]},
                    {"name": "job_id", "dataType": ["string"]},
                    {"name": "content_type", "dataType": ["string"]},
                    {"name": "processed_at", "dataType": ["string"]}
                ]
            }
            
            # Crear la clase en weaviate usando la API correcta según la versión
            try:
                client.schema.create_class(class_obj)
            except AttributeError:
                try:
                    client.schema().create_class(class_obj)
                except:
                    # Último intento para V4
                    client.collections.create(class_obj)
            
            logger.info(f"Created schema for class {KNOWLEDGE_CLASS}")
    except Exception as e:
        logger.error(f"Error initializing schema: {e}")
        raise RuntimeError(f"Cannot initialize schema: {e}")

def store_vectors_in_weaviate(vectors: List[Dict[str, Any]], metadata: Dict[str, Any]):
    """
    Store vector embeddings in Weaviate and return the generated UUIDs
    """
    # Initialize schema if needed
    init_schema()
    
    # Para almacenar los UUIDs generados
    generated_ids = []
    
    # Prepare batch processing
    with client.batch as batch:
        batch.batch_size = 100
        
        for i, vector in enumerate(vectors):
            # Generate a UUID based on content to avoid duplicates
            object_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"{metadata['user_id']}-{vector['content']}"))
            generated_ids.append(object_id)  # Guardar ID
            
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
            
            # Add object to batch
            batch.add_data_object(
                data_object=properties,
                class_name=KNOWLEDGE_CLASS,
                uuid=object_id,
                vector=embedding.tolist()
            )
            
    # Devolver los IDs generados
    return generated_ids

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
    from db.embeddings_client import generate_embeddings
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
