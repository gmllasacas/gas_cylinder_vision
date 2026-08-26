from fastapi import APIRouter
from app.api.v1.endpoints import stream_router, sources_router, settings_router, playback_router

v1_router = APIRouter()
v1_router.include_router(stream_router)
v1_router.include_router(sources_router)
v1_router.include_router(settings_router)
v1_router.include_router(playback_router)

__all__ = ["v1_router"]
