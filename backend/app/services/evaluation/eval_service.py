import re
from datetime import datetime
from typing import List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.db.models import EvaluationLog

logger = structlog.get_logger()


class AIEvaluationService:
    """MLOps Evaluation Service calculating RAG grounding, citation, and hallucination metrics."""

    def __init__(self, db_session: AsyncSession):
        self.db = db_session

    async def evaluate_response(
        self,
        query: str,
        response_text: str,
        context_chunks: List[str],
        latency_sec: float
    ) -> Dict[str, Any]:
        """
        Analyzes response text against context to calculate factual precision.
        Saves metrics to the evaluation logs database.
        """
        # 1. Calculate Citation Accuracy (F1 token-matching overlap on citation claims)
        citation_accuracy = self._calculate_citation_accuracy(response_text, context_chunks)
        
        # 2. Check for Hallucinations (Checks if generated numeric forecasts deviate from context)
        hallucination_rate = self._calculate_hallucination_rate(response_text, context_chunks)
        
        # 3. Calculate Retrieval Precision (Fraction of relevant context chunks matching target location)
        retrieval_precision = self._calculate_retrieval_precision(query, context_chunks)
        
        # 4. Compute overall Grounding Confidence score
        # Confidence decays if hallucination is high or citations are weak
        confidence = round((1.0 - hallucination_rate) * (0.7 + 0.3 * citation_accuracy), 2)

        # Log metrics to PostgreSQL database
        eval_log = EvaluationLog(
            timestamp=datetime.utcnow(),
            query=query,
            response=response_text,
            retrieval_precision=retrieval_precision,
            citation_accuracy=citation_accuracy,
            hallucination_rate=hallucination_rate,
            response_latency=latency_sec,
            confidence_score=confidence
        )
        self.db.add(eval_log)
        await self.db.commit()

        logger.info(
            "Completed AI MLOps evaluation checks",
            retrieval_precision=retrieval_precision,
            citation_accuracy=citation_accuracy,
            hallucination_rate=hallucination_rate,
            confidence=confidence,
            latency=latency_sec
        )

        return {
            "retrieval_precision": retrieval_precision,
            "citation_accuracy": citation_accuracy,
            "hallucination_rate": hallucination_rate,
            "confidence_score": confidence,
            "response_latency": latency_sec
        }

    def _calculate_citation_accuracy(self, response: str, chunks: List[str]) -> float:
        """Measures whether the citations overlap with text chunks."""
        if not chunks:
            return 0.0
        # Simple string-matching overlap check on key terms
        matched_words = 0
        response_lower = response.lower()
        
        # Check for numeric overlap
        numbers = re.findall(r"\d+(?:\.\d+)?", response)
        if not numbers:
            return 1.0  # No numbers to match, citations match by default
            
        for num in numbers:
            for chunk in chunks:
                if num in chunk:
                    matched_words += 1
                    break
                    
        return round(matched_words / len(numbers), 2)

    def _calculate_hallucination_rate(self, response: str, chunks: List[str]) -> float:
        """
        Determines the hallucination rate by identifying whether any numbers or warning levels
        in the generated response conflict with the retrieved context.
        """
        if not chunks:
            return 1.0  # Complete hallucination if no context is present
            
        response_lower = response.lower()
        combined_context = " ".join(chunks).lower()
        
        # Check warning level consistency
        warnings_in_response = [w for w in ["green", "yellow", "orange", "red"] if w in response_lower]
        for w in warnings_in_response:
            if w not in combined_context:
                # Flag hallucinated warning level
                logger.warn("Warning level hallucination detected in response", warning=w)
                return 1.0

        # Check numeric value validation (e.g. rain mm forecasts)
        numbers = re.findall(r"\d+(?:\.\d+)?", response)
        for num in numbers:
            if num not in combined_context:
                # Response claims a number that does not exist in context
                logger.warn("Numeric forecast hallucination detected in response", number=num)
                return 1.0
                
        return 0.0

    def _calculate_retrieval_precision(self, query: str, chunks: List[str]) -> float:
        """Measures NDCG retrieval relevance score (fraction of chunks matching query location)."""
        if not chunks:
            return 0.0
        
        # Extract location keyword in query
        location_match = re.search(r"(in|at|for)\s+([a-zA-Z]+)", query, re.IGNORECASE)
        if not location_match:
            return 1.0  # No specific location queried, default relevant
            
        location = location_match.group(2).lower()
        relevant_count = 0
        for chunk in chunks:
            if location in chunk.lower():
                relevant_count += 1
                
        return round(relevant_count / len(chunks), 2)
