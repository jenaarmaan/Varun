import httpx
from typing import Dict, Any, Optional
import structlog

logger = structlog.get_logger()


class OpenMeteoClient:
    """Client to query Open-Meteo REST API for gridded weather forecasts."""

    def __init__(self):
        self.base_url = "https://api.open-meteo.com/v1/forecast"

    async def fetch_forecast(self, lat: float, lon: float) -> Optional[Dict[str, Any]]:
        """Queries hourly forecast for rain, temperature, and wind speed."""
        params = {
            "latitude": lat,
            "longitude": lon,
            "hourly": "rain,temperature_2m,wind_speed_10m",
            "forecast_days": 1,
            "timezone": "auto"
        }
        
        logger.info("Querying Open-Meteo API", latitude=lat, longitude=lon)
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.get(self.base_url, params=params)
                if response.status_code == 200:
                    return response.json()
                else:
                    logger.error(
                        "Open-Meteo API returned non-200 status",
                        status_code=response.status_code,
                        response=response.text
                    )
            except httpx.RequestError as e:
                logger.error("HTTP request error to Open-Meteo API", error=str(e))
        return None

    def normalize_forecast(
        self,
        api_data: Dict[str, Any],
        district_name: str,
        district_code: str
    ) -> Dict[str, Any]:
        """Normalizes Open-Meteo JSON response into the unified forecast payload schema."""
        hourly = api_data.get("hourly", {})
        rains = hourly.get("rain", [])
        temps = hourly.get("temperature_2m", [])
        winds = hourly.get("wind_speed_10m", [])

        # Sum total rainfall forecast, calculate avg temperature and peak wind speed
        total_rain = sum(rains) if rains else 0.0
        avg_temp = sum(temps) / len(temps) if temps else None
        max_wind = max(winds) if winds else None

        # Determine warning level based on Open-Meteo rain thresholds
        warning_level = "Green"
        if total_rain > 200.0:
            warning_level = "Red"
        elif total_rain > 115.0:
            warning_level = "Orange"
        elif total_rain > 64.0:
            warning_level = "Yellow"

        return {
            "district_code": district_code,
            "district_name": district_name,
            "rainfall_mm": round(total_rain, 2),
            "temp_c": round(avg_temp, 2) if avg_temp is not None else None,
            "wind_kph": round(max_wind, 2) if max_wind is not None else None,
            "warning_level": warning_level
        }
ZOOM_FACTOR = 1.0
