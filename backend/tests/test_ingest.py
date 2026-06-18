import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta
from fastapi.testclient import TestClient

from app.main import app
from app.services.ingest.pdf_parser import MeteorologicalPDFParser
from app.services.ingest.open_meteo import OpenMeteoClient
from app.services.ingest.dqs import DataQualityService
from app.schemas.forecast import NormalizedWeatherPayload
from app.core.database import get_db

client = TestClient(app)


# --- 1. Test PDF Parser ---

def test_pdf_parser_tier1_template():
    """Tests template-based parser regex matching on simulated text lines."""
    parser = MeteorologicalPDFParser()
    
    # Mock pdfplumber context and text extraction
    mock_page = MagicMock()
    mock_page.extract_text.return_value = (
        "IMD Weather Forecast Bulletin\n"
        "Location: Mysuru, Rain: 45.5 mm, Alert: Orange\n"
        "District: Khordha, Rainfall: 15.0 mm, Warning: Yellow\n"
        "District: Bangalore, Rainfall: invalid_rain, Warning: Red\n"  # Invalid entry
    )
    mock_pdf = MagicMock()
    mock_pdf.pages = [mock_page]
    
    with patch("pdfplumber.open", return_value=MagicMock(__enter__=lambda s: mock_pdf, __exit__=MagicMock())):
        records = parser._parse_tier1_template("mock_path.pdf")
        
    assert len(records) == 2
    assert records[0]["district_name"] == "Mysuru"
    assert records[0]["rainfall_mm"] == 45.5
    assert records[0]["warning_level"] == "Orange"
    
    assert records[1]["district_name"] == "Khordha"
    assert records[1]["rainfall_mm"] == 15.0
    assert records[1]["warning_level"] == "Yellow"


# --- 2. Test Open-Meteo Client ---

@pytest.mark.asyncio
async def test_open_meteo_fetch_and_normalize():
    """Tests gridded weather REST Client response normalization."""
    om_client = OpenMeteoClient()
    
    mock_api_response = {
        "latitude": 12.3,
        "longitude": 76.6,
        "hourly": {
            "rain": [1.0, 2.5, 0.5, 0.0, 0.0],
            "temperature_2m": [26.0, 28.5, 27.0, 25.0, 24.5],
            "wind_speed_10m": [12.0, 15.5, 18.0, 10.0, 9.5]
        }
    }
    
    normalized = om_client.normalize_forecast(
        mock_api_response,
        district_name="Mysuru",
        district_code="district_29"
    )
    
    assert normalized["district_code"] == "district_29"
    assert normalized["district_name"] == "Mysuru"
    assert normalized["rainfall_mm"] == 4.0  # Sum: 1.0 + 2.5 + 0.5
    assert normalized["temp_c"] == 26.2      # Avg
    assert normalized["wind_kph"] == 18.0    # Max
    assert normalized["warning_level"] == "Green"


# --- 3. Test Data Quality Service (DQS) ---

def test_dqs_validation():
    """Tests Pydantic validation assertions and checks in DQS."""
    dqs = DataQualityService()
    
    valid_record = {
        "district_code": "district_29",
        "district_name": "Mysuru",
        "rainfall_mm": 45.5,
        "temp_c": 28.5,
        "wind_kph": 18.0,
        "warning_level": "Orange"
    }
    
    validated = dqs.validate_and_normalize(valid_record)
    assert validated is not None
    assert isinstance(validated, NormalizedWeatherPayload)
    assert validated.rainfall_mm == 45.5

    # Test invalid record (negative rain value, invalid warning level)
    invalid_record = {
        "district_code": "district_29",
        "district_name": "Mysuru",
        "rainfall_mm": -10.0,
        "warning_level": "Blue"
    }
    
    with patch.object(dqs, "_quarantine_record") as mock_quarantine:
        invalid_val = dqs.validate_and_normalize(invalid_record)
        assert invalid_val is None
        mock_quarantine.assert_called_once()


def test_dqs_source_precedence():
    """Tests override precedence: IMD (priority 1) overrides OpenMeteo (priority 2)."""
    dqs = DataQualityService()
    
    records = [
        {
            "district_code": "district_29",
            "source": "OpenMeteo",
            "rainfall_mm": 20.0,
            "warning_level": "Green"
        },
        {
            "district_code": "district_29",
            "source": "IMD",
            "rainfall_mm": 45.5,
            "warning_level": "Orange"
        }
    ]
    
    processed = dqs.enforce_precedence(records)
    assert len(processed) == 1
    assert processed[0]["source"] == "IMD"
    assert processed[0]["rainfall_mm"] == 45.5


# --- 4. Test FastAPI Ingestion API Routes ---

def test_upload_bulletin_endpoint():
    """Tests POST /api/v1/ingest/bulletin route behavior with mock parser output."""
    from unittest.mock import AsyncMock
    mock_db = AsyncMock()
    app.dependency_overrides[get_db] = lambda: mock_db
    
    mock_records = [
        {
            "district_code": "district_29",
            "district_name": "Mysuru",
            "rainfall_mm": 45.5,
            "warning_level": "Orange",
            "temp_c": None,
            "wind_kph": None
        }
    ]
    
    # Mock parser results
    with patch("app.api.v1.ingest.pdf_parser.parse", return_value={
        "status": "success",
        "tier": 1,
        "records": mock_records,
        "history": [{"step": "template_parsing", "status": "success"}]
    }):
        # Mock copying file and call endpoint
        file_content = b"Simulated PDF Content"
        response = client.post(
            "/api/v1/ingest/bulletin",
            files={"file": ("bulletin.pdf", file_content, "application/pdf")}
        )
        
    assert response.status_code == 201
    json_data = response.json()
    assert json_data["status"] == "success"
    assert json_data["records_parsed"] == 1
    
    # Cleanup overrides
    app.dependency_overrides.clear()
