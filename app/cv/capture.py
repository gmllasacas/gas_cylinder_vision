import os
import time
from typing import Optional, Tuple
import cv2
import numpy as np
from app.core.logging import logger

SUPPORTED_EXTENSIONS = ('.mp4', '.avi', '.mov', '.mkv', '.webm')

class VideoCaptureManager:
    """Manages video file playback and RTSP live camera streaming with auto-reconnection and seeking."""

    def __init__(self, reconnect_interval_sec: int = 3):
        self.reconnect_interval_sec = reconnect_interval_sec
        self.cap = cv2.VideoCapture()
        self.current_source_path = ""
        self.is_live_stream = False
        self.is_file_missing = False
        self.camera_connected = False
        self.connection_error_msg = ""
        self.last_reconnect_attempt = 0.0
        
        self.total_frames = 0
        self.video_fps = 25.0
        self.current_frame = 0
        self.loop = True
        self.just_looped = False

    @staticmethod
    def is_live_url(source: str) -> bool:
        """Determines if the given source path is a live network stream (RTSP/HTTP/RTMP) or device index."""
        if not isinstance(source, str):
            return False
        return source.startswith(("rtsp://", "rtmp://", "http://", "https://")) or source.isdigit()

    @staticmethod
    def mask_credentials(url: str) -> str:
        """Masks passwords inside RTSP/HTTP URLs for safe display."""
        if "@" in url and "://" in url:
            try:
                protocol, rest = url.split("://", 1)
                user_info, host_info = rest.split("@", 1)
                if ":" in user_info:
                    username, _ = user_info.split(":", 1)
                    return f"{protocol}://{username}:****@{host_info}"
                return f"{protocol}://****@{host_info}"
            except Exception:
                pass
        return url

    def open(self, source_path: str) -> Tuple[bool, Optional[np.ndarray]]:
        """
        Opens a new video file or live stream.
        Returns (success, initial_frame).
        """
        if self.cap.isOpened():
            self.cap.release()

        self.current_source_path = source_path
        self.is_live_stream = self.is_live_url(source_path)
        self.last_reconnect_attempt = time.time()
        self.current_frame = 0
        self.just_looped = False

        try:
            if self.is_live_stream:
                self.is_file_missing = False
                src = int(source_path) if source_path.isdigit() else source_path
                os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp|stimeout;3000000"
                self.cap = cv2.VideoCapture(src, cv2.CAP_FFMPEG)
                self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            else:
                if not os.path.exists(source_path):
                    self.is_file_missing = True
                    self.camera_connected = False
                    self.total_frames = 0
                    self.connection_error_msg = f"Video file not found: {os.path.basename(source_path)}"
                    logger.error(self.connection_error_msg)
                    return False, None

                self.is_file_missing = False
                self.cap = cv2.VideoCapture(source_path)

            if self.cap.isOpened():
                ret, test_frame = self.cap.read()
                if ret and test_frame is not None:
                    self.camera_connected = True
                    self.is_file_missing = False
                    self.connection_error_msg = ""
                    
                    if self.is_live_stream:
                        self.total_frames = 0
                        self.video_fps = 25.0
                    else:
                        self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
                        raw_fps = self.cap.get(cv2.CAP_PROP_FPS)
                        self.video_fps = raw_fps if raw_fps and 1.0 <= raw_fps <= 120.0 else 25.0

                    logger.info(f"Source connected successfully: {self.mask_credentials(source_path)} (FPS: {self.video_fps}, Total Frames: {self.total_frames})")
                    return True, test_frame
                else:
                    self.camera_connected = False
                    self.connection_error_msg = "Stream/file opened but failed to read initial frame."
            else:
                self.camera_connected = False
                self.connection_error_msg = "Could not open stream endpoint or video file."
        except Exception as e:
            self.camera_connected = False
            self.connection_error_msg = self.mask_credentials(str(e))
            logger.error(f"Failed to open source {self.mask_credentials(source_path)}: {self.connection_error_msg}")

        return False, None

    def read_frame(self) -> Tuple[bool, Optional[np.ndarray]]:
        """Reads the next frame, handling loop behavior for video files."""
        if not self.cap.isOpened():
            return False, None

        success, frame = self.cap.read()
        if success and frame is not None:
            if not self.is_live_stream:
                self.current_frame = int(self.cap.get(cv2.CAP_PROP_POS_FRAMES))
            else:
                self.current_frame += 1
            self.camera_connected = True
            return True, frame
        
        # Handle file end loop
        if not self.is_live_stream and self.loop and self.total_frames > 0:
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            self.current_frame = 0
            self.just_looped = True
            success, frame = self.cap.read()
            if success and frame is not None:
                return True, frame

        if self.is_live_stream:
            self.camera_connected = False

        return False, None

    def seek_frame(self, target_frame: int) -> Tuple[bool, Optional[np.ndarray]]:
        """Seeks to a specific frame number in local video files."""
        if self.is_live_stream or self.is_file_missing or not self.cap.isOpened() or self.total_frames <= 0:
            return False, None

        clamped = max(0, min(self.total_frames - 1, target_frame))
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, clamped)
        self.current_frame = clamped
        return self.cap.read()

    def seek_offset(self, seconds_offset: float) -> Tuple[bool, Optional[np.ndarray]]:
        """Seeks relative to current frame in seconds."""
        if self.is_live_stream or self.is_file_missing:
            return False, None
        frame_offset = int(seconds_offset * self.video_fps)
        return self.seek_frame(self.current_frame + frame_offset)

    def step(self, delta_frames: int) -> Tuple[bool, Optional[np.ndarray]]:
        """Steps forward or backward by delta_frames."""
        return self.seek_frame(self.current_frame + delta_frames)

    def reset_position(self) -> Tuple[bool, Optional[np.ndarray]]:
        """Rewinds the video file to frame 0."""
        return self.seek_frame(0)

    def release(self):
        """Releases the underlying OpenCV video capture resources."""
        if self.cap.isOpened():
            self.cap.release()
