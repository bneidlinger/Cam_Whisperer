# Changelog

All notable changes to CamOpt AI will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Planned for v0.4.0
- Database layer implementation (PostgreSQL/SQLite)
- Camera inventory persistence
- Optimization history storage
- User authentication (JWT)
- Production deployment (Render/Railway)
- Complete imaging settings apply (video source token integration)

### Planned for v0.5.0
- Camera health monitoring
- Periodic snapshot capture
- Configuration drift detection
- Automated re-optimization triggers
- Multi-camera site optimization

### Planned for v0.6.0
- VMS SDK integration (Genetec, Milestone, Avigilon)
- Advanced analytics and reporting
- Fleet management dashboard
- Mobile-responsive UI

---

## [0.3.0] - 2025-12-06

### 🎉 Major Features

#### Hanwha WAVE VMS Integration (Phase 5 - VMS)
- **Added** Complete Hanwha WAVE VMS integration for enterprise deployments
- **Added** WAVE REST API client with HTTP Digest authentication
- **Added** Camera discovery via WAVE API
- **Added** Camera settings query via WAVE
- **Added** Camera settings application via WAVE with job tracking
- **Added** Settings verification and format conversion (CamOpt ↔ WAVE)
- **Added** VMS-managed camera workflow support
- **Implemented** `GET /api/wave/discover` endpoint
- **Implemented** `GET /api/wave/cameras/{id}/capabilities` endpoint
- **Implemented** `GET /api/wave/cameras/{id}/current-settings` endpoint
- **Updated** `POST /api/apply` to support VMS integration

**Key Capabilities:**
- Discover all cameras registered in WAVE system
- Query camera capabilities and current configuration
- Apply optimized settings through WAVE VMS
- Job-based tracking with progress monitoring
- Automatic settings verification
- Support for WAVE 4.0+ servers

**API Features:**
- HTTP Digest authentication
- Self-signed SSL certificate support
- Async/await throughout
- ThreadPoolExecutor for blocking HTTP calls
- Comprehensive error handling
- Settings format conversion

### 🔧 Backend Infrastructure

#### New Integration Layer
- **Created** `backend/integrations/hanwha_wave_client.py` (~700 lines)
  - Full REST API client for Hanwha WAVE VMS
  - Camera discovery and enumeration
  - Settings query and application
  - Snapshot retrieval
  - Server info queries

#### Enhanced Services
- **Updated** `backend/services/discovery.py` (+170 lines)
  - `discover_wave_cameras()` - List cameras from WAVE
  - `get_wave_camera_capabilities()` - Query camera capabilities
  - `get_wave_current_settings()` - Get current configuration

- **Updated** `backend/services/apply.py` (+300 lines)
  - `apply_settings_vms()` - VMS router method
  - `_apply_settings_wave()` - WAVE-specific apply with job tracking
  - `_verify_wave_settings()` - Settings verification
  - Settings format conversion (CamOpt ↔ WAVE)

#### API Endpoints
- **Updated** `backend/main.py` (+150 lines)
  - New WAVE-specific endpoints
  - Enhanced VMS apply endpoint
  - Improved credential handling

### 🧪 Testing & Documentation

#### Test Infrastructure
- **Created** `backend/test_wave.ps1` (~400 lines)
  - Comprehensive PowerShell test script
  - Tests all WAVE endpoints
  - Job tracking validation
  - Settings verification
  - Colored output and test summary

#### Documentation
- **Created** `backend/WAVE_INTEGRATION.md` (~600 lines)
  - Complete integration guide
  - API reference with examples
  - Configuration instructions
  - Troubleshooting guide
  - Performance benchmarks
  - Security considerations

- **Created** `backend/WAVE_TESTING_GUIDE.md` (~300 lines)
  - Step-by-step testing instructions
  - Manual and automated testing methods
  - Expected results and benchmarks
  - Production readiness checklist

### 📊 Performance

**Benchmarks (WAVE 5.1, 50 cameras):**
| Operation | Typical Time |
|-----------|--------------|
| Camera discovery | 2-5s |
| Capabilities query | 1-2s |
| Settings query | 1-2s |
| Settings apply | 3-5s |
| Total apply workflow | 5-10s |

### 🔒 Security

- ✅ HTTP Digest authentication (secure)
- ✅ SSL/TLS support (HTTPS)
- ✅ Self-signed certificate handling
- ✅ Credentials not stored in memory
- ✅ Input validation with Pydantic
- ✅ Comprehensive error handling

### 📈 Metrics

**Code:**
- WAVE client: ~700 lines
- Service updates: ~470 lines
- API endpoints: ~150 lines
- Test scripts: ~400 lines
- Documentation: ~900 lines
- **Total:** ~2,620 lines

**API Coverage:**
- 8/11 endpoints implemented (73%)
- Up from 5/11 in v0.2.0 (45%)

**VMS Support:**
- ✅ Hanwha WAVE (full support)
- ⏳ Genetec (planned v0.6.0)
- ⏳ Milestone (planned v0.6.0)

### 🎯 Integration Workflow

**Complete VMS Workflow:**
```
1. Discover cameras from WAVE → GET /api/wave/discover
2. Query current settings → GET /api/wave/cameras/{id}/current-settings
3. Optimize with Claude Vision → POST /api/optimize
4. Apply via WAVE → POST /api/apply (applyVia: "vms")
5. Track progress → GET /api/apply/status/{job_id}
6. Verify settings → Automatic verification
```

### 🐛 Bug Fixes

None - new feature implementation

### ⚠️ Known Limitations

- ❌ Imaging settings (exposure, WDR) not applied via WAVE (camera manages these)
- ❌ Camera add/remove operations not supported
- ❌ User management not implemented
- ❌ Recording playback not supported
- ⚠️ Requires WAVE 4.0 or higher
- ⚠️ Self-signed SSL certificates require `verify_ssl=False`

### 🔄 Breaking Changes

None - additive features only

### 📚 Documentation Updates

- Added comprehensive WAVE integration guide
- Added WAVE testing guide
- Updated API specification (implied)
- Added VMS comparison matrix

### 🙏 Acknowledgments

**Technologies:**
- Hanwha WAVE VMS for excellent REST API
- Python requests library for HTTP client
- FastAPI for clean async API design

**References:**
- WAVE Server HTTP REST API documentation
- WAVE SDK/API documentation
- Wisenet WAVE VMS feature documentation

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

- **v0.3.0** (2025-12-06) - Hanwha WAVE VMS Integration [Current]
- **v0.2.0-alpha** (2025-12-06) - AI + ONVIF Integration
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
**Current Version:** 0.3.0
