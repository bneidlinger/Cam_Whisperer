# Changelog

All notable changes to CamOpt AI will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Planned for v0.3.0
- Database layer implementation (PostgreSQL/SQLite)
- Camera inventory persistence
- Optimization history storage
- User authentication (JWT)
- Production deployment (Render/Railway)
- Complete imaging settings apply (video source token integration)

### Planned for v0.4.0
- Camera health monitoring
- Periodic snapshot capture
- Configuration drift detection
- Automated re-optimization triggers
- Multi-camera site optimization

### Planned for v0.5.0
- VMS SDK integration (Genetec, Milestone, Avigilon)
- Advanced analytics and reporting
- Fleet management dashboard
- Mobile-responsive UI

---

## [0.2.0-alpha] - 2025-12-06

### 🎉 Major Features

#### Claude Vision AI Integration (Phase 2)
- **Added** Anthropic Claude Sonnet 4.5 Vision integration for camera optimization
- **Added** Sample frame analysis (base64 image upload)
- **Added** Context-aware camera settings recommendations
- **Added** Confidence scoring (0.0-1.0 range)
- **Added** Detailed technical explanations for recommendations
- **Added** Automatic heuristic fallback when AI unavailable
- **Added** Processing time tracking
- **Implemented** `POST /api/optimize` endpoint

**Test Results:**
- Average confidence: 83.3%
- Average processing time: 8-10 seconds
- Success rate: 100% (3/3 tests)

#### ONVIF Camera Integration (Phase 4)
- **Added** Camera discovery via WS-Discovery protocol
- **Added** Device information query (manufacturer, model, firmware)
- **Added** Camera capabilities detection (codecs, resolutions, FPS)
- **Added** Current settings query from cameras
- **Added** Settings apply to cameras with verification
- **Added** Job-based apply tracking with progress monitoring
- **Implemented** `GET /api/discover` endpoint
- **Implemented** `GET /api/cameras/{id}/capabilities` endpoint
- **Implemented** `GET /api/cameras/{id}/current-settings` endpoint
- **Implemented** `POST /api/apply` endpoint
- **Implemented** `GET /api/apply/status/{job_id}` endpoint

**Supported Operations:**
- Camera discovery (WS-Discovery)
- Stream settings apply (resolution, codec, FPS, bitrate)
- Settings verification
- Error handling and recovery

