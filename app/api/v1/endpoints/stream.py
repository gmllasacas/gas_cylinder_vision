import asyncio
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from app.services.stream_manager import video_service
from app.schemas.status import StreamStatusResponse

router = APIRouter(tags=["Stream & Telemetry"])

async def mjpeg_frame_generator(request: Request):
    """Yields multipart MJPEG frame chunks, gracefully handling client disconnection and server shutdown."""
    last_sent = None
    try:
        while video_service.running:
            if await request.is_disconnected():
                break
            frame_data = video_service.last_frame_bytes
            if frame_data is not None and frame_data is not last_sent:
                last_sent = frame_data
                yield (
                    b'--frame\r\n'
                    b'Content-Type: image/jpeg\r\n\r\n' + frame_data + b'\r\n'
                )
            await asyncio.sleep(0.015)
    except (asyncio.CancelledError, GeneratorExit):
        pass

@router.get(
    "/video_feed",
    summary="Real-time MJPEG Video Feed",
    description="Streams processed video frames as multipart/x-mixed-replace MJPEG stream."
)
async def get_video_feed(request: Request):
    return StreamingResponse(
        mjpeg_frame_generator(request),
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
