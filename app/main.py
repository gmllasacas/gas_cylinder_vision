import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, Request, Response
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from app.core import settings, logger, get_current_admin
from app.api import api_router
from app.services.stream_manager import video_service
from app.db import db_repo

@asynccontextmanager
async def lifespan(application: FastAPI):
    """Handles application startup and graceful shutdown."""
    logger.info("FastAPI Application startup completed.")
    application.state.video_service = video_service
    application.state.db_repo = db_repo
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

    # Security Headers Middleware (Anti-Clickjacking, CSP, MIME-Sniffing protection)
    @application.middleware("http")
    async def add_security_headers(request: Request, call_next):
        response: Response = await call_next(request)
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "img-src 'self' data: blob:; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
            "connect-src 'self'; "
            "frame-ancestors 'none';"
        )

        # Strict-Transport-Security (HSTS): Enforce HTTPS in production or when connection is secure
        is_secure = (
            request.url.scheme == "https"
            or request.headers.get("x-forwarded-proto", "").lower() == "https"
            or str(settings.environment).lower() == "production"
        )
        if is_secure:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        return response

    # Ensure static/locales directories exist
    os.makedirs(settings.static_dir, exist_ok=True)
    os.makedirs(settings.locales_dir, exist_ok=True)

    # Mount Static Assets & Localization Files
    application.mount("/static", StaticFiles(directory=settings.static_dir), name="static")
    application.mount("/locales", StaticFiles(directory=settings.locales_dir), name="locales")

    # Health Check Endpoint for Docker & Monitoring (No Auth)
    @application.get("/health", tags=["System"])
    def get_health():
        return {"status": "healthy", "service": settings.app_name}

    # Public Root Favicon Endpoint
    favicon_ico = os.path.join(settings.static_dir, "favicon.ico")

    @application.get("/favicon.ico", include_in_schema=False)
    def get_favicon():
        if os.path.exists(favicon_ico):
            return FileResponse(favicon_ico, media_type="image/x-icon")
        return FileResponse(os.path.join(settings.static_dir, "favicon.svg"), media_type="image/svg+xml")

    # Serve Main Dashboard UI
    index_html = os.path.join(settings.templates_dir, "index.html")

    @application.get("/", tags=["Dashboard"], dependencies=[Depends(get_current_admin)])
    def get_index():
        return FileResponse(
            index_html,
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0"
            }
        )

    @application.get("/v2", tags=["Dashboard"], dependencies=[Depends(get_current_admin)])
    def get_index_v2():
        return FileResponse(
            index_html,
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0"
            }
        )

    # Include Modular API Routers with Admin Auth
    application.include_router(api_router, dependencies=[Depends(get_current_admin)])

    logger.info("FastAPI Application initialized successfully.")
    return application

app = create_app()
