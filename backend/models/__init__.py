# backend/models/__init__.py
"""
PlatoniCam Data Models

This package contains all data models for the optimization pipeline.
Includes both Pydantic models (API validation) and SQLAlchemy models (persistence).
"""

from .pipeline import (
    # Enums
    SceneType,
    CameraPurpose,
    ApplyMethod,
    ApplyStatus,

    # Camera models
    DiscoveredCamera,
    CameraCapabilities,
    StreamSettings,
    ExposureSettings,
    LowLightSettings,
    ImageSettings,
    CameraCurrentSettings,

    # Optimization models
    CameraContext,
    OptimizationContext,
    RecommendedSettings,
    OptimizationResult,

    # Apply models
    ApplyRequest,
    SettingMismatch,
    VerificationResult,
    ApplyResult,

    # Pipeline
    PipelineError as PipelineErrorModel,
    PipelineContext,
)

__all__ = [
    # Enums
    "SceneType",
    "CameraPurpose",
    "ApplyMethod",
    "ApplyStatus",

    # Camera models
    "DiscoveredCamera",
    "CameraCapabilities",
    "StreamSettings",
    "ExposureSettings",
    "LowLightSettings",
    "ImageSettings",
    "CameraCurrentSettings",

    # Optimization models
    "CameraContext",
    "OptimizationContext",
    "RecommendedSettings",
    "OptimizationResult",

    # Apply models
    "ApplyRequest",
    "SettingMismatch",
    "VerificationResult",
    "ApplyResult",

    # Pipeline
    "PipelineErrorModel",
    "PipelineContext",
    # ORM Models
    "CameraDatasheet",
    "DatasheetFetchLog",
    "Camera",
    "Optimization",
    "AppliedConfig",
]

# Import ORM models (deferred to avoid circular imports)
try:
    from .orm import (
        CameraDatasheet,
        DatasheetFetchLog,
        Camera,
        Optimization,
        AppliedConfig,
    )
except ImportError:
    # ORM models may not be available if database is not initialized
    pass
