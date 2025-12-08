# backend/models/pipeline.py
"""
Pipeline Data Models for PlatoniCam

Defines all data structures used throughout the optimization pipeline.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4


# =============================================================================
# ENUMS
# =============================================================================

class SceneType(str, Enum):
    """Camera scene/environment type"""
    ENTRANCE = "entrance"           # High contrast, doors/windows, WDR needed
    PARKING = "parking"             # Vehicles, LPR potential, variable lighting
    HALLWAY = "hallway"             # Consistent indoor lighting, linear space
    PERIMETER = "perimeter"         # Outdoor, long range, IR important
    CASHWRAP = "cashwrap"           # Point of sale, facial + transaction
    CASH_REGISTER = "cash_register" # Same as cashwrap, alias
    LOBBY = "lobby"                 # Mixed lighting, high traffic
    WAREHOUSE = "warehouse"         # Large area, high ceilings, motion
    STAIRWELL = "stairwell"         # Variable lighting, vertical space
    LOADING_DOCK = "loading"        # Vehicles + people, bright/dark transitions
    OFFICE = "office"               # Indoor, consistent lighting
    RETAIL = "retail"               # Aisles, shelves, customer tracking
    ELEVATOR = "elevator"           # Small space, close range
    ATM = "atm"                     # Facial required, transaction
    EXTERIOR_NIGHT = "exterior_night"  # Outdoor nighttime, IR critical
    SERVER_ROOM = "server_room"     # Data center, controlled environment
    GENERIC = "generic"             # Default/unknown


class CameraPurpose(str, Enum):
    """Primary operational purpose of the camera"""
    FACIAL = "facial"           # Face recognition/identification priority
    PLATES = "plates"           # License plate capture (LPR/ANPR)
    OVERVIEW = "overview"       # General monitoring, situational awareness
    EVIDENCE = "evidence"       # Evidentiary quality, court-admissible
    COUNTING = "counting"       # People/vehicle counting analytics
    BEHAVIORAL = "behavioral"   # Behavior detection, loitering, etc.
    SAFETY = "safety"           # Safety monitoring, PPE detection
    INTRUSION = "intrusion"     # Intrusion/perimeter detection
    GENERAL = "general"         # General purpose, balanced settings


class ApplyMethod(str, Enum):
    """Method used to apply settings to camera"""
    ONVIF = "onvif"             # Direct ONVIF protocol
    WAVE = "wave"               # Hanwha WAVE VMS API
    GENETEC = "genetec"         # Genetec Security Center
    MILESTONE = "milestone"     # Milestone XProtect
    MANUAL = "manual"           # Generate config file only (no auto-apply)


class ApplyStatus(str, Enum):
    """Status of a settings apply job"""
    PENDING = "pending"         # Job queued, not started
    IN_PROGRESS = "in_progress" # Currently applying settings
    VERIFYING = "verifying"     # Settings applied, verifying
    COMPLETED = "completed"     # Successfully applied and verified
    FAILED = "failed"           # Apply failed
    PARTIAL = "partial"         # Some settings applied, some failed
    CANCELLED = "cancelled"     # Job cancelled by user
    TIMEOUT = "timeout"         # Operation timed out


# =============================================================================
# CAMERA MODELS
# =============================================================================

@dataclass
class DiscoveredCamera:
    """Camera discovered via network scan or VMS"""
    id: str
    ip: str
    port: int = 80
    vendor: Optional[str] = None
    model: Optional[str] = None
    firmware: Optional[str] = None
    name: Optional[str] = None
    location: Optional[str] = None
    protocol: str = "onvif"
    vms_id: Optional[str] = None
    vms_system: Optional[str] = None
    mac_address: Optional[str] = None
    serial_number: Optional[str] = None
    discovered_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "ip": self.ip,
            "port": self.port,
            "vendor": self.vendor,
            "model": self.model,
            "firmware": self.firmware,
            "name": self.name,
            "location": self.location,
            "protocol": self.protocol,
            "vmsId": self.vms_id,
            "vmsSystem": self.vms_system,
            "macAddress": self.mac_address,
            "serialNumber": self.serial_number,
            "discoveredAt": self.discovered_at.isoformat() + "Z",
        }


@dataclass
class CameraCapabilities:
    """Hardware capabilities of a camera"""
    camera_id: str

    # Stream capabilities
    supported_resolutions: List[str] = field(default_factory=lambda: ["1920x1080"])
    supported_codecs: List[str] = field(default_factory=lambda: ["H.264", "H.265"])
    max_fps: int = 30
    min_fps: int = 1
    max_bitrate_mbps: float = 16.0
    min_bitrate_mbps: float = 0.5

    # Exposure capabilities
    wdr_levels: List[str] = field(default_factory=lambda: ["Off", "Low", "Medium", "High"])
    shutter_modes: List[str] = field(default_factory=lambda: ["Auto", "Manual"])
    shutter_range: Optional[Tuple[str, str]] = None  # ("1/30", "1/10000")
    gain_range: Optional[Tuple[int, int]] = None  # (0, 48) dB
    iris_modes: List[str] = field(default_factory=lambda: ["Auto"])

    # Low-light capabilities
    ir_modes: List[str] = field(default_factory=lambda: ["Off", "Auto", "On"])
    has_ir: bool = True
    dnr_levels: List[str] = field(default_factory=lambda: ["Off", "Low", "Medium", "High"])
    has_slow_shutter: bool = True

    # Special features
    has_wdr: bool = True
    has_blc: bool = True
    has_hlc: bool = False
    has_defog: bool = False
    has_eis: bool = False
    has_lpr_mode: bool = False
    has_privacy_mask: bool = True
    has_motion_detection: bool = True

    # PTZ
    is_ptz: bool = False
    ptz_presets: Optional[List[str]] = None
    has_auto_tracking: bool = False

    # Audio
    has_audio_in: bool = False
    has_audio_out: bool = False

    # Metadata
    queried_at: datetime = field(default_factory=datetime.utcnow)
    source: str = "onvif"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cameraId": self.camera_id,
            "supportedResolutions": self.supported_resolutions,
            "supportedCodecs": self.supported_codecs,
            "maxFps": self.max_fps,
            "minFps": self.min_fps,
            "maxBitrateMbps": self.max_bitrate_mbps,
            "wdrLevels": self.wdr_levels,
            "irModes": self.ir_modes,
            "hasWdr": self.has_wdr,
            "hasIr": self.has_ir,
            "hasLprMode": self.has_lpr_mode,
            "isPtz": self.is_ptz,
            "queriedAt": self.queried_at.isoformat() + "Z",
            "source": self.source,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CameraCapabilities":
        """Create CameraCapabilities from dict"""
        return cls(
            camera_id=data.get("cameraId", data.get("camera_id", "unknown")),
            supported_resolutions=data.get("supportedResolutions", data.get("supported_resolutions", ["1920x1080"])),
            supported_codecs=data.get("supportedCodecs", data.get("supported_codecs", ["H.264", "H.265"])),
            max_fps=data.get("maxFps", data.get("max_fps", 30)),
            min_fps=data.get("minFps", data.get("min_fps", 1)),
            max_bitrate_mbps=data.get("maxBitrateMbps", data.get("max_bitrate_mbps", 16.0)),
            min_bitrate_mbps=data.get("minBitrateMbps", data.get("min_bitrate_mbps", 0.5)),
            wdr_levels=data.get("wdrLevels", data.get("wdr_levels", ["Off", "Low", "Medium", "High"])),
            ir_modes=data.get("irModes", data.get("ir_modes", ["Off", "Auto", "On"])),
            has_wdr=data.get("hasWdr", data.get("has_wdr", True)),
            has_ir=data.get("hasIr", data.get("has_ir", True)),
            has_lpr_mode=data.get("hasLprMode", data.get("has_lpr_mode", False)),
            is_ptz=data.get("isPtz", data.get("is_ptz", False)),
            source=data.get("source", "api"),
        )


# =============================================================================
# SETTINGS MODELS
# =============================================================================

@dataclass
class StreamSettings:
    """Video stream configuration"""
    resolution: str = "1920x1080"
    codec: str = "H.265"
    fps: int = 20
    bitrate_mbps: float = 4.0
    bitrate_mode: str = "VBR"  # "VBR" or "CBR"
    gop_size: Optional[int] = None  # Keyframe interval in frames
    profile: Optional[str] = None  # "Baseline", "Main", "High"
    quality: Optional[int] = None  # 1-100 for VBR

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "resolution": self.resolution,
            "codec": self.codec,
            "fps": self.fps,
            "bitrateMbps": self.bitrate_mbps,
            "bitrateMode": self.bitrate_mode,
        }
        if self.gop_size:
            result["gopSize"] = self.gop_size
        if self.profile:
            result["profile"] = self.profile
        if self.quality:
            result["quality"] = self.quality
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StreamSettings":
        return cls(
            resolution=data.get("resolution", "1920x1080"),
            codec=data.get("codec", "H.265"),
            fps=data.get("fps", 20),
            bitrate_mbps=data.get("bitrateMbps", 4.0),
            bitrate_mode=data.get("bitrateMode", "VBR"),
            gop_size=data.get("gopSize"),
            profile=data.get("profile"),
            quality=data.get("quality"),
        )


@dataclass
class ExposureSettings:
    """Exposure and light control settings"""
    mode: str = "Auto"  # "Auto", "Manual", "Shutter Priority", "Aperture Priority"
    shutter: Optional[str] = None  # "1/250", "1/500", etc.
    iris: Optional[str] = None  # "Auto", "F1.6", "F2.0"
    gain: Optional[int] = None  # dB value
    gain_limit: Optional[int] = None  # Max gain in dB
    wdr: str = "Medium"  # "Off", "Low", "Medium", "High"
    wdr_level: Optional[int] = None  # 0-100 for fine control
    blc: str = "Off"  # Backlight compensation
    hlc: Optional[str] = None  # Highlight compensation
    exposure_compensation: Optional[int] = None  # -2 to +2 EV
    metering_mode: Optional[str] = None  # "Center", "Average", "Spot"

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "mode": self.mode,
            "wdr": self.wdr,
            "blc": self.blc,
        }
        if self.shutter:
            result["shutter"] = self.shutter
        if self.iris:
            result["iris"] = self.iris
        if self.gain is not None:
            result["gain"] = self.gain
        if self.gain_limit is not None:
            result["gainLimit"] = self.gain_limit
        if self.wdr_level is not None:
            result["wdrLevel"] = self.wdr_level
        if self.hlc:
            result["hlc"] = self.hlc
        if self.exposure_compensation is not None:
            result["exposureCompensation"] = self.exposure_compensation
        if self.metering_mode:
            result["meteringMode"] = self.metering_mode
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ExposureSettings":
        return cls(
            mode=data.get("mode", "Auto"),
            shutter=data.get("shutter"),
            iris=data.get("iris"),
            gain=data.get("gain"),
            gain_limit=data.get("gainLimit"),
            wdr=data.get("wdr", "Medium"),
            wdr_level=data.get("wdrLevel"),
            blc=data.get("blc", "Off"),
            hlc=data.get("hlc"),
            exposure_compensation=data.get("exposureCompensation"),
            metering_mode=data.get("meteringMode"),
        )


@dataclass
class LowLightSettings:
    """Low-light and IR settings"""
    ir_mode: str = "Auto"  # "Off", "Auto", "On", "Smart"
    ir_intensity: Optional[int] = None  # 0-100
    day_night_mode: str = "Auto"  # "Auto", "Day", "Night", "Schedule"
    day_night_threshold: Optional[int] = None  # Lux threshold
    dnr: str = "Medium"  # Digital noise reduction: "Off", "Low", "Medium", "High"
    dnr_level: Optional[int] = None  # 0-100 for fine control
    slow_shutter: str = "Off"  # "Off", "Auto", "1/15", "1/8", etc.
    sensitivity: Optional[str] = None  # "Low", "Medium", "High"

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "irMode": self.ir_mode,
            "dayNightMode": self.day_night_mode,
            "dnr": self.dnr,
            "slowShutter": self.slow_shutter,
        }
        if self.ir_intensity is not None:
            result["irIntensity"] = self.ir_intensity
        if self.day_night_threshold is not None:
            result["dayNightThreshold"] = self.day_night_threshold
        if self.dnr_level is not None:
            result["dnrLevel"] = self.dnr_level
        if self.sensitivity:
            result["sensitivity"] = self.sensitivity
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LowLightSettings":
        return cls(
            ir_mode=data.get("irMode", "Auto"),
            ir_intensity=data.get("irIntensity"),
            day_night_mode=data.get("dayNightMode", "Auto"),
            day_night_threshold=data.get("dayNightThreshold"),
            dnr=data.get("dnr", data.get("noiseReduction", "Medium")),
            dnr_level=data.get("dnrLevel"),
            slow_shutter=data.get("slowShutter", "Off"),
            sensitivity=data.get("sensitivity"),
        )


@dataclass
class ImageSettings:
    """Image processing settings"""
    sharpness: int = 50  # 0-100
    contrast: int = 50  # 0-100
    saturation: int = 50  # 0-100
    brightness: int = 50  # 0-100
    hue: Optional[int] = None  # 0-100
    gamma: Optional[float] = None  # 0.1-2.0
    white_balance: str = "Auto"  # "Auto", "Indoor", "Outdoor", "Manual"
    white_balance_red: Optional[int] = None  # For manual WB
    white_balance_blue: Optional[int] = None  # For manual WB
    mirror: bool = False
    flip: bool = False
    rotation: int = 0  # 0, 90, 180, 270
    defog: Optional[str] = None  # "Off", "Low", "Medium", "High"
    ldc: Optional[str] = None  # Lens distortion correction

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "sharpness": self.sharpness,
            "contrast": self.contrast,
            "saturation": self.saturation,
            "brightness": self.brightness,
            "whiteBalance": self.white_balance,
            "mirror": self.mirror,
            "flip": self.flip,
            "rotation": self.rotation,
        }
        if self.hue is not None:
            result["hue"] = self.hue
        if self.gamma is not None:
            result["gamma"] = self.gamma
        if self.defog:
            result["defog"] = self.defog
        if self.ldc:
            result["ldc"] = self.ldc
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ImageSettings":
        return cls(
            sharpness=data.get("sharpness", data.get("sharpening", 50)),
            contrast=data.get("contrast", 50),
            saturation=data.get("saturation", 50),
            brightness=data.get("brightness", 50),
            hue=data.get("hue"),
            gamma=data.get("gamma"),
            white_balance=data.get("whiteBalance", "Auto"),
            white_balance_red=data.get("whiteBalanceRed"),
            white_balance_blue=data.get("whiteBalanceBlue"),
            mirror=data.get("mirror", False),
            flip=data.get("flip", False),
            rotation=data.get("rotation", 0),
            defog=data.get("defog"),
            ldc=data.get("ldc"),
        )


@dataclass
class CameraCurrentSettings:
    """Current camera configuration"""
    camera_id: str
    stream: StreamSettings = field(default_factory=StreamSettings)
    exposure: ExposureSettings = field(default_factory=ExposureSettings)
    low_light: LowLightSettings = field(default_factory=LowLightSettings)
    image: ImageSettings = field(default_factory=ImageSettings)
    queried_at: datetime = field(default_factory=datetime.utcnow)
    source: str = "onvif"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cameraId": self.camera_id,
            "stream": self.stream.to_dict(),
            "exposure": self.exposure.to_dict(),
            "lowLight": self.low_light.to_dict(),
            "image": self.image.to_dict(),
            "queriedAt": self.queried_at.isoformat() + "Z",
            "source": self.source,
        }

    @classmethod
    def from_dict(cls, camera_id: str, data: Dict[str, Any]) -> "CameraCurrentSettings":
        return cls(
            camera_id=camera_id,
            stream=StreamSettings.from_dict(data.get("stream") or {}),
            exposure=ExposureSettings.from_dict(data.get("exposure") or {}),
            low_light=LowLightSettings.from_dict(data.get("lowLight") or {}),
            image=ImageSettings.from_dict(data.get("image") or {}),
            source=data.get("source", "onvif"),
        )


# =============================================================================
# OPTIMIZATION MODELS
# =============================================================================

@dataclass
class CameraContext:
    """Context about the camera and its deployment"""
    id: str
    ip: str
    location: str
    scene_type: SceneType
    purpose: CameraPurpose
    vendor: Optional[str] = None
    model: Optional[str] = None
    vms_system: Optional[str] = None
    vms_camera_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "ip": self.ip,
            "location": self.location,
            "sceneType": self.scene_type.value,
            "purpose": self.purpose.value,
            "vendor": self.vendor,
            "model": self.model,
            "vmsSystem": self.vms_system,
            "vmsCameraId": self.vms_camera_id,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CameraContext":
        return cls(
            id=data.get("id", "unknown"),
            ip=data.get("ip", "0.0.0.0"),
            location=data.get("location", "Unknown"),
            scene_type=SceneType(data.get("sceneType", "generic")),
            purpose=CameraPurpose(data.get("purpose", "overview")),
            vendor=data.get("vendor"),
            model=data.get("model"),
            vms_system=data.get("vmsSystem"),
            vms_camera_id=data.get("vmsCameraId"),
        )


@dataclass
class OptimizationContext:
    """Additional context for optimization"""
    bandwidth_limit_mbps: Optional[float] = None
    target_retention_days: Optional[int] = None
    sample_frame: Optional[str] = None  # Base64 encoded image
    notes: Optional[str] = None
    lighting_condition: Optional[str] = None  # "bright", "mixed", "low"
    motion_level: Optional[str] = None  # "low", "medium", "high"

    def to_dict(self) -> Dict[str, Any]:
        result = {}
        if self.bandwidth_limit_mbps is not None:
            result["bandwidthLimitMbps"] = self.bandwidth_limit_mbps
        if self.target_retention_days is not None:
            result["targetRetentionDays"] = self.target_retention_days
        if self.sample_frame:
            result["sampleFrame"] = self.sample_frame
        if self.notes:
            result["notes"] = self.notes
        if self.lighting_condition:
            result["lightingCondition"] = self.lighting_condition
        if self.motion_level:
            result["motionLevel"] = self.motion_level
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "OptimizationContext":
        return cls(
            bandwidth_limit_mbps=data.get("bandwidthLimitMbps"),
            target_retention_days=data.get("targetRetentionDays"),
            sample_frame=data.get("sampleFrame"),
            notes=data.get("notes"),
            lighting_condition=data.get("lightingCondition"),
            motion_level=data.get("motionLevel"),
        )


@dataclass
class RecommendedSettings:
    """Recommended camera settings from optimization"""
    stream: StreamSettings = field(default_factory=StreamSettings)
    exposure: ExposureSettings = field(default_factory=ExposureSettings)
    low_light: LowLightSettings = field(default_factory=LowLightSettings)
    image: ImageSettings = field(default_factory=ImageSettings)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "stream": self.stream.to_dict(),
            "exposure": self.exposure.to_dict(),
            "lowLight": self.low_light.to_dict(),
            "image": self.image.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RecommendedSettings":
        return cls(
            stream=StreamSettings.from_dict(data.get("stream", {})),
            exposure=ExposureSettings.from_dict(data.get("exposure", {})),
            low_light=LowLightSettings.from_dict(data.get("lowLight", {})),
            image=ImageSettings.from_dict(data.get("image", {})),
        )


@dataclass
class OptimizationResult:
    """Result of an optimization request"""
    camera_id: str
    recommended_settings: RecommendedSettings
    confidence: float  # 0.0 - 1.0
    explanation: str
    warnings: List[str] = field(default_factory=list)
    provider: str = "heuristic"
    processing_time_seconds: float = 0.0
    generated_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cameraId": self.camera_id,
            "recommendedSettings": self.recommended_settings.to_dict(),
            "confidence": self.confidence,
            "explanation": self.explanation,
            "warnings": self.warnings,
            "aiProvider": self.provider,
            "processingTime": self.processing_time_seconds,
            "generatedAt": self.generated_at.isoformat() + "Z",
        }


# =============================================================================
# APPLY MODELS
# =============================================================================

@dataclass
class ApplyRequest:
    """Request to apply settings to a camera"""
    camera_id: str
    settings: RecommendedSettings
    apply_via: ApplyMethod = ApplyMethod.ONVIF
    verify_after: bool = True
    credentials_username: Optional[str] = None
    credentials_password: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cameraId": self.camera_id,
            "settings": self.settings.to_dict(),
            "applyVia": self.apply_via.value,
            "verifyAfter": self.verify_after,
        }


@dataclass
class SettingMismatch:
    """A setting that didn't match after apply"""
    category: str  # "stream", "exposure", "lowLight", "image"
    setting: str  # "fps", "wdr", etc.
    expected: Any
    actual: Any

    def to_dict(self) -> Dict[str, Any]:
        return {
            "category": self.category,
            "setting": self.setting,
            "expected": self.expected,
            "actual": self.actual,
        }


