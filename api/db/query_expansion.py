import httpx
from typing import Dict, Any

async def expand_query(query_data: Dict[str, str]) -> Dict[str, Any]:
    """
    Call the BERT service to expand a query with semantically related terms
    
    Args:
        query_data: Dictionary containing the query text in the 'text' field
    
    Returns:
        Dictionary with expanded query and expansion terms
    """
    try:
        # Call your BERT service
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "http://bert-service:5000/expand",  # URL to your BERT service
                json=query_data,
                timeout=10.0
            )
            
            # Handle errors
            response.raise_for_status()
            
            # Return expanded query
            return response.json()
    except Exception as e:
        # Log error and return original query if expansion fails
        print(f"Query expansion failed: {str(e)}")
        text = query_data.get("text", "")
        return {"expanded_query": text, "expansion_terms": []}