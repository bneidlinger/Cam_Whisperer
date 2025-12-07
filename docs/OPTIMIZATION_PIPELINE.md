# PlatoniCam Optimization Pipeline Interface Plan

## Overview

This document defines the optimization pipeline architecture for PlatoniCam, establishing clear interfaces between pipeline stages and ensuring extensibility for future enhancements.

---

## Current Pipeline Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           OPTIMIZATION PIPELINE                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────┐ │
│   │ DISCOVER │───▶│CAPABILITY│───▶│ OPTIMIZE │───▶│  APPLY   │───▶│VERIFY│ │
│   └──────────┘    └──────────┘    └──────────┘    └──────────┘    └──────┘ │
│        │               │               │               │              │     │
│        ▼               ▼               ▼               ▼              ▼     │
│   Camera List    Capabilities    Recommended     Apply Job      Verified   │
│   + Metadata     + Constraints    Settings       + Status        Status    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Stage 1: Discovery

**Purpose:** Find cameras on the network or from VMS systems.

### Interface

```python
class DiscoveryResult:
    cameras: List[DiscoveredCamera]
    source: str  # "onvif", "wave", "manual", "csv"
    timestamp: datetime
    errors: List[str]

class DiscoveredCamera:
    id: str                    # Unique identifier
    ip: str                    # IP address
    port: int                  # Service port
    vendor: Optional[str]      # Manufacturer
    model: Optional[str]       # Model name
    firmware: Optional[str]    # Firmware version
    name: Optional[str]        # Camera name/label
    location: Optional[str]    # Physical location
    protocol: str              # "onvif", "wave", "rtsp"
    vms_id: Optional[str]      # VMS-assigned ID
    vms_system: Optional[str]  # "hanwha-wave", "genetec", etc.
```

### Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `GET /api/discover` | GET | ONVIF WS-Discovery scan |
| `GET /api/wave/discover` | GET | WAVE VMS camera list |
| `POST /api/cameras` | POST | Manual camera registration |
| `POST /api/cameras/import` | POST | CSV batch import |

### Current Status
- [x] ONVIF WS-Discovery
- [x] WAVE VMS discovery
- [x] Manual registration
- [x] CSV import
- [ ] Genetec integration
- [ ] Milestone integration

---

## Stage 2: Capabilities Query

**Purpose:** Determine what a camera can do (resolutions, codecs, features).

### Interface

```python
class CameraCapabilities:
    camera_id: str

    # Stream capabilities
    supported_resolutions: List[str]  # ["1920x1080", "2560x1440", "3840x2160"]
    supported_codecs: List[str]       # ["H.264", "H.265", "MJPEG"]
    max_fps: int                      # Maximum frame rate
    max_bitrate_mbps: float           # Maximum bitrate

    # Exposure capabilities
    wdr_levels: List[str]             # ["Off", "Low", "Medium", "High"]
    shutter_modes: List[str]          # ["Auto", "Manual", "Flicker-free"]
    gain_range: Tuple[int, int]       # (min, max) dB

    # Low-light capabilities
    ir_modes: List[str]               # ["Off", "Auto", "On", "Smart"]
    has_ir: bool
    dnr_levels: List[str]             # ["Off", "Low", "Medium", "High"]

    # Special features
    has_lpr_mode: bool                # License plate recognition
    has_wdr: bool                     # Wide dynamic range
    has_blc: bool                     # Backlight compensation
    has_hlc: bool                     # Highlight compensation
    has_defog: bool
    has_eis: bool                     # Electronic image stabilization

    # PTZ (if applicable)
    is_ptz: bool
    ptz_presets: Optional[List[str]]

    # Metadata
    queried_at: datetime
    source: str                       # "onvif", "wave", "manual"
```

### Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `GET /api/cameras/{id}/capabilities` | GET | Query via ONVIF |
| `GET /api/wave/cameras/{id}/capabilities` | GET | Query via WAVE |

### Current Status
- [x] ONVIF capabilities query
- [x] WAVE capabilities query
- [ ] Capability caching
- [ ] Capability validation

---

## Stage 3: Current Settings Query

**Purpose:** Get the camera's current configuration before optimization.

### Interface

