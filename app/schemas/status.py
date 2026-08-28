from typing import Optional, Dict, Any
from pydantic import BaseModel, Field

class StreamStatusResponse(BaseModel):
    """Complete system telemetry, video status, performance metrics, and counter KPIs."""
    current_video: str = Field(..., description="Active video filename or camera label")
    current_source_id: str = Field(..., description="Active source identifier")
    is_live: bool = Field(..., description="True if consuming live RTSP stream")
    is_file_missing: bool = Field(..., description="True if local video file was not found")
    camera_connected: bool = Field(..., description="True if live stream endpoint is currently connected")
    connection_error_msg: str = Field(..., description="Error message if disconnected")
    
    active_model: str = Field(..., description="Active YOLO model weights filename")
    conf: float = Field(..., description="Detector confidence threshold (0.01 - 0.99)")
    imgsz: int = Field(..., description="Inference image resolution")
    frame_skip: int = Field(..., description="Frame skip factor")
    playback_speed: float = Field(..., description="Playback speed multiplier")
    output_width: int = Field(..., description="Output stream width in pixels")
    lang: str = Field(..., description="Active localization code (e.g. en, es)")

    video_native_fps: float = Field(..., description="Original video or camera hardware FPS")
    actual_stream_fps: float = Field(..., description="Actual processed stream frame rate")
    max_hardware_fps: float = Field(..., description="Theoretical maximum hardware compute FPS")
    ai_latency_ms: float = Field(..., description="YOLO inference latency per frame in ms")
    encode_latency_ms: float = Field(..., description="JPEG resize and encode latency in ms")
    debug_mode: bool = Field(..., description="True if visual annotations and overlays are enabled")

    current_frame: int = Field(..., description="Current frame index")
    total_frames: int = Field(..., description="Total frame count in video (0 for live)")
    fps: float = Field(..., description="Current stream FPS")
    current_time: float = Field(..., description="Current playback time in seconds")
    duration: float = Field(..., description="Total video duration in seconds")
    is_paused: bool = Field(..., description="True if playback is currently paused")
    loop: bool = Field(..., description="True if video file loops upon finish")

    in_count: int = Field(..., description="Total count of cylinders going Below (IN)")
    out_count: int = Field(..., description="Total count of cylinders going Above (OUT)")
    net_count: int = Field(..., description="Net daily total (IN - OUT)")
    active_tracks: int = Field(..., description="Count of currently tracked objects in view")
    active_alerts_count: int = Field(default=0, description="Count of active unread anomaly/inconsistency alerts")
    latest_alert: Optional[Dict[str, Any]] = Field(default=None, description="Most recent anomaly alert object if any")