@dataclass
class VerificationResult:
    """Result of settings verification after apply"""
    verified: bool
    mismatches: List[SettingMismatch] = field(default_factory=list)
    verified_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "verified": self.verified,
            "mismatches": [m.to_dict() for m in self.mismatches],
            "verifiedAt": self.verified_at.isoformat() + "Z",
        }


@dataclass
class ApplyResult:
    """Result of a settings apply job"""
    job_id: str
    status: ApplyStatus
    camera_id: str
    applied_settings: Optional[Dict[str, Any]] = None
    verification: Optional[VerificationResult] = None
    errors: List[str] = field(default_factory=list)
    started_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "jobId": self.job_id,
            "status": self.status.value,
            "cameraId": self.camera_id,
            "errors": self.errors,
            "startedAt": self.started_at.isoformat() + "Z",
        }
        if self.applied_settings:
            result["appliedSettings"] = self.applied_settings
        if self.verification:
            result["verification"] = self.verification.to_dict()
        if self.completed_at:
            result["completedAt"] = self.completed_at.isoformat() + "Z"
        return result


# =============================================================================
# PIPELINE CONTEXT
# =============================================================================

@dataclass
class PipelineError:
    """Error that occurred during pipeline execution"""
    stage: str
    error_type: str
    message: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    recoverable: bool = True
    details: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "stage": self.stage,
            "errorType": self.error_type,
            "message": self.message,
            "timestamp": self.timestamp.isoformat() + "Z",
            "recoverable": self.recoverable,
        }
        if self.details:
            result["details"] = self.details
        return result


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
    camera_context: Optional[CameraContext] = None
    discovered_camera: Optional[DiscoveredCamera] = None
    capabilities: Optional[CameraCapabilities] = None
    current_settings: Optional[CameraCurrentSettings] = None
    optimization_context: Optional[OptimizationContext] = None
    optimization_result: Optional[OptimizationResult] = None
    apply_result: Optional[ApplyResult] = None

    # Error tracking
    errors: List[PipelineError] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    # Feature flags
    skip_capability_query: bool = False
    skip_current_settings: bool = False
    dry_run: bool = False  # Don't actually apply

    def add_error(
        self,
        stage: str,
        error_type: str,
        message: str,
        recoverable: bool = True,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        """Add an error to the context"""
        self.errors.append(PipelineError(
            stage=stage,
            error_type=error_type,
            message=message,
            recoverable=recoverable,
            details=details,
        ))

    def add_warning(self, message: str) -> None:
        """Add a warning to the context"""
        self.warnings.append(message)

    def record_stage_time(self, stage: str, duration: float) -> None:
        """Record the time taken for a pipeline stage"""
        self.stage_times[stage] = duration

    def has_errors(self) -> bool:
        """Check if any errors occurred"""
        return len(self.errors) > 0

    def has_fatal_errors(self) -> bool:
        """Check if any non-recoverable errors occurred"""
        return any(not e.recoverable for e in self.errors)

    def get_total_time(self) -> float:
        """Get total pipeline execution time"""
        return (datetime.utcnow() - self.started_at).total_seconds()

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "requestId": self.request_id,
            "siteId": self.site_id,
            "userId": self.user_id,
            "startedAt": self.started_at.isoformat() + "Z",
            "stageTimes": self.stage_times,
            "totalTime": self.get_total_time(),
            "errors": [e.to_dict() for e in self.errors],
            "warnings": self.warnings,
            "dryRun": self.dry_run,
        }
        if self.camera_context:
            result["cameraContext"] = self.camera_context.to_dict()
        if self.capabilities:
            result["capabilities"] = self.capabilities.to_dict()
        if self.optimization_result:
            result["optimizationResult"] = self.optimization_result.to_dict()
        if self.apply_result:
            result["applyResult"] = self.apply_result.to_dict()
        return result
