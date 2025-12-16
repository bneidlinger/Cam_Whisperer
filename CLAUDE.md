# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**PlatoniCam** is a camera settings optimization system for surveillance/VMS deployments. It generates optimal camera configurations based on scene type, lighting, and operational requirements using Claude Vision AI with heuristic fallback.

**License:** Dual-licensed under AGPL v3 (open source) and Commercial (see `COMMERCIAL.md`).

## Architecture

```
┌─────────────────────┐     ┌─────────────────────────────────────────┐
│  Frontend (Static)  │────▶│  Backend (FastAPI + Python 3.10+)       │
│  index.html         │     │  backend/main.py                        │
│  - Form UI          │     │  ┌─────────────────────────────────────┐│
│  - Results display  │     │  │ Services                            ││
│  - Sites system     │     │  │  - optimization.py (orchestration)  ││
│  - Retro aesthetic  │     │  │  - discovery.py (ONVIF/WAVE)        ││
└─────────────────────┘     │  │  - apply.py (settings application)  ││
                            │  │  - providers/ (AI + heuristic)      ││
                            │  └─────────────────────────────────────┘│
                            │  ┌─────────────────────────────────────┐│
                            │  │ Integrations                        ││
                            │  │  - claude_client.py (Claude Vision) ││
                            │  │  - onvif_client.py (ONVIF protocol) ││
                            │  │  - webrtc_signaling.py (live view)  ││
                            │  │  - hanwha_wave_client.py (WAVE VMS) ││
                            │  └─────────────────────────────────────┘│
                            │  ┌─────────────────────────────────────┐│
                            │  │ Persistence (SQLite via SQLAlchemy) ││
                            │  │  - cameras, optimizations, jobs     ││
                            │  └─────────────────────────────────────┘│
                            └─────────────────────────────────────────┘
```

### Frontend
- Single `index.html` (~3,600 lines) with embedded CSS/JavaScript (vanilla, no frameworks)
- Deployed via GitHub Pages at https://bneidlinger.github.io/cam_whisperer/
- Contains fallback heuristic engine (`basicHeuristicEngine` function)
- **Sites/Projects system** for organizing cameras (localStorage + JSON export/import)

### Backend (`backend/`)
Key files:
- `main.py` - FastAPI app, all API endpoints
- `config.py` - Pydantic settings from `.env`
- `database.py` - SQLAlchemy engine and session management
- `errors.py` - Exception hierarchy with recovery hints
- `models/pipeline.py` - Pydantic API models, enums (SceneType, CameraPurpose, etc.)
- `models/orm.py` - SQLAlchemy ORM models (Camera, Optimization, AppliedConfig, CameraDatasheet)
- `services/optimization.py` - Optimization orchestration
- `services/discovery.py` - ONVIF WS-Discovery and WAVE camera discovery
- `services/apply.py` - Apply settings via ONVIF/VMS
- `services/providers/base.py` - `OptimizationProvider` ABC
- `services/providers/claude_provider.py` - Claude AI provider
- `services/providers/heuristic_provider.py` - Rule-based fallback
- `integrations/claude_client.py` - Anthropic Claude API wrapper
- `integrations/onvif_client.py` - ONVIF camera protocol client (Profile S/T)
- `integrations/media2_client.py` - ONVIF Media2 service for Profile T
- `integrations/webrtc_signaling.py` - WebRTC signaling gateway for low-latency streaming
- `integrations/hanwha_wave_client.py` - Hanwha WAVE VMS API client

## Development Commands

### Frontend (no build)
```bash
# Open directly
start index.html  # Windows
open index.html   # macOS

# Or serve with Python
python -m http.server 3000
```

### Backend
```bash
cd backend

# Setup (first time)
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # macOS/Linux
pip install -r requirements.txt
cp .env.example .env   # Edit and add ANTHROPIC_API_KEY

# Run development server
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Quick start (Windows) - handles venv, deps, config
.\start.bat
# Or PowerShell with full validation:
.\start.ps1
```

### Testing
```bash
# From project root (with backend venv activated)
pytest tests/                                          # All tests
pytest tests/backend/test_optimization.py              # Single file
pytest tests/backend/test_optimization.py -k "heuristic"  # Pattern match
pytest tests/ --cov=backend --cov-report=html          # With coverage

# Integration tests (PowerShell, require live cameras/VMS)
.\tests\backend\test_onvif.ps1   # ONVIF camera tests
.\tests\backend\test_wave.ps1    # WAVE VMS tests
```

### Code Quality
```bash
black .        # Format
ruff check .   # Lint
mypy .         # Type checking (optional)
```

API docs available at `http://localhost:8000/docs` (Swagger UI) when backend is running.

## Frontend Sites System

The frontend organizes cameras into **Sites**. State is in `state.sites[]` and `state.currentSiteId`. All camera/optimization access must use helper functions (not direct `state.cameras`). Data persists to localStorage key `platonicam_state`.

