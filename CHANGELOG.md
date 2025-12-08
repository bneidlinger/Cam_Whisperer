# Changelog

All notable changes to PlatoniCam will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Added

#### Landing Page & Documentation
- **Added** `landing.html` - GitHub Pages landing/guide page
  - Interactive scenario simulator (Lobby, LPR, Perimeter, Retail)
  - Technology deep dive section (WDR, HLC, DNR, Smart Codec)
  - Manufacturer settings translation matrix (Hikvision, Axis, Dahua, Hanwha)
  - Storage/bandwidth calculator
  - PlatoniCam branding with dark theme and orange accents
  - Links to main app (`index.html`)

#### HLC (High Light Compensation) Support
- **Added** HLC field handling in `claude_provider.py`
- **Added** HLC to heuristic rules:
  - PLATES purpose: HLC On (masks headlight glare)
  - PARKING scene: HLC On (incoming vehicle headlights)
- **Updated** `_apply_purpose_rule()` to apply HLC settings
- **Updated** `_apply_scene_rule()` to apply HLC settings

#### Enhanced LPR/Plates Optimization
- **Enhanced** PLATES purpose rule with research-based settings:
  - FPS: 25 (up from 20)
  - Shutter: 1/500 (fixed, was range)
  - WDR: Off (prevents ghosting on fast-moving plates)
  - HLC: On (masks headlight glare)
  - Gain Limit: 24 dB (limits noise, prioritizes fast shutter)
  - Updated explanation with detailed reasoning

#### Storage Calculator (Frontend)
- **Added** "Calc" navigation item in sidebar
- **Added** Calculator section with inputs:
  - Number of cameras, resolution, FPS, recording hours
  - Codec type (H.264, H.265, H.265+/Zipstream)
  - Retention days, scene activity level
- **Added** Results panel: per-camera bitrate, total bandwidth, daily storage, total TB
- **Added** "Use Site Cameras" button to auto-populate camera count
- **Added** CSS styling for result display

#### UI Improvements
- **Added** `[?] GUIDE` link in main app header linking to landing page

### Changed
- **Updated** PARKING scene rule to include HLC

---

## [0.4.0] - 2025-12-07

### Added

#### Optimization Pipeline Infrastructure
- **Added** Complete pipeline data models (`backend/models/pipeline.py`)
  - Enums: `SceneType` (17 types), `CameraPurpose` (9 types), `ApplyMethod`, `ApplyStatus`
  - Camera models: `DiscoveredCamera`, `CameraCapabilities` with `from_dict()`/`to_dict()`
  - Settings models: `StreamSettings`, `ExposureSettings`, `LowLightSettings`, `ImageSettings`
  - Optimization models: `CameraContext`, `OptimizationContext`, `RecommendedSettings`, `OptimizationResult`
  - Apply models: `ApplyRequest`, `VerificationResult`, `ApplyResult`
  - `PipelineContext` class for request tracking, timing, and error accumulation

- **Added** Exception hierarchy with recovery hints (`backend/errors.py`)
  - Base: `PlatoniCamError` with `recoverable` flag and `recovery_hint`
  - Pipeline: `PipelineError` with stage tracking
  - Discovery: `DiscoveryError`, `NetworkScanError`, `VmsConnectionError`
  - Capability: `CapabilityQueryError`, `UnsupportedProtocolError`
  - Optimization: `OptimizationError`, `ProviderError`, `ProviderRateLimitError`, `ProviderAuthError`, `InvalidResponseError`, `ConstraintViolationError`
  - Apply: `ApplyError`, `PartialApplyError`, `ApplyTimeoutError`, `ApplyRollbackError`
  - Verification: `VerificationError`
  - Auth: `AuthenticationError`, `CameraAuthError`, `VmsAuthError`
  - Config: `ConfigurationError`, `MissingApiKeyError`

- **Added** Provider abstraction layer (`backend/services/providers/`)
  - `OptimizationProvider` abstract base class with capabilities
  - `ClaudeOptimizationProvider` - Claude Vision AI provider
  - `HeuristicOptimizationProvider` - Rule-based fallback with scene/purpose rules
  - `ProviderFactory` with auto-selection and fallback support
  - `ProviderCapability` enum: `SCENE_ANALYSIS`, `MULTI_CAMERA`, `CONSTRAINT_SOLVING`, `LEARNING`, `OFFLINE`

- **Added** Pipeline logging and metrics (`backend/services/pipeline_logger.py`)
  - `PipelineLogger` for structured request-scoped logging
  - `StageMetrics` and `PipelineMetrics` for timing
  - `@timed_stage` decorator for async functions
  - `configure_pipeline_logging()` setup function

