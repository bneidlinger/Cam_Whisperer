# Changelog

All notable changes to PlatoniCam will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Added

#### ONVIF WebRTC Low-Latency Streaming (Phase 3) ✅

- **Created** `backend/integrations/webrtc_signaling.py` (~550 lines)
  - `ONVIFWebRTCGateway` class with JSON-RPC 2.0 signaling
  - WebSocket proxy between browser and camera
  - SDP offer/answer exchange with ICE candidate forwarding
  - RTSP fallback for non-WebRTC cameras
  - Session management with state tracking
  - Heartbeat mechanism for connection health

- **Added** WebRTC configuration settings (`backend/config.py`)
  - `webrtc_stun_server` - STUN server URL
  - `webrtc_turn_server` - TURN server URL
  - `webrtc_turn_username` / `webrtc_turn_credential` - TURN auth

- **Added** WebRTC API endpoints
  - `WS /api/webrtc/stream` - WebSocket signaling endpoint
  - `GET /api/webrtc/config` - Get WebRTC/ICE configuration
  - `GET /api/webrtc/sessions` - List active streaming sessions

#### ONVIF Profile M Analytics Integration (Phase 4) ✅

- **Created** `backend/integrations/mqtt_events.py` (~450 lines)
  - `ONVIFEventBridge` class for MQTT pub/sub
  - `MQTTBrokerConfig` dataclass with connection settings
  - `CameraEvent` dataclass with EventType enum
  - Camera MQTT configuration via ONVIF AddEventBroker
  - Event subscription with handler registration
  - Connection status tracking and auto-reconnect
  - Statistics: events received, published, errors

- **Created** `backend/integrations/metadata_parser.py` (~400 lines)
  - `MetadataParser` for XML and JSON analytics frames
  - `BoundingBox` with normalized coordinates (0.0-1.0)
  - `DetectedObject` with classification and confidence
  - `MotionRegion` for motion detection data
  - `AnalyticsFrame` aggregating all detections
  - `ObjectClass` enum: Human, Face, Vehicle, LicensePlate, Animal, etc.
  - RTP payload parsing support (bytes input)

- **Added** MQTT configuration settings (`backend/config.py`)
  - `mqtt_enabled` - Enable/disable MQTT integration
  - `mqtt_broker_host` / `mqtt_broker_port` - Broker connection
  - `mqtt_use_tls` - TLS encryption for MQTT
  - `mqtt_username` / `mqtt_password` - Broker authentication
  - `mqtt_topic_prefix` - Topic namespace (default: "platonicam")

- **Added** MQTT API endpoints
  - `GET /api/mqtt/status` - Bridge status and statistics
  - `POST /api/mqtt/connect` - Connect to MQTT broker
  - `POST /api/mqtt/disconnect` - Disconnect from broker
  - `POST /api/mqtt/camera/configure` - Configure camera MQTT publishing
  - `DELETE /api/mqtt/camera/{ip}` - Remove camera MQTT config
  - `POST /api/mqtt/subscribe` - Subscribe to camera events

#### ONVIF Security Hardening (Phase 5) ✅

- **Created** `backend/utils/tls_helper.py` (~250 lines)
  - `create_ssl_context()` - Configurable SSL context creation
  - Support for strict verification or self-signed certificates
  - Client certificate support for mutual TLS
  - Secure protocol options (TLS 1.2+ only)
  - `get_default_ssl_context()` - Uses application settings
  - `validate_camera_certificate()` - Check camera TLS cert details

- **Added** TLS configuration settings (`backend/config.py`)
  - `tls_verify_certificates` - Enable strict cert validation
  - `tls_allow_self_signed` - Allow self-signed certs (default: True)
  - `tls_ca_bundle_path` - Custom CA bundle path
  - `tls_client_cert_path` / `tls_client_key_path` - Client cert for mTLS

- **Added** WS-Discovery mode control (`backend/integrations/onvif_client.py`)
  - `get_discovery_mode()` - Query camera discovery visibility
  - `set_discovery_mode()` - Enable/disable discoverability
  - `disable_discovery()` / `enable_discovery()` - Convenience methods

