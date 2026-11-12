from typing import Optional
from fastapi import APIRouter, Query
from app.services.stream_manager import video_service
from app.schemas.status import StreamStatusResponse

router = APIRouter(tags=["Playback Control"])

@router.post(
    "/api/playback/toggle",
    response_model=StreamStatusResponse,
    summary="Toggle Play / Pause",
    description="Toggles playback pause state."
)
def toggle_playback():
    video_service.toggle_pause()
    return video_service.get_status()

@router.post(
    "/api/playback/restart",
    response_model=StreamStatusResponse,
    summary="Restart Video",
    description="Rewinds video playback to the very beginning (frame 0) and resumes playback."
)
def restart_playback():
    video_service.seek_frame(0)
    video_service.set_pause(False)
    return video_service.get_status()

@router.post(
    "/api/playback/loop",
    response_model=StreamStatusResponse,
    summary="Toggle Loop Mode",
    description="Toggles video looping on or off."
)
def toggle_loop(enabled: Optional[bool] = Query(None, description="Optional explicit boolean state")):
    if enabled is not None:
        video_service.set_loop(enabled)
    else:
        video_service.toggle_loop()
    return video_service.get_status()

@router.post(
    "/api/playback/seek",
    response_model=StreamStatusResponse,
    summary="Seek Video Position",
    description="Seeks by absolute frame index or relative time offset in seconds."
)
def seek_playback(
    frame: Optional[int] = Query(None, description="Absolute frame number"),
    offset: Optional[float] = Query(None, description="Relative time offset in seconds")
):
    if frame is not None:
        video_service.seek_frame(frame)
    elif offset is not None:
        video_service.seek_offset(offset)
    return video_service.get_status()

@router.post(
    "/api/playback/seek_offset",
    response_model=StreamStatusResponse,
    summary="Seek Video Offset",
    description="Seeks forward or backward by seconds."
)
def seek_offset_playback(
    seconds: Optional[float] = Query(None, description="Relative time offset in seconds"),
    offset: Optional[float] = Query(None, description="Relative time offset alias")
):
    val = seconds if seconds is not None else (offset or 0.0)
    video_service.seek_offset(val)
    return video_service.get_status()

@router.post(
    "/api/playback/step",
    response_model=StreamStatusResponse,
    summary="Step Frame-by-Frame",
    description="Pauses playback and steps forward (+1) or backward (-1) frames."
)
def step_playback(
    delta: Optional[int] = Query(None, description="Frame step delta (-1 or +1)"),
    delta_frames: Optional[int] = Query(None, description="Frame step delta alias")
):
    step_val = delta_frames if delta_frames is not None else (delta if delta is not None else 1)
    video_service.set_pause(True)
    video_service.step(step_val)
    return video_service.get_status()

@router.post(
    "/api/playback/reset",
    response_model=StreamStatusResponse,
    summary="Reset Video & Counters",
    description="Resets all cylinder counts and rewinds video to beginning."
)
def reset_playback():
    video_service.reset()
    return video_service.get_status()
