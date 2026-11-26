from typing import Optional
from fastapi import APIRouter, Query, Depends, Body
from app.services.stream_manager import VideoStreamService, video_service
from app.api.deps import get_video_service
from app.schemas.status import StreamStatusResponse
from app.schemas.playback import SeekRequest, StepRequest

router = APIRouter(tags=["Playback Control"])

@router.post(
    "/api/playback/toggle",
    response_model=StreamStatusResponse,
    summary="Toggle Play / Pause",
    description="Toggles playback pause state."
)
def toggle_playback(service: VideoStreamService = Depends(get_video_service)):
    service.toggle_pause()
    return service.get_status()

@router.post(
    "/api/playback/restart",
    response_model=StreamStatusResponse,
    summary="Restart Video",
    description="Rewinds video playback to the very beginning (frame 0) and resumes playback."
)
def restart_playback(service: VideoStreamService = Depends(get_video_service)):
    service.seek_frame(0)
    service.set_pause(False)
    return service.get_status()

@router.post(
    "/api/playback/loop",
    response_model=StreamStatusResponse,
    summary="Toggle Loop Mode",
    description="Toggles video looping on or off."
)
def toggle_loop(
    enabled: Optional[bool] = Query(None, description="Optional explicit boolean state"),
    service: VideoStreamService = Depends(get_video_service)
):
    if enabled is not None:
        service.set_loop(enabled)
    else:
        service.toggle_loop()
    return service.get_status()

@router.post(
    "/api/playback/seek",
    response_model=StreamStatusResponse,
    summary="Seek Video Position",
    description="Seeks by absolute frame index or relative time offset in seconds via JSON body or query param."
)
def seek_playback(
    payload: Optional[SeekRequest] = Body(None),
    frame: Optional[int] = Query(None, description="Absolute frame number"),
    offset: Optional[float] = Query(None, description="Relative time offset in seconds"),
    service: VideoStreamService = Depends(get_video_service)
):
    target_frame = payload.frame if (payload and payload.frame is not None) else frame
    target_offset = payload.offset if (payload and payload.offset is not None) else offset

    if target_frame is not None:
        service.seek_frame(target_frame)
    elif target_offset is not None:
        service.seek_offset(target_offset)
    return service.get_status()

@router.post(
    "/api/playback/seek_offset",
    response_model=StreamStatusResponse,
    summary="Seek Video Offset",
    description="Seeks forward or backward by seconds."
)
def seek_offset_playback(
    seconds: Optional[float] = Query(None, description="Relative time offset in seconds"),
    offset: Optional[float] = Query(None, description="Relative time offset alias"),
    service: VideoStreamService = Depends(get_video_service)
):
    val = seconds if seconds is not None else (offset or 0.0)
    service.seek_offset(val)
    return service.get_status()

@router.post(
    "/api/playback/step",
    response_model=StreamStatusResponse,
    summary="Step Frame-by-Frame",
    description="Pauses playback and steps forward (+1) or backward (-1) frames via JSON body or query param."
)
def step_playback(
    payload: Optional[StepRequest] = Body(None),
    delta: Optional[int] = Query(None, description="Frame step delta (-1 or +1)"),
    delta_frames: Optional[int] = Query(None, description="Frame step delta alias"),
    service: VideoStreamService = Depends(get_video_service)
):
    if payload is not None and payload.delta is not None:
        step_val = payload.delta
    elif delta_frames is not None:
        step_val = delta_frames
    else:
        step_val = delta if delta is not None else 1

    service.set_pause(True)
    service.step(step_val)
    return service.get_status()

@router.post(
    "/api/playback/reset",
    response_model=StreamStatusResponse,
    summary="Reset Video & Counters",
    description="Resets all cylinder counts and rewinds video to beginning."
)
def reset_playback(service: VideoStreamService = Depends(get_video_service)):
    service.reset()
    return service.get_status()
