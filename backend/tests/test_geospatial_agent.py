import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime

from app.services.impact.impact_engine import ImpactPredictionEngine
from app.services.rag.rag_engine import WeatherRAGEngine


def test_hvi_calculation_scaling():
    """Asserts that Human Vulnerability Index (HVI) scales correctly and caps at population limits."""
    engine = ImpactPredictionEngine()

    # 1. Test scaling with population 3,001,000 (exceeds 1,000,000 scaling limit, caps at factor 1.0)
    # HVI = risk_score * (0.7 + 0.3 * 1.0) = risk_score * 1.0
    hvi_large_pop = engine.calculate_human_vulnerability_index(flood_risk_score=0.88, population=3001000)
    assert hvi_large_pop == 0.88

    # 2. Test scaling with population 500,000 (factor 0.5)
    # HVI = risk_score * (0.7 + 0.3 * 0.5) = risk_score * (0.7 + 0.15) = risk_score * 0.85
    # 0.88 * 0.85 = 0.748 -> round to 0.748
    hvi_medium_pop = engine.calculate_human_vulnerability_index(flood_risk_score=0.88, population=500000)
    assert hvi_medium_pop == 0.748

    # 3. Test scaling with population 0 (factor 0.0)
    # HVI = risk_score * (0.7 + 0.0) = risk_score * 0.7
    # 0.88 * 0.7 = 0.616
    hvi_zero_pop = engine.calculate_human_vulnerability_index(flood_risk_score=0.88, population=0)
    assert hvi_zero_pop == 0.616


@pytest.mark.asyncio
async def test_cross_modal_reasoning_synthesis():
    """Verifies that WeatherRAGEngine performs cross-modal reasoning over multiple domains."""
    mock_db = AsyncMock()
    engine = WeatherRAGEngine(mock_db)

    # Mock GraphNode search return (Bhubaneswar district node details)
    mock_node = MagicMock()
    mock_node.id = "district_21"
    mock_node.name = "Khordha (Bhubaneswar)"
    mock_node.properties = {
        "state": "Odisha",
        "population": 2251000,
        "elevation_metric": 0.4,
        "river_proximity": 0.5,
        "soil_saturation": 0.6
    }
    
    mock_node_result = MagicMock()
    mock_node_result.scalars.return_value.first.return_value = mock_node
    
    # Configure DB execution to return district details
    mock_db.execute.return_value = mock_node_result

    # Mock DB Context Weather Ingestion record
    mock_forecast = {
        "district_code": "district_21",
        "district_name": "Khordha (Bhubaneswar)",
        "rainfall_mm": 62.0,
        "warning_level": "Orange",
        "source": "IMD_PDF",
        "issue_time": datetime.utcnow().isoformat()
    }

    # Execute query reasoning manually
    with patch.object(engine, "_retrieve_context", return_value=[mock_forecast]):
        response = await engine.execute_query("Run a geospatial risk analysis for Bhubaneswar", "en")

    # Assert cross-modal outputs
    answer = response["answer"]
    assert "Google Earth AI Cross-Modal Risk Synthesis" in answer
    assert "Meteorological Domain" in answer
    assert "Geospatial & Hydrological Network Domain" in answer
    assert "Population Domain" in answer
    assert "Human Vulnerability Index" in answer
    assert "HVI" in answer
    assert "0.36 / 1.0" in answer
    assert "Emergency Action SOPs" in answer
