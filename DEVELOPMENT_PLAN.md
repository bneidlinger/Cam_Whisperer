# CamOpt AI - Development Plan to Testing Phase

**Status:** Planning Complete ✅
**Next Phase:** Implementation
**Target:** Working prototype ready for field testing

---

## Executive Summary

This document outlines the development path from the current v0.1 static prototype to a fully functional MVP ready for testing with real cameras. The plan focuses on **Claude Vision AI integration** as the core optimization engine, with ONVIF camera integration for hardware control.

**Timeline Estimate:** 4 weeks to testable MVP
**Key Technologies:** FastAPI, Claude Sonnet 4.5, ONVIF, PostgreSQL

---

## Current State (v0.1)

### What We Have
✅ Single-page web UI (`index.html`)
✅ Client-side heuristic engine (JavaScript)
✅ FastAPI backend skeleton (`backend/main.py`)
✅ Comprehensive whitepaper architecture
✅ Complete planning documentation

### What We Need
❌ AI integration (Claude Vision)
❌ Database layer
❌ Camera discovery/integration
❌ Frontend-backend connection
❌ Deployment infrastructure

---

## MVP Testing Goals

### Must-Have Features

1. **Manual Camera Registration**
   - User can input camera details via web form
   - Store camera inventory in database

2. **AI-Powered Optimization**
   - Upload sample frame from camera
   - Claude Vision analyzes image + context
   - Generate optimized settings with explanation

3. **Settings Export**
   - Human-readable JSON output
   - Copy/paste friendly format
   - Integrator notes and warnings

4. **Basic Camera Integration**
   - ONVIF discovery (at least one camera)
   - Apply settings via ONVIF
   - Verify configuration applied

5. **Health Check**
   - Capture snapshot from camera
   - Basic quality metrics (brightness, noise)
   - Flag anomalies

### Nice-to-Have (Future)

- Multi-VMS support (beyond ONVIF)
- Automated network scanning
- Continuous monitoring loop
- Fleet management dashboard
- Historical analytics

---

## Implementation Phases

### PHASE 1: Backend Foundation (Week 1)

**Goal:** Runnable backend with database and config management

**Tasks:**
1. Database setup
   - [x] Create SQLAlchemy models (`models.py`)
   - [ ] Set up database connection (`database.py`)
   - [ ] Initialize SQLite for development
   - [ ] Create Alembic migrations
   - [ ] Seed sample data

2. Configuration management
   - [x] Environment variables (`.env`)
   - [ ] Config class (`config.py`)
   - [ ] Logging setup
   - [ ] Error handling middleware

3. File storage
   - [ ] Create uploads directory structure
   - [ ] Image processing utilities
   - [ ] File cleanup jobs

**Deliverable:** Backend starts without errors, database initialized

**Test:** `pytest tests/test_database.py`

---

### PHASE 2: Claude Vision Integration (Week 1-2)

**Goal:** AI optimization endpoint returns real Claude recommendations

**Tasks:**
1. Anthropic API client
   - [ ] Create `integrations/claude_client.py`
   - [ ] Implement vision API call
   - [ ] Handle base64 image encoding
   - [ ] Parse structured JSON response
   - [ ] Add retry logic + timeout

2. Prompt engineering
   - [ ] Design system prompt for camera optimization
   - [ ] Create few-shot examples
   - [ ] Test prompt variations
   - [ ] Tune temperature/tokens

3. Optimization service
   - [ ] Update `/api/optimize` endpoint
   - [ ] Integrate Claude client
   - [ ] Add heuristic fallback
   - [ ] Store optimization history in DB
   - [ ] Calculate confidence scores

4. Testing
   - [ ] Test with sample camera images
   - [ ] Validate output format
   - [ ] Measure response times
   - [ ] Test error handling

**Deliverable:** `/api/optimize` returns Claude Vision recommendations

**Example Prompt:**
```
You are an expert surveillance camera optimization engineer with 20+ years of field experience.

SCENE ANALYSIS:
Analyze the attached camera frame and identify:
- Lighting conditions (bright/dark/high contrast/WDR needed)
- Motion characteristics (static/low/medium/high motion)
- Key areas of interest (entry points, faces, license plates)
- Environmental challenges (glare, shadows, weather)

CAMERA CONTEXT:
- Location: {location}
- Scene Type: {sceneType}
- Purpose: {purpose}
- Current Settings: {currentSettings}
- Constraints: {bandwidthLimit} Mbps, {retentionDays} days retention

TASK:
Generate optimal camera settings that:
1. Maximize evidence quality for the stated purpose
2. Stay within bandwidth/storage constraints
3. Handle the lighting conditions visible in the frame
4. Prevent common deployment mistakes (motion blur, noise, etc.)

Return settings in this exact JSON structure:
{
  "stream": {
    "resolution": "1920x1080",
    "codec": "H.265",
    "fps": 20,
    "bitrateMbps": 3.5,
    "keyframeInterval": 40,
    "cbr": true
  },
  "exposure": {
    "shutter": "1/250",
    "iris": "Auto",
    "gainLimit": "36dB",
    "wdr": "High",
    "backlightComp": "Off"
  },
  "lowLight": {
    "irMode": "Auto",
    "irIntensity": "Medium",
    "noiseReduction": "Low",
    "slowShutter": "Off"
  },
  "image": {
    "sharpening": "High",
    "contrast": "55",
    "saturation": "50"
  },
  "warnings": [
    "List of warnings or constraint violations"
  ],
  "explanation": "Detailed justification for key settings (2-3 paragraphs)"
}

Be specific and technical. Explain trade-offs made.
```