Key functions: `getCurrentSite()`, `getCurrentCameras()`, `addCameraToCurrentSite(camera)`, `createSite(name, description)`, `exportCurrentSite()`, `importSiteFromFile(file)`

## Code Modification Guidelines

### Adding Scene Types
1. Add to `SceneType` enum in `models/pipeline.py`
2. Add option to `#scene-type` select in `index.html`
3. Add case in `basicHeuristicEngine` (frontend) and `services/providers/heuristic_provider.py` (backend)

### Adding Purposes
1. Add to `CameraPurpose` enum in `models/pipeline.py`
2. Add option to `#purpose` select in `index.html`
3. Add case in purpose switch in both heuristic engines

### Modifying AI Prompt
Edit `_build_optimization_prompt()` in `services/providers/claude_provider.py`

### Adding a New Optimization Provider
1. Create class implementing `OptimizationProvider` ABC from `services/providers/base.py`
2. Implement `info`, `optimize()`, and `is_available()` methods
3. Register in `services/providers/factory.py`

### Adding VMS Integration
1. Add client in `integrations/` (e.g., `integrations/new_vms_client.py`)
2. Add discovery methods in `services/discovery.py`
3. Add apply adapter in `services/apply.py`
4. Add `ApplyMethod` enum value in `models/pipeline.py`
5. Add endpoints in `main.py`

## Environment Variables

Required in `backend/.env`:
```
ANTHROPIC_API_KEY=sk-ant-...  # Required for AI optimization
```

Optional (with defaults):
```
APP_ENV=development
CLAUDE_MODEL=claude-sonnet-4-5-20250929
FALLBACK_TO_HEURISTIC=true
DATABASE_URL=sqlite:///./platonicam.db
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000,file://
ONVIF_TIMEOUT_SECONDS=10
AI_OPTIMIZATION_TIMEOUT_SECONDS=30
LOG_LEVEL=INFO

# WebRTC (Phase 3)
WEBRTC_ENABLED=true
TURN_SERVER_URL=                    # Optional TURN for NAT traversal
STUN_SERVER_URLS=stun:stun.l.google.com:19302
```

## Error Handling

The backend uses a structured exception hierarchy (`errors.py`) where every error includes:
- `recoverable` flag - whether retry/fallback is possible
- `recovery_hint` - user-friendly guidance

Key error categories:
- **Discovery**: `DiscoveryError`, `NetworkScanError`, `VmsConnectionError`
- **Optimization**: `ProviderError`, `ProviderRateLimitError`, `InvalidResponseError`
- **Apply**: `ApplyError`, `PartialApplyError`, `ApplyTimeoutError`
- **Auth**: `CameraAuthError`, `VmsAuthError`, `MissingApiKeyError`

When adding error handling, raise from appropriate error class and include recovery hints.

## Provider System

The optimization engine uses a provider abstraction (`services/providers/base.py`):

```python
# Provider capabilities (check with provider.info.capabilities)
SCENE_ANALYSIS     # Analyze sample frames
MULTI_CAMERA       # Optimize multiple cameras together
CONSTRAINT_SOLVING # Respect bandwidth/retention constraints
OFFLINE            # Works without internet (heuristic only)
```

**Fallback behavior**: Claude AI → retry once on transient errors → heuristic engine

## Database Schema

SQLAlchemy ORM models in `models/orm.py`:
- **Camera** - Registered camera inventory with credentials and capabilities
- **Optimization** - Audit trail of all optimization runs
- **AppliedConfig** - Applied configuration job tracking
- **CameraDatasheet** - Manufacturer specs fetched from datasheets

Database initialized via `init_db()` in `database.py` on startup.

## Domain Context

### Camera Settings
- **WDR**: Handles high-contrast scenes (bright windows)
- **HLC**: High Light Compensation masks headlight glare (parking lots)
- **IR**: Night vision illumination
- **Shutter Speed**: 1/250-1/500 prevents blur but needs more light
- **H.265 vs H.264**: H.265 offers ~50% better compression

### Trade-offs the Engine Balances
1. Image quality vs storage (bitrate)
2. Motion clarity vs low-light (shutter speed)
3. Bandwidth vs retention
4. Detail vs coverage (FPS, resolution)

## ONVIF Integration

The backend supports ONVIF Profile S (streaming) and Profile T (advanced streaming):
- `onvif_client.py` handles device discovery, PTZ, and imaging services
- `media2_client.py` provides Media2 service for Profile T cameras
- `webrtc_signaling.py` proxies WebRTC signaling (JSON-RPC 2.0) between browsers and cameras

WebRTC architecture: Browser ↔ WebSocket ↔ Backend Gateway ↔ Camera, then direct SRTP P2P or TURN relay for media.
