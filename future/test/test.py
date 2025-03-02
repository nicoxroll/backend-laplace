# tests/test_analyze.py (Ejemplo)
async def test_full_analysis_flow():
    test_query = {
        "agent_id": "code_agent",
        "knowledge_id": "kb_123",
        "repo_id": "repo_456",
        "query": "Implementar JWT seguro"
    }
    
    # Test cache miss
    response = await client.post("/analyze", json=test_query)
    assert response.status_code == 200
    assert "explicacion" in response.json()
    
    # Test cache hit
    cached_response = await client.post("/analyze", json=test_query)
    assert cached_response.headers["X-Cache-Status"] == "HIT"