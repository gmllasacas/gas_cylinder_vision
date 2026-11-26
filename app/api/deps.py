from fastapi import Request
from app.db import db_repo, DailyCountRepository
from app.services.stream_manager import VideoStreamService, video_service

def get_db(request: Request) -> DailyCountRepository:
    """Dependency provider for DailyCountRepository, preferring app.state if available."""
    if hasattr(request, "app") and hasattr(request.app.state, "db_repo"):
        return request.app.state.db_repo
    return db_repo

def get_video_service(request: Request) -> VideoStreamService:
    """Dependency provider for VideoStreamService, preferring app.state if available."""
    if hasattr(request, "app") and hasattr(request.app.state, "video_service"):
        return request.app.state.video_service
    return video_service