```python
class CameraCurrentSettings:
    camera_id: str

    stream: StreamSettings
    exposure: ExposureSettings
    low_light: LowLightSettings
    image: ImageSettings

    queried_at: datetime
    source: str

class StreamSettings:
    resolution: str           # "1920x1080"
    codec: str                # "H.265"
    fps: int                  # 20
    bitrate_mbps: float       # 4.0
    bitrate_mode: str         # "VBR" or "CBR"
    gop_size: Optional[int]   # 60
    profile: Optional[str]    # "Main", "High"

class ExposureSettings:
    mode: str                 # "Auto", "Manual"
    shutter: Optional[str]    # "1/250"
    iris: Optional[str]       # "Auto", "F1.6"
    gain_limit: Optional[int] # 12 dB
    wdr: str                  # "Medium"
    blc: Optional[str]        # "Off"
    hlc: Optional[str]        # "Off"

class LowLightSettings:
    ir_mode: str              # "Auto"
    ir_intensity: Optional[int]  # 0-100
    day_night: str            # "Auto", "Day", "Night"
    dnr: str                  # "Medium"
    slow_shutter: str         # "Off"

class ImageSettings:
    sharpness: int            # 0-100
    contrast: int             # 0-100
    saturation: int           # 0-100
    brightness: int           # 0-100
    white_balance: str        # "Auto", "Indoor", "Outdoor"
```

### Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `GET /api/cameras/{id}/current-settings` | GET | Query via ONVIF |
| `GET /api/wave/cameras/{id}/current-settings` | GET | Query via WAVE |

### Current Status
- [x] ONVIF settings query
- [x] WAVE settings query
- [ ] Settings diffing
- [ ] Settings history

---

## Stage 4: Optimization

**Purpose:** Generate optimal settings based on context and AI analysis.

### Interface

```python
class OptimizationRequest:
    camera: CameraContext
    capabilities: CameraCapabilities
    current_settings: CameraCurrentSettings
    context: OptimizationContext

class CameraContext:
    id: str
    ip: str
    location: str
    scene_type: SceneType
    purpose: CameraPurpose
    vendor: Optional[str]
    model: Optional[str]

class SceneType(Enum):
    ENTRANCE = "entrance"       # High contrast, WDR needed
    PARKING = "parking"         # LPR, fast shutter
    HALLWAY = "hallway"         # Consistent lighting
    PERIMETER = "perimeter"     # Long range, IR important
    CASHWRAP = "cashwrap"       # Facial, evidence-grade
    LOBBY = "lobby"             # Mixed lighting
    WAREHOUSE = "warehouse"     # Large area, motion
    STAIRWELL = "stairwell"     # Variable lighting
    LOADING_DOCK = "loading"    # Vehicles + faces

class CameraPurpose(Enum):
    FACIAL = "facial"           # Face recognition priority
    PLATES = "plates"           # License plate capture
    OVERVIEW = "overview"       # General monitoring
    EVIDENCE = "evidence"       # Evidentiary quality
    COUNTING = "counting"       # People/vehicle counting

class OptimizationContext:
    bandwidth_limit_mbps: Optional[float]
    target_retention_days: Optional[int]
    sample_frame: Optional[str]  # Base64 image
    notes: Optional[str]
    lighting_condition: Optional[str]  # "bright", "mixed", "low"
    motion_level: Optional[str]        # "low", "medium", "high"

class OptimizationResult:
    recommended_settings: RecommendedSettings
    confidence: float           # 0.0 - 1.0
    explanation: str            # AI-generated reasoning
    warnings: List[str]         # Constraint violations
    ai_provider: str            # "claude-sonnet-4-5" or "heuristic"
    processing_time: float      # Seconds
    generated_at: datetime

class RecommendedSettings:
    stream: StreamSettings
    exposure: ExposureSettings
    low_light: LowLightSettings
    image: ImageSettings
```

### Optimization Strategies