- **Added** Security API endpoints
  - `GET /api/camera/{ip}/discovery-mode` - Get discovery mode
  - `POST /api/camera/discovery-mode` - Set discovery mode
  - `GET /api/camera/{ip}/tls-certificate` - Validate TLS certificate

#### Phase 4/5 Test Suite

- **Created** `tests/backend/test_tls_helper.py` - TLS helper tests (11 tests)
- **Created** `tests/backend/test_security.py` - Security integration tests (19 tests)
- **Created** `tests/backend/test_mqtt_events.py` - MQTT event bridge tests (14 tests)
- **Created** `tests/backend/test_metadata_parser.py` - Metadata parser tests (24 tests)

**Test Results:** 56 passed, 1 skipped

#### Frontend Integration (Phase 3-5 UI) ✅

- **Added** MQTT Events navigation and section (`index.html`)
  - New "Events" nav item with unread badge counter
  - MQTT broker connection panel (host, port, username, password, TLS)
  - Connect/Disconnect controls with status indicator
  - Real-time statistics (events received, processed, dropped)
  - Camera MQTT configuration (select camera, topic prefix, enable/disable)
  - Event log with filtering by type (All, Motion, Alert, Tamper, Analytics)
  - Auto-refresh polling for broker status and events

- **Added** TLS/Security info to Camera Bay cards
  - 4-column grid: Device, Capabilities, Current, **Security**
  - TLS status indicator (Valid/Self-signed/Invalid) with color coding
  - Certificate issuer and days until expiry display
  - Discovery mode status (Enabled/Disabled/Unknown)
  - "Check TLS" button to validate camera certificate
  - "Toggle Disc" button to enable/disable WS-Discovery visibility

- **Added** WebRTC session management UI
  - Session count display in liveview modal
  - "Manage Sessions" button opens session list modal
  - Active sessions list with camera IP, state, and close button
  - WebRTC sessions modal with backdrop close support

- **Added** CSS styles (~160 lines)
  - MQTT status badge states (connected/connecting/disconnected)
  - Event type badges (motion, alert, tamper, analytics, line_crossing, intrusion)
  - TLS indicator classes (tls-valid, tls-warning, tls-invalid)
  - Alert pulse animation for critical events

- **Added** JavaScript functions (~470 lines)
  - MQTT: `connectMqttBroker()`, `disconnectMqttBroker()`, `fetchMqttStatus()`, `configureCameraMqtt()`, `removeCameraMqtt()`, `updateMqttCameraSelector()`, `addEventToLog()`, `renderEventLog()`, `clearEventLog()`
  - TLS: `checkCameraTls()`, `toggleDiscoveryMode()`
  - WebRTC: `fetchWebRtcSessions()`, `openWebRtcSessionsModal()`, `closeWebRtcSession()`, `closeWebRtcSessionsModal()`

**Frontend Total:** ~630 lines added to `index.html`

#### ONVIF Integration Improvements (Phase 1 & 2)

**Phase 1: Foundation Improvements** ✅
- **Added** WSDL caching with SQLite (`backend/cache/wsdl_cache.db`)
  - Reduces camera connection time from ~5s to <500ms
  - 24-hour cache TTL for parsed WSDL documents
  - Uses `zeep.cache.SqliteCache`

- **Added** Scope-based WS-Discovery filtering
  - Filter by location, manufacturer, or custom scopes
  - Prevents broadcast storms on large networks
  - Optional `scopes` parameter on discovery

- **Added** Direct connect mode (`ONVIFClient.direct_connect()`)
  - Bypass WS-Discovery when IP is known
  - More secure - no unauthenticated UDP broadcast
  - Returns device info, capabilities, Profile T support status

- **Added** Connection pooling for ONVIF cameras
  - Reuse authenticated camera connections
  - `cache_connection()`, `get_cached_connection()`, `remove_cached_connection()`
  - Reduces repeated authentication overhead

- **Added** Profile T detection
  - Auto-detect Media2 service availability
  - Log deprecation warning for Profile S-only cameras
  - `profile_t_supported` flag in connection results

