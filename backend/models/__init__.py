# backend/models/__init__.py
"""
PlatoniCam Data Models

This package contains all data models for the optimization pipeline.
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
]
