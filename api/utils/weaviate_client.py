import weaviate
from config import settings
import json
import logging
from pydantic import ConfigDict  # Nueva importación requerida

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WeaviateClient:
    _instance = None
    # Configuración actualizada para Pydantic v2
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(WeaviateClient, cls).__new__(cls)
            try:
                cls._instance.client = weaviate.Client(
                    url=settings.WEAVIATE_URL
                )
                logger.info("Connected to Weaviate at %s", settings.WEAVIATE_URL)
            except Exception as e:
                logger.error(f"Failed to connect to Weaviate: {e}")
                cls._instance.client = None
        return cls._instance
    
    def get_client(self):
        return self.client
    
    def create_schema(self, class_name, properties):
        """Create a schema class in Weaviate"""
        if not self.client:
            logger.error("No Weaviate client available")
            return False
        
        try:
            class_obj = {
                "class": class_name,
                "vectorizer": "text2vec-transformers",
                "properties": properties
            }
            
            self.client.schema.create_class(class_obj)
            logger.info(f"Created schema class '{class_name}'")
            return True
        except Exception as e:
            logger.error(f"Failed to create schema: {e}")
            return False
    
    def add_object(self, class_name, data_object, id=None):
        """Add an object to a schema class"""
        if not self.client:
            logger.error("No Weaviate client available")
            return None
        
        try:
            object_id = self.client.data_object.create(
                data_object=data_object,
                class_name=class_name,
                uuid=id
            )
            return object_id
        except Exception as e:
            logger.error(f"Failed to add object: {e}")
            return None
    
    def search(self, class_name, query, limit=5):
        """Search for objects using vector search"""
        if not self.client:
            logger.error("No Weaviate client available")
            return []
        
        try:
            result = (
                self.client.query
                .get(class_name, ["content", "metadata"])
                .with_near_text({"concepts": [query]})
                .with_limit(limit)
                .do()
            )
            
            if "data" in result and "Get" in result["data"] and class_name in result["data"]["Get"]:
                return result["data"]["Get"][class_name]
            return []
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []

def get_weaviate_client():
    return WeaviateClient().get_client()