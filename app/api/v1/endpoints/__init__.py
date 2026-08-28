from app.api.v1.endpoints.stream import router as stream_router
from app.api.v1.endpoints.sources import router as sources_router
from app.api.v1.endpoints.settings import router as settings_router
from app.api.v1.endpoints.playback import router as playback_router
from app.api.v1.endpoints.counts import router as counts_router
from app.api.v1.endpoints.alerts import router as alerts_router

__all__ = [
    "stream_router",
    "sources_router",
    "settings_router",
    "playback_router",
    "counts_router",
    "alerts_router",
]