#### Retro Industrial UI
- **Added** 80's security-themed industrial design
- **Added** Industrial orange color scheme (#ff6b1a)
- **Added** CRT scan line visual effects
- **Added** Grid background pattern
- **Added** Terminal green output display (#00ff41)
- **Added** Glowing status indicators
- **Added** Real-time optimization feedback
- **Added** Confidence score display
- **Added** AI provider badge (Claude vs Heuristic)

### 🔧 Backend Infrastructure

#### Services Layer
- **Created** `backend/services/optimization.py` - Optimization service
- **Created** `backend/services/discovery.py` - Camera discovery service
- **Created** `backend/services/apply.py` - Settings apply service
- **Created** `backend/integrations/claude_client.py` - Claude Vision API client
- **Created** `backend/integrations/onvif_client.py` - ONVIF protocol client

#### Configuration & Environment
- **Created** `backend/config.py` - Pydantic-based settings management
- **Created** `backend/.env.example` - Environment variable template
- **Created** `backend/.gitignore` - Security and cleanup rules
- **Added** CORS middleware configuration
- **Added** Structured logging

#### Startup Scripts
- **Created** `backend/start.bat` - Windows batch startup script
- **Created** `backend/start.ps1` - PowerShell startup script
- **Added** Automatic virtual environment activation
- **Added** Server status display

### 🧪 Testing & Tracking

#### Test Tracking System
- **Created** `backend/test_tracker.py` - Test result analysis tool
- **Created** `backend/save_test_result.py` - Result save helper
- **Created** `backend/convert_image.py` - Image to base64 converter
- **Created** `backend/test_onvif.ps1` - Comprehensive ONVIF test suite
- **Added** Automated test log generation (`test_log.json`)
- **Added** Markdown report generation (`TEST_REPORT.md`)
- **Added** Confidence trend analysis
- **Added** Provider comparison

#### Test Infrastructure
- **Created** `backend/ai_outputs/` directory for test results
- **Created** `backend/ai_outputs/README.md` - Testing workflow guide
- **Added** Manual test tracking (file-based)

### 📚 Documentation

#### Planning & Architecture
- **Created** `DEVELOPMENT_PLAN.md` - Complete development roadmap
- **Created** `QUICKSTART.md` - 15-minute setup guide
- **Created** `backend/ARCHITECTURE.md` - System architecture documentation
- **Created** `backend/API_SPECIFICATION.md` - Complete API reference
- **Created** `backend/DATABASE_SCHEMA.md` - Database design documentation
- **Created** `backend/README.md` - Backend development guide

#### ONVIF Integration
- **Created** `backend/ONVIF_TESTING.md` - ONVIF testing guide
- **Created** `backend/ONVIF_INTEGRATION_SUMMARY.md` - Implementation summary
- **Created** `backend/TESTING_COMPLETE.md` - Testing status document

#### Project Management
- **Created** `STATUS_CHECK.md` - Development status comparison
- **Created** `SYSTEM_REVIEW.md` - Comprehensive system review
- **Created** `CHANGELOG.md` - This file
- **Updated** `README.md` - Reflect v0.2 features and architecture

### 🐛 Bug Fixes

- **Fixed** Pydantic validation errors with extra .env fields
- **Fixed** CORS issues with file:// protocol
- **Fixed** Unicode encoding errors on Windows (test tracker)
- **Fixed** Pillow wheel build errors (upgraded pip first)
- **Fixed** WSDiscovery import handling with graceful fallback

### ⚙️ Dependencies

#### Added
- `anthropic==0.42.0` - Claude Vision API
- `WSDiscovery==2.0.0` - ONVIF camera discovery
- `onvif-zeep==0.2.12` - ONVIF protocol support
- `zeep==4.3.1` - SOAP client for ONVIF
- `pydantic-settings==2.6.1` - Settings management
- `python-multipart==0.0.20` - File upload support

#### Updated
- `pillow>=10.0.0` - Use latest compatible version

### 🔒 Security

- **Added** `.gitignore` to prevent committing secrets
- **Added** `.env.example` template (no actual keys)
- **Added** Pydantic validation for all inputs
- **Added** CORS origin restrictions
- **Added** Logging without sensitive data

### 📊 Performance

- **Optimized** Async/await throughout backend
- **Added** ThreadPoolExecutor for blocking ONVIF calls
- **Added** Concurrent camera discovery support
- **Added** Request timeout handling (prevents hanging)

### 🎨 UI/UX

- **Redesigned** Entire frontend with retro aesthetic
- **Added** Real-time status updates
- **Added** Error message display
- **Added** Processing time display
- **Added** Confidence score visualization
- **Improved** Form validation and feedback

### 📈 Metrics

**Code:**
- Backend: ~2,560 lines of Python
- Frontend: ~1,000 lines of HTML/CSS/JS
- Documentation: ~5,180 lines
- Total: ~7,740 lines

**API Coverage:**
- 5/11 endpoints implemented (45%)
- Up from 1/11 in v0.1 (9%)

**Phase Completion:**
- Phase 1 (Database): 30%
- Phase 2 (Claude Vision): 71% ✅
- Phase 3 (Frontend): 73% ✅
- Phase 4 (ONVIF): 91% ✅
- Overall MVP: ~55%

### ⚠️ Known Limitations

- **No database persistence** - All data in-memory only
- **No user authentication** - Single-user prototype
- **ONVIF imaging settings incomplete** - Need video source token
- **No production deployment** - Local development only
- **No camera monitoring** - Phase 5 not started
- **No unit tests** - Manual testing only

### 🔮 Breaking Changes

None - First alpha release

### 🗑️ Deprecated

None - First alpha release

### 🔄 Migration Notes

**From v0.1 to v0.2:**

1. **Backend Setup Required:**
   ```bash
   cd backend
   python -m venv venv
   venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Environment Configuration:**
   ```bash
   cp .env.example .env
   # Edit .env and add ANTHROPIC_API_KEY
   ```

3. **Start Backend:**
   ```bash
   uvicorn main:app --reload
   ```

4. **Serve Frontend:**
   ```bash
   python -m http.server 3000
   ```

5. **Access:**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Docs: http://localhost:8000/docs

---

## [0.1.0] - 2025-12-05

### Initial Prototype

- **Created** Static single-page web application
- **Added** Client-side heuristic engine (JavaScript)
- **Added** Camera optimization form
- **Added** JSON output display
- **Added** Basic scene type and purpose selection
- **Added** Bandwidth and retention constraint handling
- **Created** Initial README and whitepaper
- **Deployed** to GitHub Pages (static)

**Features:**
- Rule-based camera settings generation
- No backend required
- No AI integration
- No camera integration

**Status:** Proof of concept

---

## Version History

- **v0.2.0-alpha** (2025-12-06) - AI + ONVIF Integration [Current]
- **v0.1.0** (2025-12-05) - Initial Static Prototype

---

## Semantic Versioning

**Version Format:** MAJOR.MINOR.PATCH-LABEL

- **MAJOR:** Breaking changes, incompatible API changes
- **MINOR:** New features, backwards-compatible
- **PATCH:** Bug fixes, backwards-compatible
- **LABEL:** alpha, beta, rc (release candidate), or none (stable)

**Example:**
- `0.2.0-alpha` - Alpha release with new features
- `0.2.1-alpha` - Alpha with bug fixes
- `0.3.0-beta` - Beta release with new features
- `1.0.0` - First stable release

---

## Release Notes Template

```markdown
## [X.Y.Z] - YYYY-MM-DD

### Added
- New features

### Changed
- Changes to existing features

### Deprecated
- Features being phased out

### Removed
- Removed features

### Fixed
- Bug fixes

### Security
- Security fixes
```

---

**Maintained by:** CamOpt AI Development Team
**Last Updated:** 2025-12-06
**Current Version:** 0.2.0-alpha
