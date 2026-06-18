import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime
from fastapi.testclient import TestClient

from app.main import app
from app.services.rag.rag_engine import WeatherRAGEngine
from app.core.database import get_db

client = TestClient(app)


# --- 1. Test Query Cache Key Generation ---

def test_cache_key_generation():
    """Tests that cache keys are generated consistently."""
    engine = WeatherRAGEngine(MagicMock())
    key1 = engine._generate_cache_key("Will it rain tomorrow?", "en")
    key2 = engine._generate_cache_key("Will it rain tomorrow?", "en")
    key3 = engine._generate_cache_key("will it rain tomorrow? ", "en")  # checks capitalization and space sanitization
    key4 = engine._generate_cache_key("Will it rain tomorrow?", "hi")

    assert key1 == key2
    assert key1 == key3
    assert key1 != key4
    assert key1.startswith("query_cache:en:")


# --- 2. Test Cache Hits and Misses ---

@pytest.mark.asyncio
async def test_cache_hit_bypasses_inference():
    """Tests that a cache hit directly returns value without querying LLM."""
    mock_db = AsyncMock()
    engine = WeatherRAGEngine(mock_db)
    
    # Mock Redis client
    mock_redis = MagicMock()
    mock_redis.get.return_value = '{"answer": "Cached answer", "confidence": 0.95, "sources": []}'
    engine.redis_client = mock_redis

    response = await engine.execute_query("Will it rain in Mysuru?")
    
    assert response["answer"] == "Cached answer"
    assert response["confidence"] == 0.95
    mock_redis.get.assert_called_once()
    # Check that database context retrieval was NOT called
    mock_db.execute.assert_not_called()


# --- 3. Test RAG Context Retrieval & Safety Fallback ---

@pytest.mark.asyncio
async def test_safety_fallback_on_low_confidence():
    """Tests that the system falls back to raw database metrics if LLM confidence is low."""
    mock_db = AsyncMock()
    engine = WeatherRAGEngine(mock_db)
    
    # Mock database records to return context
    mock_db_record = MagicMock()
    mock_db_record.source = "IMD_PDF"
    mock_db_record.model_issue_time = datetime.utcnow()
    mock_db_record.data_payload = {
        "records": [
            {
                "district_code": "district_29",
                "district_name": "Mysuru",
                "rainfall_mm": 45.5,
                "warning_level": "Orange"
            }
        ]
    }
    
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [mock_db_record]
    mock_db.execute.return_value = mock_result
    
    # Force Gemini reasoning to return a low confidence score (< 0.85)
    with patch.object(engine, "_call_gemini_reasoning", return_value={
        "answer": "Not grounded answer",
        "confidence": 0.50,
        "sources": []
    }):
        response = await engine.execute_query("Will it rain in Mysuru?")
        
    assert response["answer"] == "Fallback: Displaying raw validated weather forecast parameters."
    assert "warning" in response
    assert "UNCERTAINTY_ESCALATION" in response["warning"]
    assert response["raw_data"][0]["district"] == "Mysuru"
    assert response["raw_data"][0]["rain_mm"] == 45.5


# --- 4. Test API Route Query Endpoint ---

def test_chat_query_endpoint():
    """Tests POST /api/v1/chat/query endpoint validation and response formats."""
    mock_db = AsyncMock()
    app.dependency_overrides[get_db] = lambda: mock_db
    
    # Mock execute_query method to return successful response
    mock_response = {
        "answer": "Yes, Mysuru is forecast to receive rain.",
        "confidence": 0.95,
        "sources": []
    }
    
    with patch("app.api.v1.chat.WeatherRAGEngine.execute_query", return_value=mock_response):
        response = client.post(
            "/api/v1/chat/query",
            json={"query": "Will it rain in Mysuru?", "language": "en"}
        )
        
    assert response.status_code == 200
    json_data = response.json()
    assert json_data["answer"] == "Yes, Mysuru is forecast to receive rain."
    assert json_data["confidence"] == 0.95

    # Test invalid language code request (MVP only supports en/hi)
    response_invalid = client.post(
        "/api/v1/chat/query",
        json={"query": "Will it rain in Mysuru?", "language": "kn"}
    )
    assert response_invalid.status_code == 400
    assert "Unsupported language" in response_invalid.json()["detail"]

    # Cleanup overrides
    app.dependency_overrides.clear()
