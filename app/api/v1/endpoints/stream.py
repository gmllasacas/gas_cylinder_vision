from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from app.services.stream_manager import video_service
from app.schemas.status import StreamStatusResponse

router = APIRouter(tags=["Stream & Telemetry"])

@router.get(
    "/video_feed",
    summary="Real-time MJPEG Video Feed",
    description="Streams processed video frames as multipart/x-mixed-replace MJPEG stream."
)
def get_video_feed():
    return StreamingResponse(
        video_service.generate_frames(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )

@router.get(
    "/api/status",
    response_model=StreamStatusResponse,
    summary="Get System Status & Telemetry",
    description="Returns real-time stream status, AI inference latency, frame rates, and cylinder counts."
)
def get_stream_status():
    return video_service.get_status()
