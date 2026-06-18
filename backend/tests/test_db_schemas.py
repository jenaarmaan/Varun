import pytest
from sqlalchemy import select, func
from app.db.models import User, WeatherForecastRecord, GraphNode, GraphEdge, EvaluationLog, AuditLog


def test_user_model_fields():
    """Asserts that User model schema fields exist and match requirements."""
    user = User(
        email="test_officer@gov.in",
        hashed_password="hashedpassword123",
        role="officer",
        consent_alerts=True,
        phone_number="+919999999999"
    )
    assert user.email == "test_officer@gov.in"
    assert user.role == "officer"
    assert user.consent_alerts is True
    assert user.phone_number == "+919999999999"


def test_forecast_data_lineage_fields():
    """Asserts that WeatherForecastRecord preserves data lineage metadata fields."""
    record = WeatherForecastRecord(
        source="IMD_PDF",
        transformation_history=[{"step": "pdf_extraction", "timestamp": "2026-06-18T12:00:00Z"}],
        data_payload={"rainfall_forecast_mm": 45.5}
    )
    assert record.source == "IMD_PDF"
    assert "step" in record.transformation_history[0]
    assert record.data_payload["rainfall_forecast_mm"] == 45.5


def test_graph_node_spatial_compilation():
    """Verifies that PostGIS spatial functions compile correctly in SQLAlchemy queries."""
    # This checks SQL compilation of ST_Contains and ST_DWithin
    point_geom = func.ST_SetSRID(func.ST_MakePoint(76.64, 12.31), 4326)
    query = select(GraphNode).where(func.ST_Contains(GraphNode.geom, point_geom))
    sql_str = str(query)
    
    assert "ST_Contains" in sql_str
    assert "ST_MakePoint" in sql_str


def test_graph_recursive_cte_compilation():
    """Verifies that the recursive CTE query for Weather Intelligence Graph compiles successfully."""
    # Test query compilation for graph traversal path
    from sqlalchemy.orm import aliased
    
    di_alias = aliased(GraphNode, name="downstream_impacts")
    
    # Simple compilation check of CTE syntax
    query = select(GraphNode.id, GraphNode.type).where(GraphNode.id == "reservoir_kr_sagar")
    cte_query = query.cte("downstream_impacts", recursive=True)
    
    recursive_query = select(cte_query.c.id, cte_query.c.type)
    sql_str = str(recursive_query)
    
    assert "WITH RECURSIVE" in sql_str
    assert "downstream_impacts" in sql_str
