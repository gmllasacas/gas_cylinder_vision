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

## Quick Start

### 1. Prerequisites
- Python 3.10+
- Virtual environment (`venv`)

### 2. Setup Environment
```bash
# Create and activate virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1   # Windows PowerShell
# source venv/bin/activate    # Linux / macOS

# Install dependencies
pip install -r requirements.txt
```

### 3. Run Application
```bash
# Using Uvicorn (Recommended)
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Or using Python module runner
python -m app
```
Navigate to: **[http://localhost:8000](http://localhost:8000)**

---

## Interactive API Documentation

Once the server is running, explore auto-generated interactive documentation:
- **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)

---

## Running Automated Tests

The test suite covers unit logic (mathematical line crossings, Pydantic validation, i18n lookups) and FastAPI HTTP integration endpoints:

```bash
# Run all tests
pytest

# Run only unit tests
pytest -m unit

# Run only API integration tests
pytest -m integration
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
