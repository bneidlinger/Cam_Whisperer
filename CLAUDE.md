# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**CamOpt AI** is a single-page web application (prototype v0.1) that generates optimal camera settings recommendations for surveillance/VMS (Video Management System) deployments. It's designed for security integrators to quickly determine ideal camera configurations based on scene type, lighting conditions, and operational requirements.

The entire application is contained in a single `index.html` file with embedded CSS and JavaScript - no build process, dependencies, or backend required.

## Architecture

### Application Structure

This is a **static web application** with no external dependencies:
- **No build process** - open `index.html` directly in a browser
- **No package manager** - no npm, yarn, or similar
- **No backend** - currently uses client-side heuristic rules (placeholder for future AI integration)
- **No frameworks** - vanilla HTML/CSS/JavaScript

The `.nojekyll` file indicates this is deployed to GitHub Pages.

### Core Components (all in index.html)

1. **Form Interface (Left Panel)** - Collects camera deployment context:
   - Site/camera identification
   - Scene type (hallway, parking lot, entrance, etc.)
   - Purpose (overview, face recognition, license plates, etc.)
   - Environmental factors (lighting, motion level)
   - Constraints (bandwidth budget, retention requirements)
   - Optional sample frame upload

2. **Results Panel (Right Panel)** - Displays generated recommendations as JSON:
   - Stream settings (resolution, codec, FPS, bitrate)
   - Exposure settings (shutter, WDR, backlight compensation)
   - Low-light settings (IR mode, noise reduction)
   - Image processing (sharpening, contrast)
   - Recording parameters
   - Context-specific notes and warnings

3. **Recommendation Engine** (`basicHeuristicEngine` function):
   - Currently uses rule-based heuristics
   - Adjusts settings based on scene type, purpose, lighting, and motion
   - Handles constraint violations (bandwidth limits)
   - Generates human-readable notes for integrators
   - **TODO**: Replace with actual AI/backend API integration (see line 838-840)

### Key Functions

- `basicHeuristicEngine(input)` (line 597-773): Core logic that generates camera settings based on form inputs
- `buildInputFromForm()` (line 775-796): Extracts and normalizes form data
- `buildOutputPayload(input, settings)` (line 798-820): Constructs final JSON output with metadata
- `setStatus(mode, message)` (line 580-586): Updates UI status indicator
- `showToast(message, ok)` (line 588-595): Displays temporary notification

## Development Workflow

### Running Locally

Simply open `index.html` in a web browser:
```bash
# On Windows
start index.html

# On macOS
open index.html

# On Linux
xdg-open index.html
```

Or use a simple HTTP server if needed:
```bash
# Python 3
python -m http.server 8000

# Python 2
python -m SimpleHTTPServer 8000
```

### Deployment

This is a GitHub Pages site. Push to the `main` branch to deploy:
```bash
git add .
git commit -m "Update application"
git push origin main
```

## Code Modification Guidelines

### Adding New Scene Types

1. Add option to the `#scene-type` select element (line 427-436)
2. Add corresponding case in `basicHeuristicEngine` switch statement (line 646-687)
3. Define appropriate default settings for that scene type

### Adding New Purposes

1. Add option to the `#purpose` select element (line 440-447)
2. Add corresponding case in purpose switch statement (line 690-718)
3. Adjust FPS, bitrate, shutter speed, and add relevant notes

### Modifying Recommendation Logic

The core logic is in `basicHeuristicEngine()` (line 597-773). Settings are adjusted in this order:
1. Initialize with baseline defaults
2. Apply scene-type adjustments
3. Apply purpose adjustments
4. Apply lighting adjustments
5. Apply motion-level adjustments
6. Enforce bandwidth constraints
7. Add retention notes

### Future AI Integration

The placeholder for backend integration is at line 838-840. To connect to an AI backend:
```javascript
const response = await fetch("/api/optimize", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(input)
});
const { settings } = await response.json();
```

## Domain-Specific Context

### Surveillance Camera Settings

- **WDR (Wide Dynamic Range)**: Handles high-contrast scenes (bright windows in dark rooms)
- **IR (Infrared)**: Night vision illumination
- **Shutter Speed**: Faster (1/250-1/500) prevents motion blur but requires more light
- **Bitrate**: Higher quality requires more bandwidth and storage
- **H.265 vs H.264**: H.265 offers ~50% better compression but requires more processing
- **FPS (Frames Per Second)**: Higher is better for fast motion but increases bandwidth

### VMS Platforms

Supported platforms (line 413-420):
- Avigilon ACC
- Genetec Security Center
- Milestone XProtect
- Exacq
- Hanwha WAVE

### Typical Trade-offs

The engine balances:
1. **Image quality vs storage** - higher bitrate = better quality but more storage
2. **Motion clarity vs low-light performance** - fast shutter reduces blur but needs more light
3. **Bandwidth vs retention** - must fit within network and storage constraints
4. **Detail vs coverage** - face/plate recognition needs higher FPS and faster shutter

## File References

- Main application: `index.html` (single file containing everything)
- Deployment marker: `.nojekyll` (GitHub Pages configuration)
