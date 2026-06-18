import re
import os
from typing import List, Dict, Any, Optional
import pdfplumber
import structlog

logger = structlog.get_logger()


class MeteorologicalPDFParser:
    """
    Multi-tier parsing engine for IMD daily forecast PDF bulletins.
    Tier 1: Template regex parsing
    Tier 2: LLM-assisted layout parsing (Gemini)
    Tier 3: OCR fallback
    """

    def __init__(self):
        # Sample regex matches for standard district rain bulletin layouts
        self.district_pattern = re.compile(
            r"(District|Dist|Location):\s*(?P<name>[a-zA-Z\s]+)\s*,\s*(Rainfall|Rain):\s*(?P<rain>\d+(\.\d+)?)\s*mm\s*,\s*(Warning|Alert):\s*(?P<warning>Green|Yellow|Orange|Red)",
            re.IGNORECASE
        )

    def parse(self, file_path: str) -> Dict[str, Any]:
        """Runs the multi-tier extraction pipeline on the PDF file."""
        logger.info("Starting PDF parsing pipeline", file=file_path)
        
        # Verify file exists
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"PDF file not found at {file_path}")

        # Try Tier 1: Template Parsing
        try:
            records = self._parse_tier1_template(file_path)
            if records:
                logger.info("Tier 1 template parsing succeeded", records_count=len(records))
                return {
                    "status": "success",
                    "tier": 1,
                    "records": records,
                    "history": [{"step": "template_parsing", "status": "success"}]
                }
        except Exception as e:
            logger.warn("Tier 1 template parsing failed", error=str(e))

        # Try Tier 2: LLM-Assisted Layout Parsing (Mocked for testing, integrated with Gemini)
        try:
            records = self._parse_tier2_llm(file_path)
            if records:
                logger.info("Tier 2 LLM layout parsing succeeded", records_count=len(records))
                return {
                    "status": "success",
                    "tier": 2,
                    "records": records,
                    "history": [
                        {"step": "template_parsing", "status": "failed"},
                        {"step": "llm_layout_parsing", "status": "success"}
                    ]
                }
        except Exception as e:
            logger.warn("Tier 2 LLM layout parsing failed", error=str(e))

        # Try Tier 3: OCR Fallback (Mocked for testing, converts image pages to string)
        try:
            records = self._parse_tier3_ocr(file_path)
            if records:
                logger.info("Tier 3 OCR parsing succeeded", records_count=len(records))
                return {
                    "status": "success",
                    "tier": 3,
                    "records": records,
                    "history": [
                        {"step": "template_parsing", "status": "failed"},
                        {"step": "llm_layout_parsing", "status": "failed"},
                        {"step": "ocr_parsing", "status": "success"}
                    ]
                }
        except Exception as e:
            logger.error("Tier 3 OCR parsing failed", error=str(e))

        # All tiers failed
        return {
            "status": "failed",
            "tier": 0,
            "records": [],
            "history": [
                {"step": "template_parsing", "status": "failed"},
                {"step": "llm_layout_parsing", "status": "failed"},
                {"step": "ocr_parsing", "status": "failed"}
            ]
        }

    def _parse_tier1_template(self, file_path: str) -> List[Dict[str, Any]]:
        """Extracts text page-by-page and runs standard regex matching."""
        extracted_records = []
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if not text:
                    continue
                
                # Check line by line
                for line in text.split("\n"):
                    match = self.district_pattern.search(line)
                    if match:
                        data = match.groupdict()
                        extracted_records.append({
                            "district_name": data["name"].strip(),
                            "rainfall_mm": float(data["rain"]),
                            "warning_level": data["warning"].capitalize(),
                            "temp_c": None,  # Optional placeholders
                            "wind_kph": None
                        })
        return extracted_records

    def _parse_tier2_llm(self, file_path: str) -> Optional[List[Dict[str, Any]]]:
        """
        Placeholder representing Gemini layout-aware extraction.
        Will trigger Vertex AI file parsing for unstructured tables.
        """
        # In a real environment, we send text or PDF pages to Gemini
        # For the mock/MVP execution, we fallback if template worked or return empty
        return None

    def _parse_tier3_ocr(self, file_path: str) -> Optional[List[Dict[str, Any]]]:
        """Placeholder for OCR fallback parsing."""
        return None
