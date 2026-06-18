from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.core.database import get_db
from app.services.rag.rag_engine import WeatherRAGEngine

logger = structlog.get_logger()
router = APIRouter()


class ChatQueryRequest(BaseModel):
    query: str = Field(..., min_length=2, description="Natural language weather question")
    language: str = Field("en", description="Target language: en (English), hi (Hindi)")


@router.post("/query", status_code=status.HTTP_200_OK)
async def query_weather(
    request_data: ChatQueryRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Submit a conversational query to the Weather Intelligence Assistant.
    Retrieves grounded context and implements anti-hallucination confidence fallbacks.
    """
    logger.info("Received chat query request", query=request_data.query, language=request_data.language)
    
    # Restrict language in MVP to English and Hindi
    lang = request_data.language.lower()
    if lang not in {"en", "hi"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported language. Phase 1 MVP supports only English ('en') and Hindi ('hi')."
        )

    # Initialize RAG Engine
    rag_engine = WeatherRAGEngine(db)
    
    try:
        response = await rag_engine.execute_query(request_data.query, language=lang)
        return response
    except Exception as e:
        logger.error("Error occurred in RAG pipeline execution", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while executing the weather query pipeline."
        )
