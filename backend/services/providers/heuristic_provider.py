# backend/services/providers/heuristic_provider.py
"""
Heuristic optimization provider.

Rule-based optimization that works offline without AI.
Used as fallback when Claude is unavailable.
"""

import logging
from datetime import datetime
from typing import Optional, List, Dict, Any

from .base import OptimizationProvider, ProviderInfo, ProviderCapability
from models import (
    CameraContext,
    CameraCapabilities,
    CameraCurrentSettings,
    OptimizationContext,
    OptimizationResult,
    RecommendedSettings,
    StreamSettings,
    ExposureSettings,
    LowLightSettings,
    ImageSettings,
    SceneType,
    CameraPurpose,
)
from models.pipeline import PipelineContext

logger = logging.getLogger(__name__)


# Heuristic rule definitions
PURPOSE_RULES: Dict[CameraPurpose, Dict[str, Any]] = {
    CameraPurpose.PLATES: {
        "min_fps": 25,
        "shutter": "1/500",
        "slow_shutter": "Off",
        "wdr": "Off",  # WDR causes ghosting on fast-moving plates
        "hlc": "On",  # Mask headlight glare
        "gain_limit": 24,  # Limit noise, prioritize fast shutter
        "explanation": "License plate recognition requires fast shutter (1/500+) to freeze motion. HLC masks headlight glare. WDR disabled to prevent ghosting artifacts on moving vehicles.",
    },
    CameraPurpose.FACIAL: {
        "min_fps": 20,
        "shutter": "1/250",
        "explanation": "Facial recognition needs fast shutter and good detail",
    },
    CameraPurpose.OVERVIEW: {
        "min_fps": 10,
        "explanation": "Overview coverage prioritizes wide field of view over detail",
    },
    CameraPurpose.EVIDENCE: {
        "min_fps": 15,
        "codec": "H.265",
        "bitrate_mode": "CBR",
        "explanation": "Evidentiary recording needs consistent quality",
    },
    CameraPurpose.COUNTING: {
        "min_fps": 10,
        "explanation": "People counting analytics work well with moderate FPS",
    },
    CameraPurpose.INTRUSION: {
        "min_fps": 15,
        "explanation": "Intrusion detection needs good motion capture",
    },
    CameraPurpose.GENERAL: {
        "min_fps": 15,
        "explanation": "General purpose settings provide balanced performance",
    },
}

SCENE_RULES: Dict[SceneType, Dict[str, Any]] = {
    SceneType.ENTRANCE: {
        "wdr": "High",
        "explanation": "Entrances often have high contrast (bright exterior vs dark interior)",
    },
    SceneType.LOADING_DOCK: {
        "wdr": "High",
        "explanation": "Loading docks have challenging lighting with open bay doors",
    },
    SceneType.PARKING: {
        "wdr": "Medium",
        "hlc": "On",  # Mask headlight glare from incoming vehicles
        "ir_mode": "Auto",
        "explanation": "Parking areas need HLC for headlight glare and WDR for mixed lighting conditions",
    },
    SceneType.EXTERIOR_NIGHT: {
        "ir_mode": "Auto",
        "ir_level": 75,
        "dnr": "High",
        "explanation": "Nighttime exterior requires IR illumination and noise reduction",
    },
    SceneType.HALLWAY: {
        "wdr": "Low",
        "explanation": "Hallways typically have consistent artificial lighting",
    },
    SceneType.WAREHOUSE: {
        "wdr": "Medium",
        "explanation": "Warehouses may have mixed natural and artificial light",
    },
    SceneType.RETAIL: {
        "wdr": "Medium",
        "saturation": 55,
        "explanation": "Retail needs good color reproduction for merchandise",
    },
    SceneType.OFFICE: {
        "wdr": "Low",
        "explanation": "Offices typically have consistent overhead lighting",
    },
    SceneType.STAIRWELL: {
        "wdr": "Medium",
        "explanation": "Stairwells may have variable lighting conditions",
    },
    SceneType.LOBBY: {
        "wdr": "High",
        "explanation": "Lobbies often have large windows creating backlight",
    },
    SceneType.PERIMETER: {
        "ir_mode": "Auto",
        "wdr": "Medium",
        "explanation": "Perimeter cameras face day/night transitions",
    },
    SceneType.ATM: {
        "wdr": "High",
        "min_fps": 20,
        "explanation": "ATM cameras need high detail with screen glare handling",
    },
    SceneType.CASH_REGISTER: {
        "min_fps": 20,
        "shutter": "1/250",
        "explanation": "POS areas need clear capture of transactions",
    },
    SceneType.SERVER_ROOM: {
        "ir_mode": "Off",
        "explanation": "Server rooms typically have consistent artificial light",
    },
}


