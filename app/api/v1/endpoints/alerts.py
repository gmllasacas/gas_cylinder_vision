from typing import Optional
from fastapi import APIRouter, Query
from app.db import db_repo
from app.services.stream_manager import video_service
from app.schemas.alerts import AlertListResponse, InconsistencyAlertResponse

router = APIRouter(prefix="/api/alerts", tags=["Inconsistency & Anomaly Alerts"])

@router.get(
    "",
    response_model=AlertListResponse,
    summary="Get Inconsistency Alerts",
    description="Retrieves a list of detected batch count inconsistencies (e.g. IN vs OUT mismatches) from SQLite."
)
def get_alerts(
    limit: int = Query(50, ge=1, le=500, description="Max alerts to retrieve"),
    target_date: Optional[str] = Query(None, description="Optional filter date (YYYY-MM-DD), default is today"),
    unread_only: bool = Query(False, description="Filter to only unread/unacknowledged alerts"),
    all_dates: bool = Query(False, description="If true, retrieves alerts across all historical dates")
):
    date_val = None if all_dates else (target_date or db_repo._today_str())
    alerts_raw = db_repo.get_inconsistency_alerts(
        limit=limit,
        target_date=date_val,
        unread_only=unread_only
    )
    items = [InconsistencyAlertResponse(**a) for a in alerts_raw]
    return AlertListResponse(
        total=len(items),
        unread_count=video_service.anomaly_detector.unread_alerts_count,
        alerts=items
    )

@router.post(
    "/clear",
    summary="Clear / Acknowledge Inconsistency Alerts",
    description="Clears unread alert state and removes historical anomaly alerts."
)
def clear_alerts(
    target_date: Optional[str] = Query(None, description="Optional date filter to clear only specific date")
):
    cleared = db_repo.clear_inconsistency_alerts(target_date=target_date)
    video_service.anomaly_detector.clear_alerts()
    return {
        "success": True,
        "cleared_count": cleared,
        "message": f"Successfully cleared {cleared} alert records."
    }
