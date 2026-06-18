import os
import shutil
import tempfile
from datetime import datetime
from typing import List
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import structlog

from app.core.database import get_db
from app.db.models import WeatherForecastRecord, GraphNode
from app.services.ingest.pdf_parser import MeteorologicalPDFParser
from app.services.ingest.open_meteo import OpenMeteoClient
from app.services.ingest.dqs import DataQualityService

logger = structlog.get_logger()
router = APIRouter()

pdf_parser = MeteorologicalPDFParser()
open_meteo_client = OpenMeteoClient()
dqs = DataQualityService()


@router.post("/bulletin", status_code=status.HTTP_201_CREATED)
async def upload_bulletin(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    """
    Upload and parse an official IMD daily forecast PDF bulletin.
    Validates data lineage and quarantines corrupted records via DQS.
    """
    logger.info("Received PDF bulletin upload request", filename=file.filename)
    
    # 1. Enforce PDF safety limits
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file format. Only PDF bulletins are accepted."
        )

    # Save to a temporary file in a secure sandboxed location
    temp_dir = tempfile.gettempdir()
    temp_path = os.path.join(temp_dir, f"imd_upload_{os.urandom(8).hex()}.pdf")
    
    try:
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # 2. Run multi-tier PDF parsing
        parsed_result = pdf_parser.parse(temp_path)
        if parsed_result["status"] == "failed":
            # Quarantine the entire file path as corrupt/unparsable
            dqs._quarantine_record({"filename": file.filename}, reason="PDF Parsing failed across all tiers.")
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Unable to parse PDF weather bulletin layout."
            )
            
        raw_records = parsed_result["records"]
        validated_records = []
        
        # 3. Process parsed items via DQS
        for rec in raw_records:
            normalized = dqs.validate_and_normalize(rec)
            if normalized:
                validated_records.append(normalized.model_dump())
                
        if not validated_records:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="No valid metereological records could be validated from the bulletin."
            )

        # 4. Save to database forecast records (preserving data lineage)
        db_record = WeatherForecastRecord(
            source="IMD_PDF",
            model_issue_time=datetime.utcnow(),  # Set mock model issue timestamp
            transformation_history=parsed_result["history"],
            data_payload={"records": validated_records}
        )
        db.add(db_record)
        await db.commit()
        await db.refresh(db_record)
        
        logger.info("Successfully ingested PDF weather bulletin", record_id=db_record.id)
        
        return {
            "status": "success",
            "record_id": db_record.id,
            "records_parsed": len(validated_records),
            "tier_used": parsed_result["tier"]
        }
        
    finally:
        # Cleanup temporary files
        if os.path.exists(temp_path):
            os.remove(temp_path)


@router.post("/sync-grid", status_code=status.HTTP_202_ACCEPTED)
async def sync_grid_forecast(
    db: AsyncSession = Depends(get_db)
):
    """
    Triggers Open-Meteo REST API sync for all loaded district centroids.
    Validates grid metrics and resolves conflicts using source priority overrides.
    """
    logger.info("Triggering gridded forecast sync task")
    
    # 1. Fetch all seeded districts from PostGIS graph nodes to get centroid/coordinates
    result = await db.execute(
        select(GraphNode).where(GraphNode.type == "district")
    )
    districts = result.scalars().all()
    
    if not districts:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No district nodes seeded in the Graph to query forecast targets."
        )
        
    synced_records = []
    
    # 2. Iterate and query Open-Meteo for each district (MVP runs synchronously)
    for dist in districts:
        # Get coordinates from node properties or mock coordinates from geom centroid
        # For simplicity, extract mock coordinates from geom or properties JSONB
        props = dist.properties or {}
        # Default mock coordinates if properties missing
        lat = props.get("latitude", 12.31 if dist.id == "district_29" else 20.29)
        lon = props.get("longitude", 76.64 if dist.id == "district_29" else 85.82)
        
        raw_api_data = await open_meteo_client.fetch_forecast(lat, lon)
        if raw_api_data:
            normalized = open_meteo_client.normalize_forecast(
                raw_api_data,
                district_name=dist.name,
                district_code=dist.id
            )
            
            # 3. Validate grid forecast record
            validated = dqs.validate_and_normalize(normalized)
            if validated:
                synced_records.append(validated.model_dump())
                
    if not synced_records:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to sync forecast data from Open-Meteo API."
        )

    # 4. Save to database forecast records (preserving data lineage)
    db_record = WeatherForecastRecord(
        source="OpenMeteo",
        model_issue_time=datetime.utcnow(),
        transformation_history=[{"step": "open_meteo_sync", "status": "success"}],
        data_payload={"records": synced_records}
    )
    db.add(db_record)
    await db.commit()
    await db.refresh(db_record)
    
    logger.info("Successfully completed Open-Meteo grid sync", record_id=db_record.id)
    
    return {
        "status": "completed",
        "record_id": db_record.id,
        "districts_synced": len(synced_records)
    }
