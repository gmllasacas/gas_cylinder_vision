from typing import Optional
from pydantic import BaseModel, Field

class SeekRequest(BaseModel):
    """Parameters for seeking video playback."""
    frame: Optional[int] = Field(None, ge=0, description="Target absolute frame index")
    offset: Optional[float] = Field(None, description="Relative time offset in seconds (+5, -5)")

class StepRequest(BaseModel):
    """Parameters for stepping video frame-by-frame."""
    delta: int = Field(default=-1, description="Frame step delta (-1 or +1)")
