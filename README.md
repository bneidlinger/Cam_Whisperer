```
╔═══════════════════════════════════════════════════════════════════════════╗
║                                                                           ║
║   ██████╗ █████╗ ███╗   ███╗ ██████╗ ██████╗ ████████╗    █████╗ ██╗    ║
║  ██╔════╝██╔══██╗████╗ ████║██╔═══██╗██╔══██╗╚══██╔══╝   ██╔══██╗██║    ║
║  ██║     ███████║██╔████╔██║██║   ██║██████╔╝   ██║      ███████║██║    ║
║  ██║     ██╔══██║██║╚██╔╝██║██║   ██║██╔═══╝    ██║      ██╔══██║██║    ║
║  ╚██████╗██║  ██║██║ ╚═╝ ██║╚██████╔╝██║        ██║      ██║  ██║██║    ║
║   ╚═════╝╚═╝  ╚═╝╚═╝     ╚═╝ ╚═════╝ ╚═╝        ╚═╝      ╚═╝  ╚═╝╚═╝    ║
║                                                                           ║
║                   CAMERA SETTINGS OPTIMIZATION SYSTEM                     ║
║                              Version 0.1                                  ║
║                                                                           ║
╚═══════════════════════════════════════════════════════════════════════════╝

CLASSIFICATION: UNCLASSIFIED / INTEGRATOR USE ONLY
SYSTEM TYPE:    Video Management System Configuration Assistant
DATE:           2024-CURRENT
STATUS:         PROTOTYPE - HEURISTIC ENGINE ACTIVE
```

## MISSION STATEMENT

> **Every camera has a platonic state, and it actually can and should be achieved at all times.**

The gap between factory defaults and optimal field performance is where 70% of video surveillance failures occur. CamOpt AI exists to close that gap.

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

CamOpt AI provides integrators with **deterministic starting configurations** based on:

- **Scene Classification** (hallway, parking lot, entrance, perimeter, etc.)
- **Operational Purpose** (overview, face recognition, license plate capture, evidence-grade)
- **Environmental Factors** (lighting variance, motion levels, contrast extremes)
- **Resource Constraints** (bandwidth budgets, retention requirements, VMS platform)

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

### Local Operation

```bash
# Clone the repository
git clone https://github.com/bneidlinger/cam_whisperer.git
cd cam_whisperer

# Open in browser (no build process required)
open index.html
```

### Live Deployment

**SYSTEM ONLINE:** https://bneidlinger.github.io/cam_whisperer/

The application is currently deployed and operational via GitHub Pages. No server-side processing required.

## USAGE PROTOCOL

```
STEP 1: Input Camera Context
        ├── Site identification
        ├── Camera model (if known)
        ├── Scene type selection
        ├── Primary operational purpose
        ├── Lighting/motion characteristics
        └── Bandwidth and retention constraints

STEP 2: Generate Recommendations
        └── Execute heuristic engine

STEP 3: Review Output
        ├── Examine recommended settings
        ├── Read integrator notes
        └── Verify against deployment constraints

STEP 4: Apply to Camera/VMS
        ├── Use settings as initial configuration
        ├── Fine-tune based on live footage review
        └── Document final settings for site records
```

## TECHNICAL SPECIFICATIONS

```
┌─────────────────────────────────────────────────────────────┐
│ APPLICATION STACK                                            │
├─────────────────────────────────────────────────────────────┤
│  Frontend:      Pure HTML5 / CSS3 / JavaScript (ES6+)       │
│  Dependencies:  None                                         │
│  Backend:       None (client-side heuristics)                │
│  Build Process: None required                                │
│  Runtime:       Modern web browser (Chrome, Firefox, Safari) │
└─────────────────────────────────────────────────────────────┘
```

## CURRENT LIMITATIONS

```
[!] PROTOTYPE STATUS
    └── Current engine uses rule-based heuristics, not AI inference

[!] NO BACKEND INTEGRATION
    └── Placeholder for future AI model integration (see index.html:838-840)

[!] NO IMAGE ANALYSIS
    └── Sample frame upload UI present but not processed

[!] NO STORAGE CALCULATOR
    └── Retention targets noted but not validated against actual capacity
```

## FUTURE ROADMAP

```
PHASE 2: AI MODEL INTEGRATION
         └── Replace heuristic engine with trained model
         └── Backend API for inference
         └── Sample frame analysis for scene validation

PHASE 3: ADVANCED FEATURES
         └── Multi-camera site optimization
         └── Storage capacity calculator
         └── VMS-specific export formats
         └── Historical tuning data analysis

PHASE 4: FIELD VALIDATION
         └── Integration with actual VMS platforms
         └── A/B testing framework
         └── Feedback loop from deployed cameras
```

## PHILOSOPHICAL FOUNDATION

The concept of the **platonic camera state** acknowledges that:

1. Every surveillance camera has an ideal configuration for its specific deployment context
2. This ideal state is deterministic and knowable
3. Deviation from this state results in preventable failures
4. Factory defaults are, by definition, suboptimal for any specific deployment
5. Integrator expertise should be encoded, not rediscovered on every job

CamOpt AI is the first step toward **universal camera optimization** - where every camera, everywhere, operates at its theoretical best.

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

[Specify license here]

## CONTACT

```
REPOSITORY: https://github.com/bneidlinger/cam_whisperer
ISSUES:     https://github.com/bneidlinger/cam_whisperer/issues
LIVE DEMO:  https://bneidlinger.github.io/cam_whisperer/
```

For issues, feature requests, or integration questions, file a report via GitHub Issues.

---

**END OF DOCUMENT**

```
TRANSMISSION COMPLETE
SYSTEM READY
```
