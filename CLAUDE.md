# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**PlatoniCam** (v0.4.0) is a camera settings optimization system for surveillance/VMS deployments. It generates optimal camera configurations based on scene type, lighting, and operational requirements using Claude Vision AI with heuristic fallback.

**License:** Dual-licensed under AGPL v3 (open source) and Commercial (see `COMMERCIAL.md`).

## Architecture

```
┌─────────────────────┐     ┌─────────────────────────────────┐
│  Frontend (Static)  │────▶│  Backend (FastAPI + Python)     │
│  index.html         │     │  backend/main.py                │
│  - Form UI          │     │  - Claude Vision AI integration │
│  - Results display  │     │  - ONVIF camera discovery       │
│  - Retro aesthetic  │     │  - Heuristic fallback engine    │
└─────────────────────┘     │  - Hanwha WAVE VMS support      │
                            └─────────────────────────────────┘
```

### Frontend
- Single `index.html` with embedded CSS/JavaScript (vanilla, no frameworks)
- Deployed via GitHub Pages
- Contains fallback heuristic engine (`basicHeuristicEngine` function)
- **Sites/Projects system** for organizing cameras (localStorage + JSON export/import)

### Backend (`backend/`)
- **Framework**: FastAPI (Python 3.10+)
- **AI**: Anthropic Claude Vision (`claude-sonnet-4-5-20250929`)
- **Camera Integration**: ONVIF protocol, Hanwha WAVE VMS API

Key backend files:
- `main.py` - FastAPI app, all API endpoints
- `config.py` - Pydantic settings from `.env`
- `models/pipeline.py` - Pydantic data models, enums (SceneType, CameraPurpose, etc.)
- `errors.py` - Exception hierarchy with recovery hints
- `services/optimization.py` - Optimization orchestration
- `services/discovery.py` - ONVIF and WAVE camera discovery
- `services/apply.py` - Apply settings via ONVIF/VMS
- `services/providers/` - Provider abstraction layer:
  - `base.py` - `OptimizationProvider` ABC
  - `claude_provider.py` - Claude AI provider
  - `heuristic_provider.py` - Rule-based fallback
  - `factory.py` - Provider factory pattern
- `integrations/claude_client.py` - Anthropic Claude API wrapper
- `integrations/onvif_client.py` - ONVIF camera protocol client
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
```

### Code Quality
```bash
black .        # Format
ruff check .   # Lint
```

### Deployment
Frontend: Push to `main` branch (GitHub Pages auto-deploys)
Backend: See `backend/README.md` for Render/Railway deployment

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/health` | GET | Health check |
| `/api/optimize` | POST | Generate optimal settings (AI + fallback) |
| `/api/discover` | GET | ONVIF camera discovery (WS-Discovery) |
| `/api/cameras/{id}/capabilities` | GET | Query camera capabilities via ONVIF |
| `/api/cameras/{id}/current-settings` | GET | Query current settings via ONVIF |
| `/api/apply` | POST | Apply settings via ONVIF/VMS |
| `/api/apply/status/{job_id}` | GET | Check apply job status |
| `/api/wave/discover` | GET | Hanwha WAVE VMS camera discovery |
| `/api/wave/cameras/{id}/capabilities` | GET | Query capabilities via WAVE |
| `/api/wave/cameras/{id}/current-settings` | GET | Query current settings via WAVE |
| `/api/providers` | GET | List available optimization providers |

API docs: `http://localhost:8000/docs` (Swagger UI)

## Sites/Projects System

The frontend organizes cameras into **Sites** (projects/groups). Each site contains its own cameras, optimizations, and health schedules.

### Site Data Model (localStorage)
```javascript
{
  id: "uuid",
  name: "Site Name",
  description: "Optional",
  createdAt: "ISO8601",
  updatedAt: "ISO8601",
  cameras: [...],
  optimizations: [...],
  healthSchedules: [...]
}
```

### Key Functions (in `index.html`)
- `getCurrentSite()` - Returns active site object
- `getCurrentCameras()` - Returns cameras for active site
- `addCameraToCurrentSite(camera)` - Adds camera with validation
- `createSite(name, description)` - Creates new site
- `exportCurrentSite()` - Downloads site as JSON
- `importSiteFromFile(file)` - Loads site from JSON

### Adding Site Features
1. Site state is in `state.sites[]` and `state.currentSiteId`
2. All camera/optimization access must use helper functions (not direct `state.cameras`)
3. Site data persists to localStorage key `platonicam_state`

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
FALLBACK_TO_HEURISTIC=true         # Fall back to heuristic if AI fails
DATABASE_URL=sqlite:///./platonicam.db
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000,file://
ONVIF_TIMEOUT_SECONDS=10
AI_OPTIMIZATION_TIMEOUT_SECONDS=30
LOG_LEVEL=INFO
```

## Domain Context

### Camera Settings
- **WDR**: Handles high-contrast scenes (bright windows)
- **IR**: Night vision illumination
- **Shutter Speed**: 1/250-1/500 prevents blur but needs more light
- **H.265 vs H.264**: H.265 offers ~50% better compression

### Trade-offs the Engine Balances
1. Image quality vs storage (bitrate)
2. Motion clarity vs low-light (shutter speed)
3. Bandwidth vs retention
4. Detail vs coverage (FPS, resolution)
