from fastapi import APIRouter, Query, HTTPException, Depends
from fastapi.responses import JSONResponse
from app.services.stream_manager import VideoStreamService, video_service
from app.api.deps import get_video_service
from app.schemas.source import VideoSourcesResponse, SelectSourceResponse

router = APIRouter(tags=["Video Sources"])

@router.get(
    "/api/videos",
    response_model=VideoSourcesResponse,
    summary="List Available Video Sources",
    description="Returns available local video files and configured RTSP camera streams."
)
def get_available_sources(service: VideoStreamService = Depends(get_video_service)):
    return {
        "sources": service.get_available_sources(),
        "videos": service.get_available_videos(),
        "current_video": service.current_video_name,
        "current_source_id": service.current_source_id,
        "is_live": service.is_live_stream
    }

@router.post(
    "/api/videos/select",
    response_model=SelectSourceResponse,
    summary="Select Active Video Source",
    description="Switches the active video source to a specific video file or live camera."
)
def select_video_source(
    filename: str = Query(..., description="Target video filename or 'live_camera'"),
    service: VideoStreamService = Depends(get_video_service)
):
    success = service.change_source(filename)
    if not success:
        return JSONResponse(
            status_code=400,
            content={"status": "error", "message": f"Could not load source '{filename}'"}
        )
    return {"status": "success", "message": f"Source changed to {filename}"}