**Test Criteria:**
- ✅ Response time < 15 seconds
- ✅ Valid JSON structure
- ✅ Explanation is detailed and relevant
- ✅ Settings respect hardware constraints
- ✅ Confidence score is reasonable (0.7-0.9 for good scenes)

---

### PHASE 3: Frontend-Backend Integration (Week 2)

**Goal:** Web UI calls backend API instead of local heuristics

**Tasks:**
1. Update `index.html`
   - [ ] Replace heuristic engine with API call
   - [ ] Add loading states
   - [ ] Handle API errors gracefully
   - [ ] Show AI provider badge (Claude vs Heuristic)
   - [ ] Display confidence score

2. API endpoint configuration
   - [ ] Development: `http://localhost:8000`
   - [ ] Production: `https://api.camopt.ai` (or similar)
   - [ ] Environment detection

3. Enhanced UI features
   - [ ] Before/after settings comparison
   - [ ] Explanation in readable format
   - [ ] Copy settings to clipboard
   - [ ] Download JSON file
   - [ ] Show processing time

**Deliverable:** End-to-end optimization flow works

**Test:** User can upload image, get AI recommendations, export JSON

---

### PHASE 4: ONVIF Camera Integration (Week 3)

**Goal:** Connect to real camera, apply settings, verify

**Tasks:**
1. ONVIF discovery
   - [ ] Implement WS-Discovery scan
   - [ ] Parse ONVIF device info
   - [ ] Query capabilities
   - [ ] Store in database

2. Settings query
   - [ ] GetVideoEncoderConfigurations
   - [ ] GetImagingSettings
   - [ ] Map to CamOpt data model

3. Settings apply
   - [ ] SetVideoEncoderConfiguration
   - [ ] SetImagingSettings
   - [ ] Verification query
   - [ ] Error handling

4. Integration testing
   - [ ] Test with Hanwha camera
   - [ ] Test with Axis camera
   - [ ] Test with Hikvision camera
   - [ ] Document vendor quirks

**Deliverable:** `/api/apply` works with at least one physical camera

**Required Hardware:**
- 1-3 IP cameras (ONVIF-compliant)
- Network switch
- Computer on same network

**Test Scenario:**
1. Discover camera on network
2. Query current settings
3. Generate AI recommendations
4. Apply new settings via ONVIF
5. Verify settings were applied
6. Capture snapshot to confirm quality

---

### PHASE 5: Monitoring & Health (Week 3-4)

**Goal:** Basic quality assessment for deployed cameras

**Tasks:**
1. Snapshot capture
   - [ ] GetSnapshotUri from camera
   - [ ] Download and store image
   - [ ] Generate thumbnail

2. Quality metrics
   - [ ] Brightness histogram analysis
   - [ ] Noise level detection (variance)
   - [ ] Blur detection (edge sharpness)
   - [ ] Store metrics in DB

3. Anomaly detection
   - [ ] Too dark/bright thresholds
   - [ ] High noise warning
   - [ ] Configuration drift detection
   - [ ] Re-optimization trigger

4. Health endpoint
   - [ ] `/api/cameras/{id}/health`
   - [ ] Return health status + metrics
   - [ ] Recommendations for improvement

**Deliverable:** Health monitoring works for one camera

**Test:** System detects when camera settings degrade over time

---

### PHASE 6: Deployment & Testing (Week 4)

**Goal:** Production deployment, end-to-end testing

**Tasks:**
1. Backend deployment
   - [ ] Choose platform (Render, Railway, Fly.io)
   - [ ] Set up PostgreSQL database
   - [ ] Configure environment variables
   - [ ] Deploy FastAPI app
   - [ ] Set up SSL/HTTPS

2. Frontend deployment
   - [ ] Update API endpoint to production URL
   - [ ] Deploy to GitHub Pages
   - [ ] Test CORS configuration
   - [ ] Verify end-to-end flow

3. Documentation
   - [ ] User guide for integrators
   - [ ] API documentation (auto-generated via FastAPI)
   - [ ] Troubleshooting guide
   - [ ] Sample camera configurations

4. Field testing
   - [ ] Test with 3+ different camera models
   - [ ] Test with 3+ different scene types
   - [ ] Compare AI recommendations to manual expert tuning
   - [ ] Collect feedback from integrators
   - [ ] Document success rate and edge cases

**Deliverable:** Deployed system accessible via URL

**Testing Readiness Checklist:**
- ✅ User can access web UI from any browser
- ✅ Backend responds to API calls
- ✅ Database persists data
- ✅ Claude API integration works
- ✅ ONVIF camera apply works
- ✅ Error handling is graceful
- ✅ Documentation is complete

---

