from typing import Optional
from pydantic import BaseModel, Field, field_validator


class NormalizedWeatherPayload(BaseModel):
    """Pydantic model validating unified weather forecast schema records."""
    district_code: str = Field(..., description="Local Government Directory (LGD) district code")
    district_name: str = Field(..., description="English name of the target district")
    rainfall_mm: float = Field(..., ge=0.0, description="Forecast rainfall amount in millimeters")
    temp_c: Optional[float] = Field(None, ge=-50.0, le=60.0, description="Average temperature in Celsius")
    wind_kph: Optional[float] = Field(None, ge=0.0, le=300.0, description="Peak wind speed in km/h")
    warning_level: str = Field("Green", description="IMD color warning level: Green, Yellow, Orange, Red")

    @field_validator("warning_level")
    @classmethod
    def validate_warning_level(cls, value: str) -> str:
        valid_warnings = {"Green", "Yellow", "Orange", "Red"}
        cap_val = value.capitalize()
        if cap_val not in valid_warnings:
            raise ValueError(f"Invalid warning level: {value}. Must be one of {valid_warnings}")
        return cap_val
