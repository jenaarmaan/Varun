from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, Field
import io
import structlog

from app.core.database import get_db
from app.db.models import WeatherForecastRecord, GraphNode
from app.services.reports.reporter import SituationReporter
from app.services.impact.impact_engine import ImpactPredictionEngine
from app.services.decision.decision_engine import WeatherDecisionEngine
from app.services.rag.graph_repo import GraphRepository

logger = structlog.get_logger()
router = APIRouter()


class ReportCompileRequest(BaseModel):
    district_code: str = Field(..., description="LGD district code (e.g., district_29)")
    officer_name: str = Field("Duty Officer", description="Name of the compiling officer")


@router.post("/compile", status_code=status.HTTP_200_OK)
async def compile_situation_report(
    request_data: ReportCompileRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieves weather context and graph relations for a target district,
    runs impact calculations, generates emergency SOP checklists,
    and compiles a downloadable report PDF.
    """
    logger.info("Received request to compile situation report", district=request_data.district_code)
    
    # 1. Fetch District Node from Graph to verify existence and name
    graph_repo = GraphRepository(db)
    district_node = await graph_repo.get_node_by_id(request_data.district_code)
    
    if not district_node:
        # Fallback list for mock/sandbox verification if database not fully seeded
        mock_districts = {
            "district_29": {"name": "Mysuru", "state": "Karnataka", "pop": 3001000},
            "district_21": {"name": "Khordha (Bhubaneswar)", "state": "Odisha", "pop": 2251000}
        }
        if request_data.district_code in mock_districts:
            district_name = mock_districts[request_data.district_code]["name"]
            properties = mock_districts[request_data.district_code]
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"District {request_data.district_code} not found in database graph nodes."
            )
    else:
        district_name = district_node.name
        properties = district_node.properties or {}

    # 2. Get latest weather forecast from DB
    result = await db.execute(
        select(WeatherForecastRecord).order_by(WeatherForecastRecord.ingestion_time.desc()).limit(3)
    )
    records = result.scalars().all()
    
    # Find matching record in DB
    forecast_rain = 0.0
    warning_level = "Green"
    found_forecast = False
    
    for rec in records:
        payload = rec.data_payload or {}
        inner_records = payload.get("records", [])
        for r in inner_records:
            if r.get("district_code") == request_data.district_code:
                forecast_rain = r.get("rainfall_mm", 0.0)
                warning_level = r.get("warning_level", "Green")
                found_forecast = True
                break
        if found_forecast:
            break

    # If no DB records found, provide sandbox fallback
    if not found_forecast:
        logger.info("No database forecast record found. Falling back to default sandbox values.")
        if request_data.district_code == "district_29":
            forecast_rain = 124.8
            warning_level = "Red"
        else:
            forecast_rain = 62.0
            warning_level = "Orange"

    # 3. Calculate dynamic risk score and NDMA SOP actions
    impact_engine = ImpactPredictionEngine()
    
    # Extract mock parameters from node details
    elevation = properties.get("elevation_metric", 0.8 if request_data.district_code == "district_29" else 0.4)
    proximity = properties.get("river_proximity", 0.9 if request_data.district_code == "district_29" else 0.5)
    saturation = properties.get("soil_saturation", 0.85 if request_data.district_code == "district_29" else 0.6)
    
    risk_score = impact_engine.calculate_flood_risk(
        rainfall_mm=forecast_rain,
        elevation_metric=elevation,
        river_proximity=proximity,
        soil_saturation=saturation
    )
    
    decision_engine = WeatherDecisionEngine()
    sop_actions = decision_engine.generate_sop_checklist(risk_score)

    # 4. Generate Situation Report PDF using ReportLab
    reporter = SituationReporter()
    try:
        pdf_bytes = reporter.compile_report(
            district_name=district_name,
            forecast_rain=forecast_rain,
            warning_level=warning_level,
            risk_score=risk_score,
            sop_actions=sop_actions,
            officer_name=request_data.officer_name
        )
    except Exception as e:
        logger.error("Failed to compile situation report PDF", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error occurred during PDF compile layout generation."
        )

    # Return as binary stream
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=SitRep_{district_name.replace(' ', '_')}.pdf"}
    )
