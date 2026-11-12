# Gas Tank Stream & Real-Time Computer Vision Counter

[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688.svg?style=flat&logo=FastAPI&logoColor=white)](https://fastapi.tiangolo.com)
[![Python](https://img.shields.io/badge/Python-3.10+-3776AB.svg?style=flat&logo=Python&logoColor=white)](https://www.python.org/)
[![YOLOv8](https://img.shields.io/badge/YOLOv8-Ultralytics-00FFFF.svg?style=flat)](https://ultralytics.com)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg?style=flat&logo=docker&logoColor=white)](https://www.docker.com/)
[![Tests](https://img.shields.io/badge/Tests-Pytest-brightgreen.svg?style=flat)](https://docs.pytest.org/)

An enterprise-ready, real-time Computer Vision system and FastAPI web service designed for video inspection, directional object tracking, and automatic counting of gas cylinders from RTSP CCTV camera feeds or pre-recorded video files.

---

## Architecture & Project Structure

The project follows the standard **FastAPI Application Layout** decoupled from a **Modular Computer Vision Pipeline**:

```text
gas_stream/
├── .env.example                     # Environment variables template
├── .dockerignore                    # Build artifact exclusions
├── Dockerfile                       # Multi-stage production container
├── docker-compose.yml               # Container orchestration with volumes
├── pytest.ini                       # Test suite runner & warning filters
├── requirements.txt                 # Pinned project dependencies
├── README.md                        # Documentation
│
├── app/                             # Core Application Package
│   ├── __init__.py
│   ├── __main__.py                  # python -m app entrypoint
│   ├── main.py                      # FastAPI app factory, static & locales mount
│   │
│   ├── core/                        # Singletons & App Infrastructure
│   │   ├── config.py                # Pydantic Settings (Source, Detector, Streaming)
│   │   ├── logging.py               # Structured logger
│   │   └── i18n.py                  # Dot-notation I18nManager with fallbacks
│   │
│   ├── cv/                          # Computer Vision Engine (Decoupled from Web)
│   │   ├── capture.py               # VideoCaptureManager (RTSP reconnects, file loops, seeks)
│   │   ├── detector.py              # YOLODetector (Model loader, ObjectCounter, frame skip)
│   │   ├── counter.py               # LineCrossingCounter (Trajectories, directional crossing math)
│   │   ├── renderer.py              # FrameRenderer (Standby canvases, overlays, JPEG encoding)
│   │   └── pipeline.py              # CVPipeline (Chains components and measures hardware FPS)
│   │
│   ├── services/                    # Application Services
│   │   └── stream_manager.py        # VideoStreamService (Worker thread, MJPEG generator)
│   │
│   ├── api/                         # Modular API Layer
│   │   ├── router.py                # Main router aggregator
│   │   └── v1/
│   │       └── endpoints/
│   │           ├── stream.py        # /video_feed, /api/status
│   │           ├── sources.py       # /api/videos, /api/videos/select
│   │           ├── settings.py      # /api/config, /api/settings/conf, /speed, /lang, /debug
│   │           └── playback.py      # /api/playback/toggle, /seek, /step, /reset
│   │
│   └── schemas/                     # Strongly-Typed Pydantic DTOs
│       ├── status.py                # StreamStatusResponse
│       ├── source.py                # SourceItem, VideoSourcesResponse, SelectSourceResponse
│       ├── playback.py              # SeekRequest, StepRequest
│       └── settings.py              # Validation models for conf, speed, lang, debug
│
├── tests/                           # Pytest Test Suite
│   ├── conftest.py                  # TestClient & mock frame fixtures
│   ├── unit/                        # Unit tests (Settings, Counter math, i18n)
│   └── integration/                 # API endpoint integration tests
│
├── config.json                      # Persistent application configuration
├── locales/                         # Translations (en.json, es.json)
├── models/                          # YOLO model weights (.pt files)
├── static/                          # Frontend CSS and JS
├── templates/                       # Jinja2 / HTML templates
├── videos/                          # Video storage
└── training/                        # Offline dataset tools and extraction scripts
```

---

## Quick Start (Setup by Operating System)

### Prerequisites
- Python 3.10+
- Git (optional)
- NVIDIA GPU with updated drivers (optional, for CUDA hardware acceleration)

---

### Windows (PowerShell)

1. **Open PowerShell and navigate to the project directory:**
   ```powershell
   cd d:\laragon\www\gas_stream
   ```

2. **Allow script execution for current session (if restricted):**
   ```powershell
   Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
   ```

3. **Create and activate the virtual environment:**
   ```powershell
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   ```
   *(Verify that `(venv)` appears before your prompt in the terminal).*

4. **Install dependencies:**
   ```powershell
   python -m pip install --upgrade pip
   pip install -r requirements.txt

   # Optional (For NVIDIA GPUs): Enable CUDA hardware acceleration
   pip install torch torchvision --index-url https://download.pytorch.org/whl/cu124 --force-reinstall
   ```

5. **Run the application:**
   ```powershell
   # Method A: Using Python module runner (Recommended, avoids PATH conflicts)
   python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

   # Method B: Using application entrypoint
   python -m app

   # Method C: Direct Uvicorn command
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```

---

### Windows (Command Prompt / CMD)

1. **Navigate to the project directory:**
   ```cmd
   cd /d D:\laragon\www\gas_stream
   ```

2. **Create and activate the virtual environment:**
   ```cmd
   python -m venv venv
   venv\Scripts\activate.bat
   ```

3. **Install dependencies:**
   ```cmd
   python -m pip install --upgrade pip
   pip install -r requirements.txt

   rem Optional (For NVIDIA GPUs): Enable CUDA hardware acceleration
   pip install torch torchvision --index-url https://download.pytorch.org/whl/cu124 --force-reinstall
   ```

4. **Run the application:**
   ```cmd
   python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```

---

### Linux / macOS / WSL

1. **Install system dependencies (required for OpenCV & FFmpeg):**
   ```bash
   # Debian / Ubuntu / WSL:
   sudo apt-get update && sudo apt-get install -y libgl1 libglib2.0-0 ffmpeg

   # macOS (Homebrew):
   brew install ffmpeg
   ```

2. **Create and activate the virtual environment:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt

   # Optional (For Linux/WSL with NVIDIA GPUs): Enable CUDA hardware acceleration
   pip install torch torchvision --index-url https://download.pytorch.org/whl/cu124 --force-reinstall
   ```

4. **Run the application:**
   ```bash
   python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```

---

### Hardware Acceleration (NVIDIA GPU / CUDA)

By default, the application runs inference on CPU threads. If your machine is equipped with an NVIDIA GPU (e.g. GTX 1660 Ti, RTX series), you can achieve 5x-10x faster inference (~4-8 ms per frame vs ~50 ms on CPU):

1. **Install PyTorch with CUDA 12.4 support:**
   ```powershell
   pip install torch torchvision --index-url https://download.pytorch.org/whl/cu124 --force-reinstall
   ```

2. **Verify GPU detection:**
   ```powershell
   python -c "import torch; print('CUDA Available:', torch.cuda.is_available(), '| GPU:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'None')"
   ```

3. **Configure device in `.env`:**
   ```ini
   # Options: 'auto' (automatically selects GPU if detected), 'cuda', 'cuda:0', or 'cpu'
   YOLO_DEVICE=cuda
   ```

---

### Resetting / Fixing a Broken Local Environment

If you renamed the project folder, moved directories, or receive errors such as `Fatal error in launcher` or `uvicorn is not recognized`:

#### On Windows (PowerShell):
```powershell
# 1. Deactivate existing venv if active
deactivate

# 2. Delete the broken virtual environment and caches
Remove-Item -Recurse -Force venv
Get-ChildItem -Recurse -Filter "__pycache__" | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
Get-ChildItem -Recurse -Filter ".pytest_cache" | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue

# 3. Rebuild fresh venv
python -m venv venv

# 4. Activate with script execution policy bypass
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\venv\Scripts\Activate.ps1

# 5. Upgrade pip and reinstall dependencies cleanly
python -m pip install --upgrade pip
pip install -r requirements.txt
```

#### On Linux / macOS:
```bash
deactivate 2>/dev/null || true
rm -rf venv/ .pytest_cache/ $(find . -type d -name "__pycache__")
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

---

## Interactive API Documentation

Once the server is running, navigate to:
- **Dashboard UI**: [http://localhost:8000](http://localhost:8000)
- **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)

---

## Running Automated Tests

```bash
# Run all tests using Python module runner
python -m pytest

# Run only unit tests
python -m pytest -m unit

# Run only API integration tests
python -m pytest -m integration
```

---

## Docker Deployment

Run the containerized application with persistent configuration and volumes:

```bash
docker compose up --build -d
```

To stop:
```bash
docker compose down
```
