import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime

from app.services.rag.graph_repo import GraphRepository
from app.services.impact.impact_engine import ImpactPredictionEngine
from app.services.decision.decision_engine import WeatherDecisionEngine
from app.services.evaluation.eval_service import AIEvaluationService


# --- 1. Test Impact Prediction Engine ---

def test_impact_engine_weighted_scoring():
    """Verifies that the weighted score formula maps rainfall and spatial properties correctly."""
    engine = ImpactPredictionEngine()
    
    # 1. Extreme Heavy Rain (>204.5mm) + Low elevation (1.0) + River border (1.0) + Saturated soil (1.0)
    score_extreme = engine.calculate_flood_risk(
        rainfall_mm=250.0,
        elevation_metric=1.0,
        river_proximity=1.0,
        soil_saturation=1.0
    )
    # Calculation: (0.4 * 1.0) + (0.3 * 1.0) + (0.2 * 1.0) + (0.1 * 1.0) = 1.0
    assert score_extreme == 1.0

    # 2. Heavy Rain (100mm -> factor 0.5) + mid variables (0.5)
    score_heavy = engine.calculate_flood_risk(
        rainfall_mm=100.0,
        elevation_metric=0.5,
        river_proximity=0.5,
        soil_saturation=0.5
    )
    # Calculation: (0.4 * 0.5) + (0.3 * 0.5) + (0.2 * 0.5) + (0.1 * 0.5) = 0.5
    assert score_heavy == 0.5

    # 3. Dry day (0mm -> factor 0.0) + high dry terrain (0.0)
    score_safe = engine.calculate_flood_risk(
        rainfall_mm=0.0,
        elevation_metric=0.0,
        river_proximity=0.0,
        soil_saturation=0.0
    )
    assert score_safe == 0.0


# --- 2. Test Weather Decision Engine ---

def test_decision_engine_sop_mapping():
    """Asserts that risk scores match correct NDMA SOP checklists."""
    engine = WeatherDecisionEngine()
    
    # Red Alert Checklist
    red_checklist = engine.generate_sop_checklist(0.85)
    assert len(red_checklist) == 5
    assert "evacuation" in red_checklist[1].lower()
    
    # Orange Alert Checklist
    orange_checklist = engine.generate_sop_checklist(0.60)
    assert len(orange_checklist) == 4
    assert "standby" in orange_checklist[0].lower()
    
    # Green Alert (Safe)
    green_checklist = engine.generate_sop_checklist(0.10)
    assert len(green_checklist) == 2
    assert "no emergency actions" in green_checklist[1].lower()


# --- 3. Test Graph Repository ---

@pytest.mark.asyncio
async def test_graph_repo_downstream_traversal():
    """Tests GraphRepository downstream recursive CTE SQL binding compilation."""
    mock_db = AsyncMock()
    mock_row = ["school_mysuru_public", "school", "Mysuru Public School"]
    mock_result = MagicMock()
    mock_result.fetchall.return_value = [mock_row]
    mock_db.execute.return_value = mock_result
    
    repo = GraphRepository(mock_db)
    downstream = await repo.get_downstream_infrastructure("reservoir_kr_sagar")
    
    assert len(downstream) == 1
    assert downstream[0]["id"] == "school_mysuru_public"
    assert downstream[0]["type"] == "school"
    mock_db.execute.assert_called_once()


# --- 4. Test MLOps AI Evaluation Service ---

@pytest.mark.asyncio
async def test_eval_service_hallucination_and_grounding():
    """Verifies that evaluation metrics flag numeric/warning discrepancies between output and context."""
    mock_db = AsyncMock()
    eval_service = AIEvaluationService(mock_db)
    
    context = [
        "District: Mysuru, Rainfall: 45.5 mm, Warning: Orange",
        "District: Khordha, Rainfall: 15.0 mm, Warning: Yellow"
    ]
    
    # 1. Honest Response (matches numbers and warnings)
    response_honest = "Mysuru will receive 45.5 mm rain under Orange alert."
    metrics_honest = await eval_service.evaluate_response(
        query="Will it rain in Mysuru?",
        response_text=response_honest,
        context_chunks=context,
        latency_sec=1.5
    )
    assert metrics_honest["hallucination_rate"] == 0.0
    assert metrics_honest["citation_accuracy"] == 1.0
    assert metrics_honest["confidence_score"] == 1.0  # (1 - 0) * (0.7 + 0.3) = 1.0
    
    # 2. Hallucinated Response (numeric mismatch: claims 85.0 mm which is not in context)
    response_hallucinated = "Mysuru will receive 85.0 mm rain under Orange alert."
    metrics_hallucinated = await eval_service.evaluate_response(
        query="Will it rain in Mysuru?",
        response_text=response_hallucinated,
        context_chunks=context,
        latency_sec=1.2
    )
    assert metrics_hallucinated["hallucination_rate"] == 1.0
    assert metrics_hallucinated["confidence_score"] == 0.0