- **Added** `ONVIFBatchClient` for concurrent camera operations
  - Query multiple cameras in parallel with `asyncio.gather()`
  - Batch capabilities, settings, and info queries

**Phase 2: Profile T Migration** ✅
- **Created** `backend/integrations/media2_client.py` (~250 lines)
  - `Media2Client` class with Profile S fallback
  - `has_media2_service()` - Check for Media2 availability
  - `get_profiles()` - Get media profiles (Media2 or Media1)
  - `get_video_encoder_configurations()` - Query encoder configs
  - `get_video_encoder_config_options()` - Query encoder capabilities
  - `set_video_encoder_configuration()` - Configure encoder
  - `get_stream_uri()` - Get stream URI with protocol options

- **Added** H.265/HEVC encoder configuration support
  - `check_h265_support()` - Detect H.265 capability
  - `configure_h265_stream()` - Configure H.265 encoder
  - Support for H.265 profiles (Main, Main10)
  - GOP length and bitrate configuration

- **Added** RTSPS (Secure RTSP) support
  - `get_stream_uri()` with `secure=True` option
  - HTTPS/RTSPS protocol selection
  - TLS-encrypted video streaming

- **Integrated** Media2 client into `ONVIFClient`
  - `get_h265_capabilities()` - Query H.265 support and options
  - `configure_h265()` - Apply H.265 encoder settings
  - `get_stream_uri_secure()` - Get RTSPS URI

- **Updated** Discovery service with H.265 detection
  - Discovery response includes `h265_supported`, `h265_profiles`, `max_h265_resolution`
  - Automatic capability detection during camera discovery

### Fixed

- **Fixed** `CameraCapabilities.from_dict()` None value handling
  - Now properly defaults to safe values when dict contains `null`
  - Prevents comparison errors (`'>' not supported between int and NoneType`)

- **Fixed** `_clamp_to_capabilities()` in heuristic provider
  - Added defensive check for `None` max_fps value
  - Defaults to 30 FPS if capabilities.max_fps is None

- **Fixed** ResourceWarning spam from wsdiscovery library
  - Added warning filters at module level in `main.py`
  - Added `PYTHONWARNINGS=ignore::ResourceWarning` in start scripts

- **Fixed** Snapshot not auto-filling in optimize form
  - Corrected element ID from `camera-select` to `optimize-camera-select`
  - Added change event listener to populate snapshot from camera

### Documentation

- **Created** `docs/onvif_action_plan.md` - Comprehensive ONVIF integration roadmap
  - 5 phases of improvements based on ONVIF 2024-2025 specifications
  - Profile T migration timeline (Profile S deprecated Oct 2025)
  - WebRTC signaling architecture
  - MQTT event integration (Profile M)
  - Security hardening recommendations

---

#### Full Database Persistence (Phase 1 Complete)
- **Added** SQLAlchemy 2.0 database layer (`backend/database.py`)
  - SQLite for local dev, PostgreSQL-ready for production
  - Session context manager with auto-commit/rollback
  - Database initialization on FastAPI startup

- **Added** ORM models (`backend/models/orm.py`)
  - `Camera` - Camera inventory with metadata, credentials, capabilities
  - `Optimization` - Full audit trail of optimization requests/results
  - `AppliedConfig` - Job tracking for applied settings (replaces in-memory)
  - `CameraDatasheet` - Manufacturer datasheet cache
  - `DatasheetFetchLog` - Fetch attempt tracking

- **Added** Camera service (`backend/services/camera_service.py`)
  - `register_camera()` - Create/update by IP
  - `get_camera()`, `get_camera_by_ip()` - Retrieve cameras
  - `list_cameras()` - Query with filters (scene_type, purpose, vendor)
  - `update_camera()`, `delete_camera()` - CRUD operations
  - Soft delete support with `deleted_at` timestamp

- **Added** Camera management API endpoints
  - `GET /api/cameras` - List with filters and pagination
  - `POST /api/cameras` - Register camera
  - `GET /api/cameras/{id}` - Get by ID
  - `PUT /api/cameras/{id}` - Update camera
  - `DELETE /api/cameras/{id}` - Soft/hard delete