```
┌─────────────────────────────────────────────────────────────────────┐
│                    OPTIMIZATION STRATEGY MATRIX                      │
├─────────────────┬─────────────┬─────────────┬─────────────┬─────────┤
│ Scene/Purpose   │   Facial    │   Plates    │  Overview   │Evidence │
├─────────────────┼─────────────┼─────────────┼─────────────┼─────────┤
│ Entrance        │ WDR High    │ WDR High    │ WDR High    │ WDR Max │
│                 │ 1/250 min   │ 1/500 min   │ Auto        │ 1/250   │
│                 │ 20+ FPS     │ 25+ FPS     │ 15 FPS      │ 20 FPS  │
├─────────────────┼─────────────┼─────────────┼─────────────┼─────────┤
│ Parking         │ IR Auto     │ IR Auto     │ IR Auto     │ IR Auto │
│                 │ 1/250       │ 1/500+      │ Auto        │ 1/250   │
│                 │ 20 FPS      │ 25+ FPS     │ 10-15 FPS   │ 20 FPS  │
├─────────────────┼─────────────┼─────────────┼─────────────┼─────────┤
│ Hallway         │ Standard    │ N/A         │ Standard    │ High    │
│                 │ 1/250       │             │ Auto        │ 1/250   │
│                 │ 15-20 FPS   │             │ 10-15 FPS   │ 15 FPS  │
├─────────────────┼─────────────┼─────────────┼─────────────┼─────────┤
│ Perimeter       │ IR High     │ IR High     │ IR High     │ IR Max  │
│                 │ DNR Medium  │ DNR Low     │ DNR Medium  │ DNR Low │
│                 │ 15 FPS      │ 20+ FPS     │ 10 FPS      │ 15 FPS  │
└─────────────────┴─────────────┴─────────────┴─────────────┴─────────┘
```

### AI Provider Interface

```python
class OptimizationProvider(ABC):
    """Abstract base class for optimization providers"""

    @abstractmethod
    async def optimize(
        self,
        camera: CameraContext,
        capabilities: CameraCapabilities,
        current_settings: CameraCurrentSettings,
        context: OptimizationContext
    ) -> OptimizationResult:
        pass

    @abstractmethod
    def get_provider_name(self) -> str:
        pass

class ClaudeOptimizationProvider(OptimizationProvider):
    """Claude Vision AI provider"""
    pass

class HeuristicOptimizationProvider(OptimizationProvider):
    """Rule-based fallback provider"""
    pass

# Future providers:
# class OpenAIOptimizationProvider(OptimizationProvider)
# class LocalLLMOptimizationProvider(OptimizationProvider)
```

### Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `POST /api/optimize` | POST | Generate optimal settings |

### Current Status
- [x] Claude Vision integration
- [x] Heuristic fallback
- [x] Confidence scoring
- [x] Warning generation
- [ ] Provider abstraction layer
- [ ] Multiple provider support
- [ ] A/B testing framework

---

## Stage 5: Settings Application

**Purpose:** Apply optimized settings to cameras via ONVIF or VMS.

### Interface

```python
class ApplyRequest:
    camera_id: str
    settings: RecommendedSettings
    apply_via: ApplyMethod
    verify_after: bool = True
    credentials: Optional[CameraCredentials]

class ApplyMethod(Enum):
    ONVIF = "onvif"
    WAVE = "wave"
    GENETEC = "genetec"
    MILESTONE = "milestone"
    MANUAL = "manual"  # Generate config file only

class ApplyResult:
    job_id: str
    status: ApplyStatus
    camera_id: str
    applied_settings: Dict[str, Any]
    verification: Optional[VerificationResult]
    errors: List[str]
    started_at: datetime
    completed_at: Optional[datetime]

class ApplyStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    VERIFYING = "verifying"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"  # Some settings applied

class VerificationResult:
    verified: bool
    mismatches: List[SettingMismatch]
    verified_at: datetime

class SettingMismatch:
    category: str      # "stream", "exposure", etc.
    setting: str       # "fps", "wdr", etc.
    expected: Any
    actual: Any
```

### Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `POST /api/apply` | POST | Start apply job |
| `GET /api/apply/status/{job_id}` | GET | Check job status |
| `DELETE /api/apply/{job_id}` | DELETE | Cancel job |

### Current Status
- [x] ONVIF apply (stream settings)
- [x] WAVE apply
- [x] Job tracking (in-memory)
- [ ] Job persistence (database)
- [ ] Apply rollback
- [ ] Batch apply

---

## Stage 6: Verification & Monitoring

**Purpose:** Verify settings were applied and monitor for drift.

### Interface

```python
class MonitoringConfig:
    camera_id: str
    check_interval_minutes: int
    alert_on_drift: bool
    auto_reapply: bool

class DriftDetectionResult:
    camera_id: str
    has_drift: bool
    drifted_settings: List[SettingMismatch]
    detected_at: datetime
    last_known_good: datetime

class HealthStatus:
    camera_id: str
    online: bool
    last_seen: datetime
    stream_active: bool
    settings_match: bool
    errors: List[str]
```

### Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `GET /api/cameras/{id}/health` | GET | Camera health check |
| `POST /api/monitor/start` | POST | Start monitoring |
| `POST /api/monitor/stop` | POST | Stop monitoring |
| `GET /api/monitor/status` | GET | Monitoring status |

