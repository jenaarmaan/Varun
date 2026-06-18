import os
import json
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional
from pydantic import ValidationError
import structlog

from app.core.config import settings
from app.schemas.forecast import NormalizedWeatherPayload

logger = structlog.get_logger()


class DataQualityService:
    """Service validating weather records and enforcing source priorities/quarantines."""

    def __init__(self):
        self.quarantine_dir = settings.STORAGE_QUARANTINE_DIR
        self.source_priority = settings.SOURCE_PRIORITY

    def validate_and_normalize(self, raw_record: Dict[str, Any]) -> Optional[NormalizedWeatherPayload]:
        """Validates payload schema. Quarantines invalid records."""
        try:
            # Validate against Pydantic schema
            validated = NormalizedWeatherPayload(**raw_record)
            return validated
        except ValidationError as e:
            logger.warn("DQS Validation failed. Routing to quarantine.", error=str(e), record=raw_record)
            self._quarantine_record(raw_record, reason=f"Validation Error: {str(e)}")
            return None

    def enforce_precedence(self, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Groups records by district_code and selects the highest priority source record.
        Source Priority: IMD = 1 (Highest), OpenMeteo = 2
        """
        grouped_records: Dict[str, Dict[str, Any]] = {}

        for record in records:
            dist_code = record.get("district_code")
            source = record.get("source", "OpenMeteo")  # Default to lower priority

            if not dist_code:
                logger.warn("Record missing district code, skipping", record=record)
                continue

            # If no record exists for the district yet, insert
            if dist_code not in grouped_records:
                grouped_records[dist_code] = record
                continue

            # If record exists, compare source priorities (Lower value = higher priority)
            existing_record = grouped_records[dist_code]
            existing_source = existing_record.get("source", "OpenMeteo")

            priority_new = self.source_priority.get(source, 99)
            priority_existing = self.source_priority.get(existing_source, 99)

            if priority_new < priority_existing:
                logger.info(
                    "Overriding weather record due to higher source priority",
                    district=dist_code,
                    old_source=existing_source,
                    new_source=source
                )
                grouped_records[dist_code] = record

        return list(grouped_records.values())

    def check_duplicate_bulletin(
        self,
        new_issue_time: datetime,
        source: str,
        existing_records: List[datetime]
    ) -> bool:
        """Checks if a bulletin from the same source and issue time is already ingested."""
        # Simple timestamp check
        for issue_time in existing_records:
            if issue_time == new_issue_time:
                logger.warn("Duplicate weather bulletin detected", source=source, issue_time=new_issue_time)
                return True
        return False

    def _quarantine_record(self, raw_record: Dict[str, Any], reason: str):
        """Saves invalid records into the quarantine folder for auditing."""
        if not os.path.exists(self.quarantine_dir):
            os.makedirs(self.quarantine_dir, exist_ok=True)

        filename = f"quarantine_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}.json"
        filepath = os.path.join(self.quarantine_dir, filename)

        payload = {
            "quarantined_at": datetime.utcnow().isoformat(),
            "reason": reason,
            "raw_payload": raw_record
        }

        try:
            with open(filepath, "w") as f:
                json.dump(payload, f, indent=2)
            logger.info("Record quarantined successfully", path=filepath)
        except Exception as e:
            logger.error("Failed to write to quarantine file", error=str(e))
