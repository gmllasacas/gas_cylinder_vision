from typing import Optional
from fastapi import APIRouter, Query, Depends
from app.db.repository import DailyCountRepository
from app.services.stream_manager import VideoStreamService
from app.api.deps import get_db, get_video_service
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
    all_dates: bool = Query(False, description="If true, retrieves alerts across all historical dates"),
    repo: DailyCountRepository = Depends(get_db),
    service: VideoStreamService = Depends(get_video_service)
):
    date_val = None if all_dates else (target_date or repo._today_str())
    alerts_raw = repo.get_inconsistency_alerts(
        limit=limit,
        target_date=date_val,
        unread_only=unread_only
    )
    items = [InconsistencyAlertResponse(**a) for a in alerts_raw]
    return AlertListResponse(
        total=len(items),
        unread_count=service.anomaly_detector.unread_alerts_count,
        alerts=items
    )

@router.post(
    "/clear",
    summary="Clear / Acknowledge Inconsistency Alerts",
    description="Clears unread alert state and removes historical anomaly alerts."
)
def clear_alerts(
    target_date: Optional[str] = Query(None, description="Optional date filter to clear only specific date"),
    repo: DailyCountRepository = Depends(get_db),
    service: VideoStreamService = Depends(get_video_service)
):
    cleared = repo.clear_inconsistency_alerts(target_date=target_date)
    service.anomaly_detector.latest_alert = None
    service.anomaly_detector._today_alerts_count = 0
    service.anomaly_detector._reset_batch()
    return {
        "success": True,
        "cleared_count": cleared,
        "message": f"Successfully cleared {cleared} alert records."
    }
