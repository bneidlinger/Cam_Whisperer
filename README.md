```
╔═══════════════════════════════════════════════════════════════════════════════════╗
║                                                                                   ║
║  ██████╗ ██╗      █████╗ ████████╗ ██████╗ ███╗   ██╗██╗ ██████╗ █████╗ ███╗   ███╗║
║  ██╔══██╗██║     ██╔══██╗╚══██╔══╝██╔═══██╗████╗  ██║██║██╔════╝██╔══██╗████╗ ████║║
║  ██████╔╝██║     ███████║   ██║   ██║   ██║██╔██╗ ██║██║██║     ███████║██╔████╔██║║
║  ██╔═══╝ ██║     ██╔══██║   ██║   ██║   ██║██║╚██╗██║██║██║     ██╔══██║██║╚██╔╝██║║
║  ██║     ███████╗██║  ██║   ██║   ╚██████╔╝██║ ╚████║██║╚██████╗██║  ██║██║ ╚═╝ ██║║
║  ╚═╝     ╚══════╝╚═╝  ╚═╝   ╚═╝    ╚═════╝ ╚═╝  ╚═══╝╚═╝ ╚═════╝╚═╝  ╚═╝╚═╝     ╚═╝║
║                                                                                   ║
║                      CAMERA SETTINGS OPTIMIZATION SYSTEM                          ║
║                                 Version 0.4                                       ║
║                                                                                   ║
╚═══════════════════════════════════════════════════════════════════════════════════╝

CLASSIFICATION: UNCLASSIFIED / INTEGRATOR USE ONLY
SYSTEM TYPE:    Video Management System Configuration Assistant
DATE:           2025-CURRENT
STATUS:         TESTING PHASE - CLAUDE VISION AI ACTIVE
```

