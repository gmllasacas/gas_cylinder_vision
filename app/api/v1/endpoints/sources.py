from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import JSONResponse
from app.services.stream_manager import video_service
from app.schemas.source import VideoSourcesResponse, SelectSourceResponse

router = APIRouter(tags=["Video Sources"])

@router.get(
    "/api/videos",
    response_model=VideoSourcesResponse,
    summary="List Available Video Sources",
    description="Returns available local video files and configured RTSP camera streams."
)
def get_available_sources():
    return {
        "sources": video_service.get_available_sources(),
        "videos": video_service.get_available_videos(),
        "current_video": video_service.current_video_name,
        "current_source_id": video_service.current_source_id,
        "is_live": video_service.is_live_stream
    }

@router.post(
    "/api/videos/select",
    response_model=SelectSourceResponse,
    summary="Select Active Video Source",
    description="Switches the active video source to a specific video file or live camera."
)
def select_video_source(filename: str = Query(..., description="Target video filename or 'live_camera'")):
    success = video_service.change_source(filename)
    if not success:
        return JSONResponse(
            status_code=400,
            content={"status": "error", "message": f"Could not load source '{filename}'"}
        )
    return {"status": "success", "message": f"Source changed to {filename}"}
