import json
import asyncio
import threading
from typing import Dict
from fastapi import APIRouter, Request, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from app.services.stream_manager import VideoStreamService, video_service
from app.api.deps import get_video_service
from app.schemas.status import StreamStatusResponse
from app.core.logging import logger

router = APIRouter(tags=["Stream & Telemetry"])

# In-memory concurrent stream limiter per client IP and global server cap
_active_streams: Dict[str, int] = {}
_stream_lock = threading.Lock()
MAX_CONCURRENT_STREAMS_PER_IP = 3
MAX_TOTAL_CONCURRENT_STREAMS = 10

def reset_stream_connections():
    """Resets the active stream connection tracking (useful for testing)."""
    with _stream_lock:
        _active_streams.clear()

def _acquire_stream_slot(client_ip: str) -> None:
    with _stream_lock:
        ip_count = _active_streams.get(client_ip, 0)
        total_count = sum(_active_streams.values())

        if ip_count >= MAX_CONCURRENT_STREAMS_PER_IP:
            logger.warning(
                f"Stream rate limit exceeded: IP {client_ip} has {ip_count} "
                f"active video streams (max: {MAX_CONCURRENT_STREAMS_PER_IP})"
            )
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many concurrent video streams from this IP address.",
                headers={"Retry-After": "10"}
            )

        if total_count >= MAX_TOTAL_CONCURRENT_STREAMS:
            logger.warning(
                f"Global stream limit reached: {total_count} active video streams "
                f"(max: {MAX_TOTAL_CONCURRENT_STREAMS})"
            )
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Server video stream capacity reached. Please try again later.",
                headers={"Retry-After": "10"}
            )

        _active_streams[client_ip] = ip_count + 1

def _release_stream_slot(client_ip: str) -> None:
    with _stream_lock:
        if client_ip in _active_streams:
            _active_streams[client_ip] -= 1
            if _active_streams[client_ip] <= 0:
                del _active_streams[client_ip]

async def mjpeg_frame_generator(request: Request, service: VideoStreamService, client_ip: str):
    """Yields multipart MJPEG frame chunks via event notification, eliminating busy-polling loops."""
    last_frame_id = -1
    slot_released = False
    try:
        while service.running:
            if await request.is_disconnected():
                break
            # Block asynchronously on frame production condition instead of polling sleep
            has_new = await asyncio.to_thread(service.wait_for_frame, last_frame_id, 0.25)
            if has_new and service.frame_id != last_frame_id:
                last_frame_id = service.frame_id
                frame_data = service.last_frame_bytes
                if frame_data is not None:
                    yield (
                        b'--frame\r\n'
                        b'Content-Type: image/jpeg\r\n\r\n' + frame_data + b'\r\n'
                    )
    except (asyncio.CancelledError, GeneratorExit):
        pass
    finally:
        if not slot_released:
            _release_stream_slot(client_ip)
            slot_released = True

@router.get(
    "/video_feed",
    summary="Real-time MJPEG Video Feed",
    description="Streams processed video frames as multipart/x-mixed-replace MJPEG stream."
)
async def get_video_feed(request: Request, service: VideoStreamService = Depends(get_video_service)):
    client_ip = request.client.host if request.client else "unknown"
    _acquire_stream_slot(client_ip)
    return StreamingResponse(
        mjpeg_frame_generator(request, service, client_ip),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )

@router.get(
    "/api/status",
    response_model=StreamStatusResponse,
    summary="Get System Status & Telemetry",
    description="Returns real-time stream status, AI inference latency, frame rates, and cylinder counts."
)
def get_stream_status(service: VideoStreamService = Depends(get_video_service)):
    return service.get_status()

@router.get(
    "/api/status/stream",
    summary="Real-time SSE Telemetry Stream",
    description="Streams telemetry status as Server-Sent Events (SSE) to replace high-frequency polling."
)
async def get_status_stream(request: Request, service: VideoStreamService = Depends(get_video_service)):
    async def event_generator():
        last_frame_id = -1
        try:
            while service.running:
                if await request.is_disconnected():
                    break
                has_new = await asyncio.to_thread(service.wait_for_frame, last_frame_id, 0.5)
                if has_new and service.frame_id != last_frame_id:
                    last_frame_id = service.frame_id
                    status_data = service.get_status()
                    yield f"data: {json.dumps(status_data)}\n\n"
        except (asyncio.CancelledError, GeneratorExit):
            pass

    return StreamingResponse(event_generator(), media_type="text/event-stream")