[![License: AGPL v3](https://img.shields.io/badge/License-AGPL_v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)
[![Commercial License](https://img.shields.io/badge/License-Commercial-orange.svg)](COMMERCIAL.md)

## MISSION STATEMENT

> **Every camera has a platonic state, and it actually can and should be achieved at all times.**

The gap between factory defaults and optimal field performance is where 70% of video surveillance failures occur. PlatoniCam exists to close that gap.

## PROBLEM OVERVIEW

```
┌─────────────────────────────────────────────────────────────────┐
│ CURRENT STATE OF SURVEILLANCE CAMERA DEPLOYMENT                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  [X] Cameras shipped with generic factory defaults              │
│  [X] Installers lack time to optimize per-camera settings       │
│  [X] Lighting conditions ignored during commissioning           │
│  [X] Bandwidth/storage constraints discovered post-deployment   │
│  [X] WDR, shutter speed, IR settings left on AUTO               │
│  [X] Evidence-grade footage requirements not met                │
│                                                                  │
│  RESULT: Suboptimal image quality, wasted bandwidth,            │
│          failed investigations, customer dissatisfaction        │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## SOLUTION ARCHITECTURE

PlatoniCam provides integrators with **AI-powered configuration recommendations** based on:

- **Scene Classification** (hallway, parking lot, entrance, perimeter, etc.)
- **Operational Purpose** (overview, face recognition, license plate capture, evidence-grade)
- **Environmental Factors** (lighting variance, motion levels, contrast extremes)
- **Resource Constraints** (bandwidth budgets, retention requirements, VMS platform)
- **Visual Scene Analysis** (optional sample frame upload for Claude Vision analysis)

### AI Integration

Powered by **Anthropic Claude Sonnet 4.5 Vision**, the system analyzes deployment context and optionally reviews sample frames to generate professional-grade camera settings. Falls back to heuristic engine if AI is unavailable.

### Output Specification

```
RECOMMENDED SETTINGS PACKAGE
├── Stream Configuration
│   ├── Resolution
│   ├── Codec (H.264 / H.265)
│   ├── Frame Rate (FPS)
│   ├── Bitrate Target (Mbps)
│   └── Keyframe Interval
├── Exposure Control
│   ├── Shutter Speed
│   ├── Iris Mode
│   ├── Gain Limit
│   ├── WDR Level
│   └── Backlight Compensation
├── Low-Light Strategy
│   ├── IR Mode & Intensity
│   ├── Noise Reduction Level
│   └── Slow Shutter Configuration
├── Image Processing
│   ├── Sharpening
│   ├── Contrast
│   └── Saturation
└── Integrator Notes
    └── Context-specific warnings and recommendations
```

## SUPPORTED VMS PLATFORMS

```
┌────────────────────────────┬──────────────┐
│ Platform                   │ Status       │
├────────────────────────────┼──────────────┤
│ Avigilon ACC               │ SUPPORTED    │
│ Genetec Security Center    │ SUPPORTED    │
│ Milestone XProtect         │ SUPPORTED    │
│ Exacq                      │ SUPPORTED    │
│ Hanwha WAVE                │ SUPPORTED    │
│ Other / Mixed              │ GENERIC      │
└────────────────────────────┴──────────────┘
```

## DEPLOYMENT INSTRUCTIONS

### Quick Start (15 minutes)

See `QUICKSTART.md` for detailed setup instructions.

**Frontend (Retro UI):**
```bash
# Clone the repository
git clone https://github.com/bneidlinger/cam_whisperer.git
cd cam_whisperer

# Serve frontend
python -m http.server 3000
# Open http://localhost:3000
```

**Backend (Claude Vision API):**
```bash
cd backend

# Setup virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY

# Start server (Windows)
.\start.bat
# Or use: uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Backend API will be available at `http://localhost:8000`
API documentation at `http://localhost:8000/docs`

### Live Deployment (Static Demo)

**SYSTEM ONLINE:** https://bneidlinger.github.io/cam_whisperer/

The frontend is deployed via GitHub Pages. For full AI capabilities, run the backend locally with your Anthropic API key.

## USAGE PROTOCOL

```
STEP 1: Input Camera Context
        ├── Site identification
        ├── Camera model (if known)
        ├── Scene type selection
        ├── Primary operational purpose
        ├── Lighting/motion characteristics
        ├── Bandwidth and retention constraints
        └── [OPTIONAL] Upload sample frame for AI analysis

STEP 2: Generate Recommendations
        ├── Claude Vision AI analyzes deployment context
        ├── Reviews sample frame (if provided)
        └── Falls back to heuristic engine if AI unavailable

STEP 3: Review Output
        ├── Examine recommended settings
        ├── Read AI-generated integrator notes
        ├── Check confidence score (70-95% typical)
        └── Verify against deployment constraints

STEP 4: Apply to Camera/VMS
        ├── Use settings as initial configuration
        ├── Fine-tune based on live footage review
        └── Document final settings for site records

STEP 5: Track Results (Optional)
        └── Save API responses to backend/ai_outputs/ for analysis
```

## TECHNICAL SPECIFICATIONS

```
┌─────────────────────────────────────────────────────────────┐
│ APPLICATION STACK                                            │
├─────────────────────────────────────────────────────────────┤
│  Frontend:      Pure HTML5 / CSS3 / JavaScript (ES6+)       │
│  UI Design:     80's Industrial Security Aesthetic          │
│  Dependencies:  None (frontend is standalone)                │
│  Backend:       FastAPI + Python 3.11+                       │
│  AI Engine:     Anthropic Claude Sonnet 4.5 Vision          │
│  Fallback:      Rule-based heuristic engine                  │
│  Build Process: None required for frontend                   │
│  Runtime:       Modern web browser + Python backend          │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ BACKEND ARCHITECTURE                                         │
├─────────────────────────────────────────────────────────────┤
│  Framework:     FastAPI (async REST API)                     │
│  AI Provider:   Anthropic Python SDK                         │
│  Config:        Pydantic Settings + .env                     │
│  Image Support: Base64 encoding for Vision API               │
│  CORS:          Configured for localhost + file://           │
│  Tracking:      JSON logs + Markdown reports                 │
└─────────────────────────────────────────────────────────────┘
```

## CURRENT CAPABILITIES (v0.2)

```
[✓] CLAUDE VISION AI INTEGRATION
    └── Real-time analysis of deployment context and sample frames

[✓] BACKEND API SERVER
    └── FastAPI with async optimization endpoint

[✓] IMAGE ANALYSIS
    └── Base64 sample frame upload processed by Claude Vision

[✓] HEURISTIC FALLBACK
    └── Automatic degradation to rule-based engine if AI unavailable

[✓] TEST TRACKING SYSTEM
    └── Logs all optimization requests with confidence scores

[✓] RETRO INDUSTRIAL UI
    └── 80's security aesthetic with CRT effects and terminal output
```

## REMAINING LIMITATIONS

```
[!] TESTING PHASE
    └── System under active testing, not production-ready

[!] NO DIRECT VMS INTEGRATION
    └── Settings must be manually applied to cameras

[!] NO STORAGE CALCULATOR
    └── Retention targets noted but not validated against capacity

[!] NO CAMERA DISCOVERY
    └── Manual input of camera context required
```

## ROADMAP

```
PHASE 2: ✓ COMPLETED (v0.2)
         ✓ Claude Vision AI integration
         ✓ Backend API server
         ✓ Sample frame analysis
         ✓ Test tracking system

PHASE 3: IN PROGRESS
         ├── Database integration for settings history
         ├── Multi-camera site optimization
         ├── Storage capacity calculator
         └── VMS-specific export formats

PHASE 4: PLANNED
         ├── Direct VMS API integration (Genetec, Milestone, ACC)
         ├── Camera discovery via ONVIF
         ├── Automated settings application
         └── Performance monitoring & feedback loop
```

## PHILOSOPHICAL FOUNDATION

The concept of the **platonic camera state** acknowledges that:

1. Every surveillance camera has an ideal configuration for its specific deployment context
2. This ideal state is deterministic and knowable
3. Deviation from this state results in preventable failures
4. Factory defaults are, by definition, suboptimal for any specific deployment
5. Integrator expertise should be encoded, not rediscovered on every job

PlatoniCam is the first step toward **universal camera optimization** - where every camera, everywhere, operates at its theoretical best.

---

```
┌─────────────────────────────────────────────────────────────────┐
│ NOTICE TO INTEGRATORS                                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  This system provides STARTING CONFIGURATIONS ONLY.              │
│                                                                  │
│  Always verify recommendations against:                          │
│   - Actual site conditions                                       │
│   - Live footage review                                          │
│   - Customer requirements                                        │
│   - Local regulations                                            │
│                                                                  │
│  Camera settings should be validated during commissioning        │
│  and adjusted as needed. Document all final configurations.     │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## LICENSE

PlatoniCam is dual-licensed:

**Open Source:** AGPL v3 (see [LICENSE](LICENSE))

**Commercial:** Available upon request for integrators, OEMs, VARs, and SaaS deployments (see [COMMERCIAL.md](COMMERCIAL.md))

```
Copyright 2025 PlatoniCam Contributors

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
```

## CONTACT

```
REPOSITORY:  https://github.com/bneidlinger/cam_whisperer
ISSUES:      https://github.com/bneidlinger/cam_whisperer/issues
LIVE DEMO:   https://bneidlinger.github.io/cam_whisperer/
DOCS:        See backend/README.md for API documentation
```

For issues, feature requests, or integration questions, file a report via GitHub Issues.

### Additional Documentation

- `docs/QUICKSTART.md` - 15-minute setup guide
- `docs/ARCHITECTURE.md` - System architecture diagrams
- `docs/API_SPECIFICATION.md` - Complete API reference
- `docs/DEVELOPMENT_PLAN.md` - Development roadmap
- `backend/README.md` - Backend development guide
- `tests/` - Test suite and utilities

---

**END OF DOCUMENT**

```
TRANSMISSION COMPLETE
SYSTEM READY
```
