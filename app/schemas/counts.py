from typing import List, Optional
from pydantic import BaseModel, Field

class DailyCountItem(BaseModel):
    """Daily count statistics item."""
    date: str = Field(..., description="Date in YYYY-MM-DD format")
    in_count: int = Field(..., description="Total inbound cylinder count (downwards)")
    out_count: int = Field(..., description="Total outbound cylinder count (upwards)")
    net_count: int = Field(..., description="Net cylinder count (IN - OUT)")
    created_at: Optional[str] = Field(None, description="ISO timestamp when record was first created")
    updated_at: Optional[str] = Field(None, description="ISO timestamp of last count update")

class DailyCountResponse(BaseModel):
    """Response containing a single daily count record."""
    status: str = Field("success", description="Status string")
    data: DailyCountItem = Field(..., description="Daily count record")

class DailyCountHistoryResponse(BaseModel):
    """Response containing historical daily count records."""
    status: str = Field("success", description="Status string")
    total: int = Field(..., description="Number of daily records returned")
    history: List[DailyCountItem] = Field(..., description="List of historical daily records")

class CountEventItem(BaseModel):
    """Single cylinder crossing audit log event."""
    id: int = Field(..., description="Unique event identifier")
    timestamp: str = Field(..., description="ISO timestamp of crossing")
    date: str = Field(..., description="Date in YYYY-MM-DD format")
    direction: str = Field(..., description="Crossing direction: IN or OUT")
    track_id: Optional[int] = Field(None, description="YOLO tracking object ID")
    source_id: Optional[str] = Field(None, description="Video filename or camera ID")
    frame_number: Optional[int] = Field(None, description="Video frame number at time of event")

class CountEventsResponse(BaseModel):
    """Response containing list of recent crossing events."""
    status: str = Field("success", description="Status string")
    total: int = Field(..., description="Number of events returned")
    events: List[CountEventItem] = Field(..., description="List of recent crossing events")

class ResetCountResponse(BaseModel):
    """Response returned when resetting a daily count."""
    status: str = Field("success", description="Status string")
    message: str = Field(..., description="Status message")
    data: DailyCountItem = Field(..., description="Reset daily count record")

