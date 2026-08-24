import os
from typing import Optional
from fastapi import FastAPI, Query
from fastapi.responses import FileResponse, StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from services.video_stream import video_service

app = FastAPI(title="Gas Tank Counter Dashboard")

# Paths configuration
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
LOCALES_DIR = os.path.join(BASE_DIR, "locales")
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
INDEX_HTML = os.path.join(TEMPLATES_DIR, "index.html")

# Mount static and locales files
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
app.mount("/locales", StaticFiles(directory=LOCALES_DIR), name="locales")

@app.get("/")
def index():
    return FileResponse(
        INDEX_HTML,
        headers={"Cache-Control": "no-cache, no-store, must-revalidate", "Pragma": "no-cache", "Expires": "0"}
    )

@app.get("/video_feed")
def video_feed():
    return StreamingResponse(
        video_service.generate_frames(), 
        media_type="multipart/x-mixed-replace; boundary=frame"
    )

@app.get("/api/status")
def api_status():
    return JSONResponse(video_service.get_status())

@app.get("/api/videos")
def api_videos():
    return JSONResponse({
        "sources": video_service.get_available_sources(),
        "videos": video_service.get_available_videos(),
        "current_video": video_service.current_video_name,
        "current_source_id": video_service.current_source_id,
        "is_live": video_service.is_live_stream
    })

@app.post("/api/videos/select")
def api_select_video(filename: str = Query(...)):
    success = video_service.change_source(filename)
    if not success:
        return JSONResponse({"status": "error", "message": f"Could not load source '{filename}'"}, status_code=400)
    return JSONResponse({"status": "success", "data": video_service.get_status()})

@app.get("/api/config")
def api_get_config():
    return JSONResponse(video_service.config)

@app.post("/api/settings/conf")
def api_set_conf(value: float = Query(...)):
    video_service.set_conf(value)
    return JSONResponse(video_service.get_status())

@app.post("/api/settings/speed")
def api_set_speed(value: float = Query(...)):
    video_service.set_playback_speed(value)
    return JSONResponse(video_service.get_status())

@app.post("/api/settings/lang")
def api_set_lang(value: str = Query("en")):
    video_service.set_lang(value)
    return JSONResponse(video_service.get_status())

@app.post("/api/settings/debug")
def api_toggle_debug(enabled: Optional[bool] = Query(None)):
    if enabled is not None:
        video_service.set_debug_mode(enabled)
    else:
        video_service.toggle_debug_mode()
    return JSONResponse(video_service.get_status())

@app.post("/api/playback/toggle")
def api_toggle():
    video_service.toggle_pause()
    return JSONResponse(video_service.get_status())

@app.post("/api/playback/seek")
def api_seek(frame: Optional[int] = Query(None), offset: Optional[float] = Query(None)):
    if frame is not None:
        video_service.seek_frame(frame)
    elif offset is not None:
        video_service.seek_offset(offset)
    return JSONResponse(video_service.get_status())

@app.post("/api/playback/step")
def api_step(delta: int = Query(-1)):
    video_service.set_pause(True)
    video_service.step(delta)
    return JSONResponse(video_service.get_status())

@app.post("/api/playback/reset")
def api_reset():
    video_service.reset()
    return JSONResponse(video_service.get_status())