from typing import List, Optional
from pydantic import BaseModel, Field

class InconsistencyAlertResponse(BaseModel):
    """Schema representing a single inconsistency / anomaly alert record."""
    id: int = Field(..., description="Unique alert ID")
    timestamp: str = Field(..., description="ISO 8601 Timestamp of detection")
    date: str = Field(..., description="Date partition string YYYY-MM-DD")
    in_count: int = Field(..., description="Number of tanks that entered (IN) in the batch")
    out_count: int = Field(..., description="Number of tanks that exited (OUT) in the batch")
    discrepancy: int = Field(..., description="Difference (out_count - in_count)")
    message: str = Field(..., description="Human-readable notification description")
    severity: str = Field(default="WARNING", description="Severity level: WARNING or ERROR")
    source_id: Optional[str] = Field(None, description="Video source or camera identifier")
    acknowledged: int = Field(default=0, description="1 if dismissed/read, 0 otherwise")

class AlertListResponse(BaseModel):
    """Schema representing a collection of inconsistency alerts."""
    total: int = Field(..., description="Total number of alerts returned")
    unread_count: int = Field(..., description="Total unread/active alerts")
    alerts: List[InconsistencyAlertResponse] = Field(..., description="List of alert items")