class HeuristicOptimizationProvider(OptimizationProvider):
    """
    Rule-based optimization provider.

    Applies predefined heuristics based on scene type and camera purpose.
    Works offline and serves as fallback for AI-based providers.
    """

    @property
    def info(self) -> ProviderInfo:
        return ProviderInfo(
            name="heuristic",
            version="1.0",
            capabilities=[
                ProviderCapability.OFFLINE,
            ],
            requires_api_key=False,
            supports_fallback=False,  # This IS the fallback
            description="Rule-based optimization using industry best practices",
        )

    def is_available(self) -> bool:
        """Heuristic provider is always available"""
        return True

    async def optimize(
        self,
        camera: CameraContext,
        capabilities: CameraCapabilities,
        current_settings: Optional[CameraCurrentSettings],
        context: OptimizationContext,
        pipeline: Optional[PipelineContext] = None,
    ) -> OptimizationResult:
        """
        Generate optimal settings using rule-based heuristics.
        """
        start_time = datetime.utcnow()

        # Start with current settings as baseline
        stream_settings = self._get_baseline_stream(current_settings, capabilities)
        exposure_settings = self._get_baseline_exposure(current_settings)
        low_light_settings = self._get_baseline_low_light(current_settings)
        image_settings = self._get_baseline_image(current_settings)

        explanations = []

        # Apply purpose rules
        if camera.purpose:
            purpose_rule = PURPOSE_RULES.get(camera.purpose)
            if purpose_rule:
                self._apply_purpose_rule(
                    purpose_rule,
                    stream_settings,
                    exposure_settings,
                    low_light_settings,
                )
                explanations.append(purpose_rule.get("explanation", ""))

        # Apply scene type rules
        if camera.scene_type:
            scene_rule = SCENE_RULES.get(camera.scene_type)
            if scene_rule:
                self._apply_scene_rule(
                    scene_rule,
                    exposure_settings,
                    low_light_settings,
                    image_settings,
                    stream_settings,
                )
                explanations.append(scene_rule.get("explanation", ""))

        # Apply bandwidth constraints
        if context.bandwidth_limit_mbps:
            self._apply_bandwidth_constraint(
                stream_settings,
                context.bandwidth_limit_mbps,
                capabilities,
            )

        # Clamp values to capabilities
        self._clamp_to_capabilities(stream_settings, capabilities)

        recommended = RecommendedSettings(
            stream=stream_settings,
            exposure=exposure_settings,
            low_light=low_light_settings,
            image=image_settings,
        )

        # Generate warnings
        warnings = self._generate_warnings(recommended, capabilities, context)

        processing_time = (datetime.utcnow() - start_time).total_seconds()

        if pipeline:
            pipeline.record_stage_time("optimization", processing_time)

        explanation = self._build_explanation(camera, explanations)

        return OptimizationResult(
            camera_id=camera.id,
            recommended_settings=recommended,
            confidence=0.6,  # Heuristics have moderate confidence
            explanation=explanation,
            warnings=warnings,
            provider="heuristic",
            processing_time_seconds=processing_time,
        )

    def _get_baseline_stream(
        self,
        current: Optional[CameraCurrentSettings],
        capabilities: CameraCapabilities,
    ) -> StreamSettings:
        """Get baseline stream settings"""
        if current and current.stream:
            return StreamSettings(
                resolution=current.stream.resolution or capabilities.supported_resolutions[0] if capabilities.supported_resolutions else "1920x1080",
                fps=current.stream.fps or 15,
                codec=current.stream.codec or (capabilities.supported_codecs[0] if capabilities.supported_codecs else "H.264"),
                bitrate_mode=current.stream.bitrate_mode or "VBR",
                bitrate_mbps=current.stream.bitrate_mbps or 4.0,
                gop_size=current.stream.gop_size or 30,  # ~2 seconds at 15fps
                profile=current.stream.profile,
            )
        return StreamSettings(
            resolution=capabilities.supported_resolutions[0] if capabilities.supported_resolutions else "1920x1080",
            fps=15,
            codec=capabilities.supported_codecs[0] if capabilities.supported_codecs else "H.264",
            bitrate_mode="VBR",
            bitrate_mbps=4.0,
            gop_size=30,  # ~2 seconds at 15fps
        )

    def _get_baseline_exposure(
        self,
        current: Optional[CameraCurrentSettings],
    ) -> ExposureSettings:
        """Get baseline exposure settings"""
        if current and current.exposure:
            return ExposureSettings(
                mode=current.exposure.mode or "Auto",
                shutter=current.exposure.shutter,
                gain_limit=current.exposure.gain_limit,
                wdr=current.exposure.wdr or "Off",
                blc=current.exposure.blc,
                hlc=current.exposure.hlc,
            )
        return ExposureSettings(
            mode="Auto",
            wdr="Off",
        )

    def _get_baseline_low_light(
        self,
        current: Optional[CameraCurrentSettings],
    ) -> LowLightSettings:
        """Get baseline low-light settings"""
        if current and current.low_light:
            return LowLightSettings(
                ir_mode=current.low_light.ir_mode or "Auto",
                ir_intensity=current.low_light.ir_intensity,
                day_night_mode=current.low_light.day_night_mode or "Auto",
                sensitivity=current.low_light.sensitivity,
                slow_shutter=current.low_light.slow_shutter or "Off",
                dnr=current.low_light.dnr or "Medium",
            )
        return LowLightSettings(
            ir_mode="Auto",
        )

    def _get_baseline_image(
        self,
        current: Optional[CameraCurrentSettings],
    ) -> ImageSettings:
        """Get baseline image settings"""
        if current and current.image:
            return ImageSettings(
                brightness=current.image.brightness or 50,
                contrast=current.image.contrast or 50,
                saturation=current.image.saturation or 50,
                sharpness=current.image.sharpness or 50,
                white_balance=current.image.white_balance or "Auto",
                defog=current.image.defog,
            )
        return ImageSettings(
            brightness=50,
            contrast=50,
            saturation=50,
            sharpness=50,
            white_balance="Auto",
        )

    def _apply_purpose_rule(
        self,
        rule: Dict[str, Any],
        stream: StreamSettings,
        exposure: ExposureSettings,
        low_light: LowLightSettings,
    ) -> None:
        """Apply purpose-based rules"""
        if "min_fps" in rule:
            stream.fps = max(stream.fps or 15, rule["min_fps"])

        if "shutter" in rule:
            exposure.shutter = rule["shutter"]

        if "slow_shutter" in rule:
            low_light.slow_shutter = rule["slow_shutter"]

        if "codec" in rule:
            stream.codec = rule["codec"]

        if "bitrate_mode" in rule:
            stream.bitrate_mode = rule["bitrate_mode"]

        if "wdr" in rule:
            exposure.wdr = rule["wdr"]

        if "hlc" in rule:
            exposure.hlc = rule["hlc"]

        if "gain_limit" in rule:
            exposure.gain_limit = rule["gain_limit"]

    def _apply_scene_rule(
        self,
        rule: Dict[str, Any],
        exposure: ExposureSettings,
        low_light: LowLightSettings,
        image: ImageSettings,
        stream: StreamSettings,
    ) -> None:
        """Apply scene-type based rules"""
        if "wdr" in rule:
            exposure.wdr = rule["wdr"]

        if "hlc" in rule:
            exposure.hlc = rule["hlc"]

        if "ir_mode" in rule:
            low_light.ir_mode = rule["ir_mode"]

        if "ir_level" in rule:
            low_light.ir_level = rule["ir_level"]

        if "dnr" in rule:
            low_light.dnr = rule["dnr"]

        if "saturation" in rule:
            image.saturation = rule["saturation"]

        if "min_fps" in rule:
            stream.fps = max(stream.fps or 15, rule["min_fps"])

        if "shutter" in rule:
            exposure.shutter = rule["shutter"]

    def _apply_bandwidth_constraint(
        self,
        stream: StreamSettings,
        bandwidth_limit: float,
        capabilities: CameraCapabilities,
    ) -> None:
        """Adjust settings to meet bandwidth constraint"""
        # Simple heuristic: reduce FPS or resolution if bitrate would exceed limit
        estimated_bitrate = self._estimate_bitrate(stream)

        if estimated_bitrate > bandwidth_limit:
            # First try reducing FPS
            if stream.fps and stream.fps > 10:
                stream.fps = max(10, int(stream.fps * 0.7))
                estimated_bitrate = self._estimate_bitrate(stream)

            # If still over, suggest lower resolution
            if estimated_bitrate > bandwidth_limit and capabilities.supported_resolutions:
                current_idx = 0
                if stream.resolution in capabilities.supported_resolutions:
                    current_idx = capabilities.supported_resolutions.index(stream.resolution)
                if current_idx < len(capabilities.supported_resolutions) - 1:
                    stream.resolution = capabilities.supported_resolutions[current_idx + 1]

    def _estimate_bitrate(self, stream: StreamSettings) -> float:
        """Rough bitrate estimate in Mbps"""
        # Simple estimation based on resolution and FPS
        resolution_factor = {
            "3840x2160": 4.0,
            "2560x1440": 2.0,
            "1920x1080": 1.0,
            "1280x720": 0.5,
            "640x480": 0.2,
        }.get(stream.resolution or "1920x1080", 1.0)

        fps_factor = (stream.fps or 15) / 15.0
        codec_factor = 0.5 if stream.codec == "H.265" else 1.0

        # Base bitrate of ~4 Mbps for 1080p/15fps/H.264
        return 4.0 * resolution_factor * fps_factor * codec_factor

    def _clamp_to_capabilities(
        self,
        stream: StreamSettings,
        capabilities: CameraCapabilities,
    ) -> None:
        """Ensure settings don't exceed camera capabilities"""
        if stream.fps and stream.fps > capabilities.max_fps:
            stream.fps = capabilities.max_fps

        if stream.codec and stream.codec not in capabilities.supported_codecs:
            if capabilities.supported_codecs:
                stream.codec = capabilities.supported_codecs[0]

        if stream.resolution and capabilities.supported_resolutions:
            if stream.resolution not in capabilities.supported_resolutions:
                stream.resolution = capabilities.supported_resolutions[0]

    def _generate_warnings(
        self,
        settings: RecommendedSettings,
        capabilities: CameraCapabilities,
        context: OptimizationContext,
    ) -> List[str]:
        """Generate warnings for constraint violations"""
        warnings = []

        if not context.sample_frame:
            warnings.append(
                "No sample frame provided. Using heuristic optimization. "
                "Upload a sample image for AI-powered scene analysis."
            )

        return warnings

    def _build_explanation(
        self,
        camera: CameraContext,
        rule_explanations: List[str],
    ) -> str:
        """Build human-readable explanation"""
        parts = ["Heuristic-based optimization applied."]

        if camera.purpose:
            parts.append(f"Optimized for {camera.purpose.value} purpose.")

        if camera.scene_type:
            parts.append(f"Adjusted for {camera.scene_type.value} scene type.")

        parts.extend([e for e in rule_explanations if e])

        parts.append("For best results, use AI optimization with a sample frame.")

        return " ".join(parts)
