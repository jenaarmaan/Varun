from typing import List
import structlog

logger = structlog.get_logger()


class WeatherDecisionEngine:
    """Weather Decision Engine mapping risk scores to Standard Operating Procedures (SOPs)."""

    def generate_sop_checklist(self, flood_risk_score: float) -> List[str]:
        """Translates risk score to NDMA compliant checklists."""
        logger.info("Generating SOP checklist for risk score", score=flood_risk_score)
        
        checklist = []
        
        # High Risk Level - Red Alert (SOP Checklist)
        if flood_risk_score >= 0.75:
            checklist = [
                "Activate District Emergency Operations Center (DEOC) to 24/7 alert status.",
                "Initiate immediate evacuation plans for identified low-lying coastal/river valley zones.",
                "Pre-position National Disaster Response Force (NDRF) and State SDRF units.",
                "Activate emergency shelters and deploy dry food, water, and medical resources.",
                "Trigger broadcast public warning alerts (SMS/Email/Sirens)."
            ]
        # Moderate Risk Level - Orange Alert (SOP Checklist)
        elif flood_risk_score >= 0.50:
            checklist = [
                "Place emergency response teams (NDRF/SDRF) on 1-hour standby notice.",
                "Direct reservoir managers to closely monitor inflows and prepare controlled discharges.",
                "Issue warnings to coastal fishermen to cease operations immediately.",
                "Conduct checks on critical communication networks and power line backups."
            ]
        # Low Risk Level - Yellow Alert (SOP Checklist)
        elif flood_risk_score >= 0.25:
            checklist = [
                "Monitor district telemetry station data hourly for changes.",
                "Instruct local administrative blocks (Taluks) to inspect flood embankments.",
                "Ensure local community leaders are notified of potential heavy weather anomalies."
            ]
        # Safe Risk Level - Green Alert
        else:
            checklist = [
                "Routine meteorological forecast monitoring active.",
                "No emergency actions required."
            ]
            
        return checklist
