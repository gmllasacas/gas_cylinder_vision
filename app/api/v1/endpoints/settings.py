from typing import Optional
from fastapi import APIRouter, Query
from app.services.stream_manager import video_service
from app.schemas.status import StreamStatusResponse

router = APIRouter(tags=["Runtime Settings"])

@router.get(
    "/api/config",
    summary="Get Configuration",
    description="Returns the runtime configuration parameters."
)
def get_config():
    return video_service.config

@router.post(
    "/api/settings/conf",
    response_model=StreamStatusResponse,
    summary="Set Detection Confidence",
    description="Updates the YOLO detection confidence threshold."
)
def set_confidence(value: float = Query(..., ge=0.01, le=0.99, description="Confidence threshold")):
    video_service.set_conf(value)
    return video_service.get_status()

@router.post(
    "/api/settings/confidence",
    response_model=StreamStatusResponse,
    summary="Set Detection Confidence (Alias)",
    description="Updates the YOLO detection confidence threshold."
)
def set_confidence_alias(value: float = Query(..., ge=0.01, le=0.99, description="Confidence threshold")):
    video_service.set_conf(value)
    return video_service.get_status()

@router.post(
    "/api/settings/speed",
    response_model=StreamStatusResponse,
    summary="Set Playback Speed",
    description="Updates the video playback speed multiplier."
)
def set_playback_speed(value: float = Query(..., ge=0.25, le=10.0, description="Speed multiplier")):
    video_service.set_playback_speed(value)
    return video_service.get_status()

@router.post(
    "/api/settings/lang",
    response_model=StreamStatusResponse,
    summary="Set Active Language",
    description="Switches the UI and visual overlay language."
)
def set_language(value: str = Query("en", description="Language code (e.g. en, es)")):
    video_service.set_lang(value)
    return video_service.get_status()

@router.post(
    "/api/settings/language",
    response_model=StreamStatusResponse,
    summary="Set Active Language (Alias)",
    description="Switches the UI and visual overlay language."
)
def set_language_alias(
    value: Optional[str] = Query(None, description="Language code"),
    lang: Optional[str] = Query(None, description="Language code alias")
):
    code = lang or value or "en"
    video_service.set_lang(code)
    return video_service.get_status()

@router.post(
    "/api/settings/debug",
    response_model=StreamStatusResponse,
    summary="Toggle Debug Overlays",
    description="Enables or disables visual overlays, bounding boxes, and counting lines."
)
def toggle_debug_mode(enabled: Optional[bool] = Query(None, description="Optional explicit boolean state")):
    if enabled is not None:
        video_service.set_debug_mode(enabled)
    else:
        video_service.toggle_debug_mode()
    return video_service.get_status()
