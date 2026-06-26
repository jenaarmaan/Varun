import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime
from fastapi.testclient import TestClient

from app.main import app
from app.core.database import get_db

client = TestClient(app)


def test_reports_compile_endpoint_success():
    """Tests POST /api/v1/reports/compile endpoint returns PDF file streaming response."""
    mock_db = AsyncMock()
    app.dependency_overrides[get_db] = lambda: mock_db

    # Mock GraphNode in DB lookup
    mock_node = MagicMock()
    mock_node.name = "Mysuru"
    mock_node.properties = {"state": "Karnataka", "elevation_metric": 0.8}
    
    mock_result = MagicMock()
    mock_result.scalars.return_value.first.return_value = mock_node
    
    # Mock WeatherForecastRecord lookup
    mock_db_record = MagicMock()
    mock_db_record.source = "IMD_PDF"
    mock_db_record.model_issue_time = datetime.utcnow()
    mock_db_record.data_payload = {
        "records": [
            {
                "district_code": "district_29",
                "district_name": "Mysuru",
                "rainfall_mm": 124.8,
                "warning_level": "Red"
            }
        ]
    }
    
    # Configure mock execute responses
    # First query (GraphNode): returns mock_result
    # Second query (WeatherForecastRecord): returns mock_forecast_result
    mock_forecast_result = MagicMock()
    mock_forecast_result.scalars.return_value.all.return_value = [mock_db_record]
    
    mock_db.execute.side_effect = [mock_result, mock_forecast_result]

    # Mock PDF binary output
    mock_pdf_bytes = b"%PDF-1.4 simulated report bytes"
    
    with patch("app.api.v1.reports.SituationReporter.compile_report", return_value=mock_pdf_bytes):
        response = client.post(
            "/api/v1/reports/compile",
            json={"district_code": "district_29", "officer_name": "Test Officer"}
        )

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert "attachment" in response.headers["content-disposition"]
    assert "SitRep_Mysuru.pdf" in response.headers["content-disposition"]
    assert response.content == mock_pdf_bytes

    # Cleanup overrides
    app.dependency_overrides.clear()


def test_reports_compile_endpoint_not_found():
    """Tests that compile endpoint returns 404 for unregistered district code."""
    mock_db = AsyncMock()
    app.dependency_overrides[get_db] = lambda: mock_db

    # Node not found in DB
    mock_result = MagicMock()
    mock_result.scalars.return_value.first.return_value = None
    mock_db.execute.return_value = mock_result

    response = client.post(
        "/api/v1/reports/compile",
        json={"district_code": "district_invalid", "officer_name": "Test Officer"}
    )

    assert response.status_code == 404
    assert "not found" in response.json()["detail"]

    # Cleanup overrides
    app.dependency_overrides.clear()
