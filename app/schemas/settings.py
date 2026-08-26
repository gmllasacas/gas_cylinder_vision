from typing import Optional, Literal
from pydantic import BaseModel, Field

class ConfidenceUpdateRequest(BaseModel):
    """Payload to update detector confidence threshold."""
    value: float = Field(..., ge=0.01, le=0.99, description="Confidence threshold between 0.01 and 0.99")

class SpeedUpdateRequest(BaseModel):
    """Payload to update playback speed multiplier."""
    value: float = Field(..., ge=0.25, le=10.0, description="Speed multiplier between 0.25 and 10.0")

class LanguageUpdateRequest(BaseModel):
    """Payload to update active UI and overlay language."""
    value: str = Field(default="en", description="Language code (e.g. en, es)")

class DebugToggleRequest(BaseModel):
    """Payload to set or toggle debug overlays."""
    enabled: Optional[bool] = Field(None, description="Explicit boolean state or None to toggle")
