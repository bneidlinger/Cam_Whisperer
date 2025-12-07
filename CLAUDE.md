# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**CamOpt AI** (v0.2) is a camera settings optimization system for surveillance/VMS deployments. It generates optimal camera configurations based on scene type, lighting, and operational requirements using Claude Vision AI with heuristic fallback.

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

### Backend (`backend/`)
- **Framework**: FastAPI (Python 3.10+)
- **AI**: Anthropic Claude Vision (`claude-sonnet-4-5-20250929`)
- **Camera Integration**: ONVIF protocol, Hanwha WAVE VMS API

Key backend files:
- `main.py` - FastAPI app, all API endpoints, Pydantic models
- `config.py` - Pydantic settings from `.env`
- `services/optimization.py` - Claude AI integration + heuristic fallback
- `services/discovery.py` - ONVIF and WAVE camera discovery
- `services/apply.py` - Apply settings via ONVIF/VMS
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
venv\Scripts\activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env   # Edit and add ANTHROPIC_API_KEY

# Run development server
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Run tests
pytest
pytest tests/test_optimization.py  # Single file

# Code formatting
black .
ruff check .
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

API docs: `http://localhost:8000/docs` (Swagger UI)

## Code Modification Guidelines

### Adding Scene Types
1. Add option to `#scene-type` select in `index.html`
2. Add case in `basicHeuristicEngine` (frontend) and `services/optimization.py` (backend)

### Adding Purposes
1. Add option to `#purpose` select in `index.html`
2. Add case in purpose switch in both heuristic engines

### Modifying AI Prompt
Edit the prompt template in `services/optimization.py` (`_build_optimization_prompt` method)

### Adding VMS Integration
1. Add client in `integrations/` (e.g., `integrations/new_vms_client.py`)
2. Add discovery methods in `services/discovery.py`
3. Add apply adapter in `services/apply.py`
4. Add endpoints in `main.py`

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
DATABASE_URL=sqlite:///./camopt.db
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
