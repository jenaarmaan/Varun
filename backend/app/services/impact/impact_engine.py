import structlog

logger = structlog.get_logger()


class ImpactPredictionEngine:
    """Calculates weighted flood risk score based on weather and spatial vulnerabilities."""

    def calculate_flood_risk(
        self,
        rainfall_mm: float,
        elevation_metric: float = 0.5,     # 0 (high elevation) to 1 (low-lying valley/coastal delta)
        river_proximity: float = 0.5,      # 0 (far from rivers) to 1 (immediate border)
        soil_saturation: float = 0.5       # 0 (dry soil) to 1 (fully saturated)
    ) -> float:
        """
        Computes weighted score:
        Score = (0.4 * RainFactor) + (0.3 * Elevation) + (0.2 * Proximity) + (0.1 * Saturation)
        """
        # Map rainfall to a normalized 0-1 factor
        if rainfall_mm >= 204.5:
            rain_factor = 1.0  # Extremely Heavy Rain
        elif rainfall_mm >= 115.6:
            rain_factor = 0.8  # Very Heavy Rain
        elif rainfall_mm >= 64.5:
            rain_factor = 0.5  # Heavy Rain
        elif rainfall_mm >= 15.0:
            rain_factor = 0.2  # Moderate Rain
        else:
            rain_factor = 0.0  # Light/No Rain

        # Calculate weighted sum
        score = (
            (0.4 * rain_factor) +
            (0.3 * elevation_metric) +
            (0.2 * river_proximity) +
            (0.1 * soil_saturation)
        )
        
        logger.info(
            "Calculated weighted flood risk score",
            rainfall=rainfall_mm,
            rain_factor=rain_factor,
            elevation=elevation_metric,
            proximity=river_proximity,
            saturation=soil_saturation,
            final_score=round(score, 3)
        )
        
        return round(score, 3)
