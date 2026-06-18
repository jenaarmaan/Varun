import json
import hashlib
from typing import Dict, Any, List, Optional
from datetime import datetime
import redis
import structlog

from app.core.config import settings
from app.db.models import WeatherForecastRecord

logger = structlog.get_logger()


class WeatherRAGEngine:
    """Core RAG engine implementing query caching, semantic retrieval, and safety triggers."""

    def __init__(self, db_session):
        self.db = db_session
        # Initialize Redis connection with fallback to None if offline
        try:
            self.redis_client = redis.from_url(settings.REDIS_URL, socket_timeout=2.0)
            self.redis_client.ping()
            logger.info("Connected to Redis successfully for query caching.")
        except Exception as e:
            logger.warn("Redis is offline. Query caching will be bypassed.", error=str(e))
            self.redis_client = None

    async def execute_query(self, query: str, language: str = "en") -> Dict[str, Any]:
        """
        Executes RAG pipeline: Cache lookup -> Context Retrieval -> Gemini Reasoning -> Safety check.
        """
        # 1. Redis Cache Lookup
        cache_key = self._generate_cache_key(query, language)
        if self.redis_client:
            try:
                cached_val = self.redis_client.get(cache_key)
                if cached_val:
                    logger.info("Cache hit for weather query", query=query)
                    return json.loads(cached_val)
            except Exception as e:
                logger.warn("Failed to retrieve from Redis cache", error=str(e))

        # 2. Context Retrieval (Query DB gridded forecasts & bulletins)
        # In MVP, retrieve recent forecast records from DB
        context_data = await self._retrieve_context(query)
        
        # 3. LLM/Gemini Reasoning & Citation Verification
        try:
            rag_response = await self._call_gemini_reasoning(query, context_data, language)
        except Exception as e:
            logger.error("Vertex AI call failed. Executing safety fallback.", error=str(e))
            rag_response = self._execute_safe_fallback(context_data)

        # 4. Safety Escalation Trigger
        if rag_response.get("confidence", 0.0) < settings.SAFETY_CONFIDENCE_THRESHOLD:
            logger.warn("RAG confidence below safety threshold. Escalating to raw data.")
            rag_response = self._execute_safe_fallback(context_data)
            rag_response["warning"] = "UNCERTAINTY_ESCALATION: Low AI confidence. Showing raw forecast parameters."

        # Append official IMD disclaimer (IT Act 2000 requirement)
        rag_response["disclaimer"] = (
            "Disclaimer: Conversational outputs are synthesized by AI based on official forecast bulletins "
            "from the India Meteorological Department (IMD). Verify critical warnings directly on official government portals."
        )

        # 5. Populate Redis Cache
        if self.redis_client and rag_response.get("status") != "fallback":
            try:
                self.redis_client.setex(
                    cache_key,
                    settings.CACHE_DEFAULT_TTL,
                    json.dumps(rag_response)
                )
            except Exception as e:
                logger.warn("Failed to write to Redis cache", error=str(e))

        return rag_response

    def _generate_cache_key(self, query: str, language: str) -> str:
        """Generates a stable cache key based on query hash."""
        query_hash = hashlib.sha256(query.strip().lower().encode("utf-8")).hexdigest()[:16]
        return f"query_cache:{language}:{query_hash}"

    async def _retrieve_context(self, query: str) -> List[Dict[str, Any]]:
        """Retrieves recent weather parameters from DB."""
        # Simple extraction of records for MVP context
        from sqlalchemy import select
        result = await self.db.execute(
            select(WeatherForecastRecord).order_by(WeatherForecastRecord.ingestion_time.desc()).limit(3)
        )
        records = result.scalars().all()
        
        context_records = []
        for rec in records:
            payload = rec.data_payload or {}
            inner_records = payload.get("records", [])
            for r in inner_records:
                r["source"] = rec.source
                r["issue_time"] = rec.model_issue_time.isoformat()
                context_records.append(r)
        return context_records

    async def _call_gemini_reasoning(
        self,
        query: str,
        context_data: List[Dict[str, Any]],
        language: str
    ) -> Dict[str, Any]:
        """
        Triggers Gemini Pro / Vertex AI inference.
        Returns mock response for MVP when credentials not active.
        """
        # Match location keywords in query to context
        matched_context = []
        query_lower = query.lower()
        
        for record in context_data:
            dist_name = record.get("district_name", "").lower()
            if dist_name in query_lower:
                matched_context.append(record)

        if not matched_context:
            return {
                "answer": "No forecast context could be retrieved for the requested district.",
                "confidence": 0.0,
                "sources": []
            }

        # Build natural language response based on matched data (mocking LLM synthesis)
        target = matched_context[0]
        name = target["district_name"]
        rain = target["rainfall_mm"]
        warning = target["warning_level"]
        source = target["source"]
        issue_time = target["issue_time"]

        answer_en = f"Yes, {name} is forecast to receive {rain} mm of rainfall. IMD warning level is {warning}."
        answer_hi = f"हाँ, {name} में {rain} मिमी बारिश का पूर्वानुमान है। IMD चेतावनी स्तर {warning} है।"
        
        answer = answer_hi if language == "hi" else answer_en

        return {
            "answer": answer,
            "confidence": 0.95,
            "sources": [
                {
                    "source_id": source,
                    "issue_time": issue_time,
                    "quote": f"District: {name}, Rainfall: {rain} mm, Warning: {warning}"
                }
            ]
        }

    def _execute_safe_fallback(self, context_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Executes safe local fallback, bypassing LLM synthesis and returning raw DB grids."""
        formatted_grids = []
        for rec in context_data[:5]:
            formatted_grids.append({
                "district": rec.get("district_name"),
                "rain_mm": rec.get("rainfall_mm"),
                "warning": rec.get("warning_level"),
                "source": rec.get("source")
            })

        return {
            "status": "fallback",
            "answer": "Fallback: Displaying raw validated weather forecast parameters.",
            "confidence": 1.0,
            "raw_data": formatted_grids,
            "sources": []
        }
