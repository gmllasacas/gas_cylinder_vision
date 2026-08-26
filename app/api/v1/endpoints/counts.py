from typing import Optional
from fastapi import APIRouter, Query
from app.db import db_repo
from app.schemas.counts import (
    DailyCountResponse,
    DailyCountHistoryResponse,
    CountEventsResponse,
    ResetCountResponse,
)

router = APIRouter(prefix="/api/counts", tags=["Daily Counts & History"])

@router.get(
    "/today",
    response_model=DailyCountResponse,
    summary="Get Today's Saved Counts",
    description="Returns the aggregated cylinder count saved in SQLite for today."
)
def get_today_counts():
    record = db_repo.get_or_create_daily()
    return {"status": "success", "data": record}

@router.get(
    "/history",
    response_model=DailyCountHistoryResponse,
    summary="Get Historical Daily Counts",
    description="Returns daily count history ordered by date descending."
)
def get_counts_history(
    limit: int = Query(30, ge=1, le=365, description="Number of daily records to return"),
    start_date: Optional[str] = Query(None, description="Start date filter (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date filter (YYYY-MM-DD)")
):
    history = db_repo.get_history(limit=limit, start_date=start_date, end_date=end_date)
    return {"status": "success", "total": len(history), "history": history}

@router.get(
    "/events",
    response_model=CountEventsResponse,
    summary="Get Recent Crossing Events",
    description="Returns individual cylinder crossing audit log events."
)
def get_crossing_events(
    limit: int = Query(50, ge=1, le=500, description="Number of events to return"),
    date: Optional[str] = Query(None, description="Filter events by date (YYYY-MM-DD)")
):
    events = db_repo.get_events(limit=limit, target_date=date)
    return {"status": "success", "total": len(events), "events": events}

@router.post(
    "/reset",
    response_model=ResetCountResponse,
    summary="Reset Daily Count",
    description="Resets the stored counts to 0 for a specific date (defaults to today)."
)
def reset_daily_counts(
    date: Optional[str] = Query(None, description="Date to reset (YYYY-MM-DD), default is today")
):
    record = db_repo.reset_daily_count(target_date=date)
    return {
        "status": "success",
        "message": f"Daily counts reset successfully for {record['date']}",
        "data": record
    }