#### Heuristic Provider Rules
- **Added** Purpose-based optimization rules (7 purposes)
  - PLATES: Fast shutter (1/250-1/500), 20+ FPS, slow shutter off
  - FACIAL: Fast shutter (1/250), 20+ FPS
  - EVIDENCE: CBR bitrate mode, H.265 codec
  - COUNTING, INTRUSION, GENERAL: Balanced settings

- **Added** Scene-type optimization rules (14 scenes)
  - ENTRANCE, LOBBY, LOADING_DOCK: High WDR
  - PARKING: Medium WDR, Auto IR
  - EXTERIOR_NIGHT: Auto IR, High DNR
  - RETAIL: Medium WDR, enhanced saturation
  - ATM, CASH_REGISTER: High WDR, fast shutter

### Changed

#### Refactored OptimizationService
- **Refactored** `backend/services/optimization.py` to use provider abstraction
- **Added** `optimize_typed()` method for typed interface
- **Maintained** Backward compatibility with dict-based `optimize()` method
- **Added** Automatic provider fallback on failure
- **Added** Pipeline error tracking in responses

### Technical Details

**New Files:**
- `backend/models/__init__.py` - Package exports
- `backend/models/pipeline.py` - ~600 lines of data models
- `backend/errors.py` - ~460 lines of exception hierarchy
- `backend/services/providers/__init__.py` - Package exports
- `backend/services/providers/base.py` - Abstract provider class
- `backend/services/providers/claude_provider.py` - Claude AI provider
- `backend/services/providers/heuristic_provider.py` - Rule-based provider
- `backend/services/providers/factory.py` - Provider factory
- `backend/services/pipeline_logger.py` - Logging infrastructure

**Code Metrics:**
- Models: ~600 lines
- Errors: ~460 lines
- Providers: ~650 lines
- Logger: ~200 lines
- Service refactor: ~100 lines
- **Total: ~2,010 new lines**

---

## [0.3.2] - 2025-12-07

### Changed

#### Rebranding
- **Renamed** Project from "CamOpt AI" to "PlatoniCam"
- **Updated** All frontend branding (title, headers)
- **Updated** Backend API title and startup messages
- **Updated** All documentation references
- **Changed** localStorage key from `camopt_state` to `platonicam_state`
- **Changed** Default database name from `camopt.db` to `platonicam.db`

#### Project Organization
- **Created** `docs/` folder - consolidated all documentation
- **Created** `tests/` folder with pytest structure
- **Moved** All markdown docs to `docs/` directory
- **Moved** Test scripts and utilities to `tests/backend/`
- **Added** `docs/README.md` - documentation index
- **Added** `tests/README.md` - test suite documentation
- **Added** `tests/conftest.py` - pytest fixtures
- **Added** `tests/backend/test_optimization.py` - unit tests for optimization service

#### UI Improvements
- **Added** Clean settings report display for optimization results
- **Added** Organized settings by category (Stream, Exposure, Low-Light, Image, Focus)
- **Added** Report header with confidence, provider, and processing time
- **Added** "Copy JSON" button in optimization detail modal
- **Improved** Detail modal with structured settings layout

---

## [0.3.1] - 2025-12-07

### Added

#### Sites/Projects Feature
- **Added** Site management system for organizing cameras into logical groups
- **Added** Create, switch, and delete sites via header controls
- **Added** JSON export - save any site to a `.json` file for backup/portability
- **Added** JSON import - load site files with duplicate detection (replace or create copy)
- **Added** Automatic data migration from legacy flat state to site-based structure
- **Added** Site selector dropdown in header with camera counts
- **Added** Per-site isolation of cameras, optimizations, and health schedules
- **Added** Support for same camera IP in multiple sites (different deployments)

**UI Changes:**
- Site controls in header: selector, [+] NEW, [S] SAVE, [L] LOAD, [X] DEL
- Create/Edit Site modal with name and description
- Empty state messages when no site selected
- Camera count badges per site in selector

**Data Model:**
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

#### Licensing
- **Added** Dual licensing model (AGPL v3 + Commercial)
- **Added** `LICENSE` file with GNU AGPL v3
- **Added** `COMMERCIAL.md` with commercial licensing info
- **Updated** README with license badges and dual-license section

### Changed
- **Refactored** State management to site-based architecture
- **Updated** All camera/optimization/health operations to use site context
- **Updated** localStorage schema (auto-migrates from legacy format)

### Fixed
- Camera imports now validate site exists before adding

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

- **v0.4.0** (2025-12-07) - Optimization Pipeline Infrastructure [Current]
- **v0.3.2** (2025-12-07) - Rebrand to PlatoniCam + Project Organization
- **v0.3.1** (2025-12-07) - Sites/Projects + Dual Licensing
- **v0.3.0** (2025-12-06) - Hanwha WAVE VMS Integration
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

**Maintained by:** PlatoniCam Development Team
**Last Updated:** 2025-12-07
**Current Version:** 0.4.0
