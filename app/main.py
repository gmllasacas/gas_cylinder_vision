import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from app.core import settings, logger
from app.api import api_router
from app.services.stream_manager import video_service

@asynccontextmanager
async def lifespan(application: FastAPI):
    """Handles application startup and graceful shutdown."""
    logger.info("FastAPI Application startup completed.")
    yield
    logger.info("FastAPI Application shutting down...")
    video_service.stop()

def create_app() -> FastAPI:
    """Factory creating and configuring the main FastAPI application."""
    application = FastAPI(
        title=settings.app_name,
        description="Real-time Computer Vision Gas Tank Counter & Video Inspection Dashboard",
        version="1.0.0",
        lifespan=lifespan
    )

    # Ensure static/locales directories exist
    os.makedirs(settings.static_dir, exist_ok=True)
    os.makedirs(settings.locales_dir, exist_ok=True)

    # Mount Static Assets & Localization Files
    application.mount("/static", StaticFiles(directory=settings.static_dir), name="static")
    application.mount("/locales", StaticFiles(directory=settings.locales_dir), name="locales")

    # Serve Main Dashboard UI
    index_html = os.path.join(settings.templates_dir, "index.html")

    @application.get("/", tags=["Dashboard"])
    def get_index():
        return FileResponse(
            index_html,
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0"
            }
        )

    # Include Modular API Routers
    application.include_router(api_router)

    logger.info("FastAPI Application initialized successfully.")
    return application

app = create_app()