## Technical Architecture

### Stack Summary

```
Frontend:   HTML5 + Vanilla JS (GitHub Pages)
Backend:    FastAPI + Python 3.10+ (Render/Railway)
Database:   PostgreSQL (production) / SQLite (dev)
AI:         Claude Sonnet 4.5 (Anthropic)
Camera:     ONVIF protocol
Deployment: Render (backend) + GitHub Pages (frontend)
```

### Data Flow

```
User → Web UI → Backend API → Claude Vision → Recommendations
                    ↓                              ↓
              Database (store)              User reviews
                                                   ↓
              Apply Service ← User approves ←─────┘
                    ↓
              ONVIF Client → IP Camera (apply settings)
                    ↓
              Verify → Snapshot → Health metrics
```

---

## Key Decision Points

### 1. AI Provider: Claude Sonnet 4.5 ✅

**Why Claude:**
- Vision capability (analyze sample frames)
- Excellent structured output (JSON)
- Better price/performance than GPT-4V
- Strong reasoning for complex trade-offs

**Alternative considered:** OpenAI GPT-4 Vision
**Decision:** Claude for MVP, can add GPT-4 as fallback later

---

### 2. Database: PostgreSQL ✅

**Why PostgreSQL:**
- JSONB support for flexible settings storage
- Excellent for production scale
- Free tier on Render/Railway
- SQLite compatibility for local dev

**Alternative considered:** MongoDB
**Decision:** PostgreSQL (relational structure better for camera inventory)

---

### 3. Camera Integration: ONVIF First ✅

**Why ONVIF:**
- Universal standard (most cameras)
- No vendor-specific SDKs needed
- Good Python library (onvif-zeep)
- Easier to test and debug

**Alternative considered:** VMS SDKs (Genetec, Milestone)
**Decision:** ONVIF for MVP, VMS SDKs in Phase 2

---

### 4. Deployment: Render ✅

**Why Render:**
- Free tier for testing
- PostgreSQL included
- Easy Python deployment
- Auto-deploy from Git

**Alternative considered:** Railway, Fly.io, AWS
**Decision:** Render for simplicity, can migrate later if needed

---

## Success Metrics

### Technical Metrics

- **API Response Time:** < 15 seconds for optimization
- **AI Success Rate:** > 90% valid responses
- **Apply Success Rate:** > 85% successful ONVIF applies
- **Uptime:** > 99% backend availability

### Business Metrics

- **Recommendation Acceptance:** > 70% of AI recommendations accepted by integrators
- **Quality Improvement:** Measurable improvement in footage quality
- **Time Savings:** < 5 minutes per camera vs 20+ minutes manual tuning
- **User Feedback:** Positive feedback from beta testers

---

## Risk Mitigation

### Risk 1: Claude API Rate Limits

**Mitigation:**
- Heuristic fallback engine (already implemented)
- Cache optimization results for 24 hours
- Request batching for multiple cameras

### Risk 2: ONVIF Incompatibility

**Mitigation:**
- Test with major vendors (Hanwha, Axis, Hikvision)
- Graceful degradation (manual config export)
- Document vendor-specific quirks

### Risk 3: Deployment Costs

**Mitigation:**
- Use free tiers initially (Render, Anthropic)
- Monitor API usage closely
- Implement rate limiting
- Offer self-hosted option for large deployments

---

## Next Actions

**Immediate (This Week):**
1. ✅ Review planning documents
2. [ ] Set up development environment (follow QUICKSTART.md)
3. [ ] Test backend skeleton
4. [ ] Get Anthropic API key
5. [ ] Implement Phase 1 (database layer)

**Week 2:**
- Implement Claude Vision integration
- Test with sample camera images
- Refine prompts

**Week 3:**
- ONVIF integration
- Test with physical camera
- Frontend-backend connection

**Week 4:**
- Deploy to production
- Field testing
- Documentation

---

## Resources

**Created Documentation:**
- ✅ [Quick Start Guide](QUICKSTART.md) - Get running in 15 minutes
- ✅ [Backend README](backend/README.md) - Backend development guide
- ✅ [Architecture Overview](backend/ARCHITECTURE.md) - System design
- ✅ [API Specification](backend/API_SPECIFICATION.md) - Complete API reference
- ✅ [Database Schema](backend/DATABASE_SCHEMA.md) - Database design

**External Resources:**
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Anthropic API Reference](https://docs.anthropic.com/claude/reference)
- [ONVIF Specifications](https://www.onvif.org/specs/)
- [SQLAlchemy 2.0 Guide](https://docs.sqlalchemy.org/en/20/)

---

## Questions & Support

**Technical Questions:**
- File issue on GitHub
- Check documentation first
- Review whitepaper for architecture context

**API Access:**
- Anthropic: https://console.anthropic.com/
- OpenAI (backup): https://platform.openai.com/

**Hardware Testing:**
- Need 1-3 ONVIF-compliant IP cameras
- Recommended: Hanwha, Axis, or Hikvision
- Can use ONVIF simulator for initial testing

---

**Document Status:** ✅ Complete
**Last Updated:** 2025-12-05
**Next Review:** After Phase 1 completion
