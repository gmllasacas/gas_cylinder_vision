from typing import Optional
from fastapi import APIRouter, Query, Depends, HTTPException, Body
from app.services.stream_manager import VideoStreamService, video_service
from app.api.deps import get_video_service
from app.schemas.status import StreamStatusResponse
from app.schemas.settings import (
    ConfidenceUpdateRequest,
    SpeedUpdateRequest,
    LanguageUpdateRequest,
    DebugToggleRequest
)

router = APIRouter(tags=["Runtime Settings"])

@router.get(
    "/api/config",
    summary="Get Configuration",
    description="Returns the runtime configuration parameters."
)
def get_config(service: VideoStreamService = Depends(get_video_service)):
    return service.config

@router.post(
    "/api/settings/conf",
    response_model=StreamStatusResponse,
    summary="Set Detection Confidence",
    description="Updates the YOLO detection confidence threshold via JSON body or query param."
)
def set_confidence(
    payload: Optional[ConfidenceUpdateRequest] = Body(None),
    value: Optional[float] = Query(None, ge=0.01, le=0.99, description="Confidence threshold"),
    service: VideoStreamService = Depends(get_video_service)
):
    conf_val = payload.value if payload else value
    if conf_val is None:
        raise HTTPException(status_code=400, detail="Missing required confidence value.")
    service.set_conf(conf_val)
    return service.get_status()

@router.post(
    "/api/settings/confidence",
    response_model=StreamStatusResponse,
    summary="Set Detection Confidence (Alias)",
    description="Updates the YOLO detection confidence threshold."
)
def set_confidence_alias(
    payload: Optional[ConfidenceUpdateRequest] = Body(None),
    value: Optional[float] = Query(None, ge=0.01, le=0.99, description="Confidence threshold"),
    service: VideoStreamService = Depends(get_video_service)
):
    return set_confidence(payload=payload, value=value, service=service)

@router.post(
    "/api/settings/speed",
    response_model=StreamStatusResponse,
    summary="Set Playback Speed",
    description="Updates the video playback speed multiplier via JSON body or query param."
)
def set_playback_speed(
    payload: Optional[SpeedUpdateRequest] = Body(None),
    value: Optional[float] = Query(None, ge=0.25, le=10.0, description="Speed multiplier"),
    service: VideoStreamService = Depends(get_video_service)
):
    spd_val = payload.value if payload else value
    if spd_val is None:
        raise HTTPException(status_code=400, detail="Missing required speed value.")
    service.set_playback_speed(spd_val)
    return service.get_status()

@router.post(
    "/api/settings/lang",
    response_model=StreamStatusResponse,
    summary="Set Active Language",
    description="Switches the UI and visual overlay language via JSON body or query param."
)
def set_language(
    payload: Optional[LanguageUpdateRequest] = Body(None),
    value: Optional[str] = Query(None, description="Language code (e.g. en, es)"),
    service: VideoStreamService = Depends(get_video_service)
):
    lang_val = payload.value if payload else (value or "en")
    service.set_lang(lang_val)
    return service.get_status()

@router.post(
    "/api/settings/language",
    response_model=StreamStatusResponse,
    summary="Set Active Language (Alias)",
    description="Switches the UI and visual overlay language."
)
def set_language_alias(
    payload: Optional[LanguageUpdateRequest] = Body(None),
    value: Optional[str] = Query(None, description="Language code"),
    lang: Optional[str] = Query(None, description="Language code alias"),
    service: VideoStreamService = Depends(get_video_service)
):
    code = (payload.value if payload else None) or lang or value or "en"
    service.set_lang(code)
    return service.get_status()

@router.post(
    "/api/settings/debug",
    response_model=StreamStatusResponse,
    summary="Toggle Debug Overlays",
    description="Enables or disables visual overlays, bounding boxes, and counting lines."
)
def toggle_debug_mode(
    payload: Optional[DebugToggleRequest] = Body(None),
    enabled: Optional[bool] = Query(None, description="Optional explicit boolean state"),
    service: VideoStreamService = Depends(get_video_service)
):
    flag = payload.enabled if payload and payload.enabled is not None else enabled
    if flag is not None:
        service.set_debug_mode(flag)
    else:
        service.toggle_debug_mode()
    return service.get_status()