### Current Status
- [ ] Health monitoring
- [ ] Drift detection
- [ ] Auto re-optimization
- [ ] Alerting

---

## Pipeline Context

**Purpose:** Carry metadata through all pipeline stages.

```python
@dataclass
class PipelineContext:
    """Context that flows through all pipeline stages"""

    # Request identification
    request_id: str = field(default_factory=lambda: str(uuid4()))
    site_id: Optional[str] = None
    user_id: Optional[str] = None

    # Timing
    started_at: datetime = field(default_factory=datetime.utcnow)
    stage_times: Dict[str, float] = field(default_factory=dict)

    # Data accumulated through stages
    discovered_camera: Optional[DiscoveredCamera] = None
    capabilities: Optional[CameraCapabilities] = None
    current_settings: Optional[CameraCurrentSettings] = None
    optimization_result: Optional[OptimizationResult] = None
    apply_result: Optional[ApplyResult] = None

    # Error tracking
    errors: List[PipelineError] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    # Feature flags
    skip_capability_query: bool = False
    skip_current_settings: bool = False
    dry_run: bool = False  # Don't actually apply

@dataclass
class PipelineError:
    stage: str
    error_type: str
    message: str
    timestamp: datetime
    recoverable: bool
```

---

## Error Handling

### Error Hierarchy

```python
class PipelineError(Exception):
    """Base exception for pipeline errors"""
    pass

class DiscoveryError(PipelineError):
    """Camera discovery failed"""
    pass

class CapabilityQueryError(PipelineError):
    """Failed to query camera capabilities"""
    pass

class OptimizationError(PipelineError):
    """Optimization generation failed"""
    pass

class ApplyError(PipelineError):
    """Failed to apply settings"""
    pass

class VerificationError(PipelineError):
    """Settings verification failed"""
    pass

class ProviderError(PipelineError):
    """AI provider error (Claude API, etc.)"""
    pass

class TimeoutError(PipelineError):
    """Operation timed out"""
    pass

class AuthenticationError(PipelineError):
    """Camera/VMS authentication failed"""
    pass
```

### Recovery Strategies

| Error Type | Recovery Strategy |
|------------|-------------------|
| `DiscoveryError` | Retry with different protocol, manual entry |
| `CapabilityQueryError` | Use default/generic capabilities |
| `OptimizationError` | Fall back to heuristic engine |
| `ApplyError` | Retry, partial apply, rollback |
| `VerificationError` | Re-query, alert user |
| `ProviderError` | Switch provider, retry with backoff |
| `TimeoutError` | Retry with longer timeout |
| `AuthenticationError` | Prompt for credentials |

---

## Future Enhancements

### Phase 1: Foundation (v0.4)
- [ ] Database persistence for all pipeline data
- [ ] Pipeline context implementation
- [ ] Error handling improvements
- [ ] Request/response logging

### Phase 2: Reliability (v0.5)
- [ ] Provider abstraction layer
- [ ] Retry logic with exponential backoff
- [ ] Job queue with persistence
- [ ] Health monitoring

### Phase 3: Scale (v0.6)
- [ ] Batch optimization
- [ ] Parallel apply
- [ ] Caching layer
- [ ] Rate limiting

### Phase 4: Intelligence (v0.7+)
- [ ] A/B testing framework
- [ ] Confidence calibration
- [ ] Learning from verification results
- [ ] Drift prediction

---

## Configuration

```env
# Pipeline Settings
PIPELINE_TIMEOUT_SECONDS=60
PIPELINE_MAX_RETRIES=3
PIPELINE_RETRY_DELAY_SECONDS=5

# Discovery
DISCOVERY_TIMEOUT_SECONDS=30
ONVIF_DISCOVERY_DURATION_SECONDS=5

# Optimization
OPTIMIZATION_TIMEOUT_SECONDS=30
OPTIMIZATION_PROVIDER=claude  # claude, heuristic, openai
FALLBACK_TO_HEURISTIC=true

# Apply
APPLY_TIMEOUT_SECONDS=30
VERIFY_AFTER_APPLY=true
APPLY_RETRY_COUNT=2

# Monitoring
MONITORING_CHECK_INTERVAL_MINUTES=60
DRIFT_DETECTION_ENABLED=false
AUTO_REAPPLY_ON_DRIFT=false
```

---

**Document Version:** 1.0
**Last Updated:** 2025-12-07
**Status:** Planning
