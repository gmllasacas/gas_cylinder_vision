from typing import List, Literal
from pydantic import BaseModel, Field

class SourceItem(BaseModel):
    """Represents an available camera or video file stream source."""
    type: Literal["camera", "file"] = Field(..., description="Source type")
    id: str = Field(..., description="Unique source identifier")
    name: str = Field(..., description="Human-readable label for UI selection")
    url: str = Field(..., description="Source endpoint URL or filename")

class VideoSourcesResponse(BaseModel):
    """Response containing all selectable video sources and current selection."""
    sources: List[SourceItem] = Field(default_factory=list, description="Available sources list")
    videos: List[str] = Field(default_factory=list, description="Available video filenames")
    current_video: str = Field(..., description="Current active video or camera title")
    current_source_id: str = Field(..., description="Current active source identifier")
    is_live: bool = Field(..., description="True if active source is a live camera")

class SelectSourceResponse(BaseModel):
    """Response when a video source is selected."""
    status: Literal["success", "error"] = Field(..., description="Operation status")
    message: str = Field(default="", description="Optional message or error explanation")