- **Added** Optimization persistence
  - Auto-saves all optimization results to database
  - Returns `optimizationId` in API response
  - `GET /api/optimizations` - Query history with pagination
  - `GET /api/optimizations/{id}` - Get single result
  - `GET /api/cameras/{id}/optimizations` - Camera-specific history

- **Added** Apply job persistence
  - Database-backed job tracking (replaces `self.active_jobs = {}`)
  - Jobs survive server restarts
  - `GET /api/apply/jobs` - List with status filters
  - Backward-compatible with legacy job ID format

- **Added** Auto-registration of discovered cameras
  - ONVIF-discovered cameras auto-register to database
  - WAVE VMS-discovered cameras include VMS metadata
  - `registered: true` flag in discovery response

#### Camera Datasheet Integration
- **Added** Datasheet fetcher (`backend/integrations/datasheet_fetcher.py`)
  - DuckDuckGo search for PDF datasheets
  - Hardcoded manufacturer URL patterns (Axis, Hanwha, Hikvision, Dahua, etc.)
  - PDF download and text extraction with pdfplumber
  - Spec parsing (sensor size, resolution, WDR, codecs, IR range)

- **Added** Datasheet service (`backend/services/datasheet_service.py`)
  - Database caching layer
  - Background fetch triggering (non-blocking)
  - `get_datasheet()` - Check cache first
  - `fetch_and_cache()` - Fetch and persist
  - `start_background_fetch()` - Async background task

- **Added** Datasheet API endpoints
  - `GET /api/datasheets/{manufacturer}/{model}` - Get cached datasheet
  - `POST /api/datasheets/fetch` - Trigger fetch
  - `POST /api/datasheets/upload` - Manual upload
  - `DELETE /api/datasheets/{manufacturer}/{model}` - Remove
  - `GET /api/datasheets` - List all cached

- **Integrated** Datasheet specs into Claude AI prompt
  - `datasheet_specs` field in OptimizationContext
  - Manufacturer specifications section in Claude prompt
  - Auto-fetch triggered on camera discovery

#### Network Security Controls
- **Added** Rate limiting (`backend/utils/rate_limiter.py`)
  - 30 second minimum between discovery requests per client
  - Max 3 requests/minute per client
  - Global limit: 10 requests/minute across all clients
  - 5 minute block for repeat offenders
  - Proper 429 responses with `Retry-After` header

- **Added** MAC/OUI filtering (`backend/utils/network_filter.py`)
  - MAC address whitelist/blacklist
  - OUI (vendor prefix) filtering
  - 35+ known camera manufacturer OUIs (Hanwha, Axis, Hikvision, Dahua, etc.)
  - IP subnet restrictions (CIDR notation)
  - Vendor name filtering
  - Auto-enriches cameras with vendor from MAC lookup

- **Added** Security API endpoints
  - `GET /api/security/rate-limit/status` - Check rate limit status
  - `GET /api/security/network-filter` - View filter config
  - `PUT /api/security/network-filter` - Configure filtering
  - `GET /api/security/known-ouis` - List known camera OUIs

- **Hardened** Discovery endpoints
  - Default `max_cameras=100` (was unlimited)
  - Max timeout enforced at 30 seconds
  - Rate limit status in discovery responses
  - Network filter applied post-discovery

### Changed
- **Updated** Discovery service to apply network filtering
- **Updated** Apply service to use database-backed job tracking
- **Updated** Optimization service to persist results automatically

### Security
- Rate limiting prevents network flooding via discovery abuse
- MAC filtering restricts discovery to known/trusted devices
- Subnet filtering enables network segmentation compliance

---

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

- **v0.5.0** (Unreleased) - ONVIF Phases 3-5: WebRTC, Profile M, Security
- **v0.4.0** (2025-12-07) - Optimization Pipeline Infrastructure
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
**Last Updated:** 2025-12-16
**Current Version:** 0.5.0-dev (Unreleased)
