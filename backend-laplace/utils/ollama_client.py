import httpx
import json
import os
from typing import Dict, List, Any

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
MODEL_NAME = os.getenv("OLLAMA_MODEL", "mistral")

async def generate_response(context: List[Dict[str, Any]], request: Dict[str, Any]) -> str:
    """
    Generate a response using Ollama based on the provided context and request
    
    Args:
        context: List of context documents retrieved from Weaviate
        request: The original request containing the query
    
    Returns:
        str: The generated response
    """
    # Prepare prompt with context
    prompt = f"""Please answer the following question based on the provided context:
    
Question: {request.get('query', '')}

Context:
"""
    
    # Add context documents to the prompt
    for doc in context:
        prompt += f"- {doc.get('content', '')}\n"
    
    # Call Ollama API
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            f"{OLLAMA_BASE_URL}/api/generate",
            json={
                "model": MODEL_NAME,
                "prompt": prompt,
                "stream": False
            }
        )
        
        if response.status_code != 200:
            raise Exception(f"Failed to get response from Ollama: {response.text}")
        
        result = response.json()
        return result.get("response", "")
