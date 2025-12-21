# backend/services/providers/gemini_provider.py
"""
Google Gemini AI optimization provider.

Uses Google's Gemini Vision API to analyze camera scenes
and generate optimal settings.
"""

import logging
from datetime import datetime
from typing import Optional, List

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
)
from models.pipeline import PipelineContext
from errors import (
    ProviderError,
    ProviderRateLimitError,
    ProviderAuthError,
    InvalidResponseError,
)
from config import get_settings

# Lazy imports to avoid circular dependencies when google-genai is not installed
GeminiVisionClient = None


def _get_gemini_client():
    """Lazy load Gemini client"""
    global GeminiVisionClient
    try:
        from integrations.gemini_client import get_gemini_client, GeminiVisionClient as GVC
        GeminiVisionClient = GVC
        return get_gemini_client()
    except ImportError as e:
        import logging
        logging.getLogger(__name__).warning(f"Could not load Gemini client: {e}")
        return None


logger = logging.getLogger(__name__)


class GeminiOptimizationProvider(OptimizationProvider):
    """
    Google Gemini Vision AI optimization provider.

    Analyzes sample frames and camera context to generate
    optimal settings using scene understanding.
    """

    def __init__(self, client=None):
        """
        Initialize Gemini provider.

        Args:
            client: Optional GeminiClient instance (uses singleton if not provided)
        """
        self._client = client
        self._settings = get_settings()

    @property
    def client(self):
        """Lazy-load Gemini client"""
        if self._client is None:
            self._client = _get_gemini_client()
        return self._client

    @property
    def info(self) -> ProviderInfo:
        return ProviderInfo(
            name="gemini",
            version="2.5-flash",
            capabilities=[
                ProviderCapability.SCENE_ANALYSIS,
                ProviderCapability.CONSTRAINT_SOLVING,
            ],
            requires_api_key=True,
            supports_fallback=True,
            description="Google Gemini Vision AI for intelligent scene-based optimization",
        )

    def is_available(self) -> bool:
        """Check if Gemini API is available"""
        try:
            return self.client is not None and self._settings.google_api_key
        except Exception:
            return False

    async def optimize(
        self,
        camera: CameraContext,
        capabilities: CameraCapabilities,
        current_settings: Optional[CameraCurrentSettings],
        context: OptimizationContext,
        pipeline: Optional[PipelineContext] = None,
    ) -> OptimizationResult:
        """
        Generate optimal settings using Google Gemini Vision AI.

        Analyzes the sample frame (if provided) along with camera context
        to produce scene-aware recommendations.
        """
        start_time = datetime.utcnow()

        try:
            # Build inputs for Gemini client
            camera_dict = {
                "id": camera.id,
                "sceneType": camera.scene_type.value if camera.scene_type else None,
                "purpose": camera.purpose.value if camera.purpose else None,
                "location": camera.location,
                "manufacturer": camera.vendor,  # CameraContext uses 'vendor'
                "model": camera.model,
            }

            current_dict = current_settings.to_dict() if current_settings else {}
            capabilities_dict = capabilities.to_dict()

            constraints = {
                "bandwidthLimitMbps": context.bandwidth_limit_mbps,
                "targetRetentionDays": context.target_retention_days,
            }

            # Call Gemini API with datasheet specs if available
            recommended_dict, confidence, explanation, ai_warnings = (
                self.client.optimize_camera_settings(
                    camera_context=camera_dict,
                    current_settings=current_dict,
                    capabilities=capabilities_dict,
                    constraints=constraints,
                    sample_frame=context.sample_frame,
                    datasheet_specs=context.datasheet_specs,
                )
            )

            # Parse response into typed settings
            recommended = self._parse_recommended_settings(recommended_dict)

            # Combine AI warnings with constraint validation warnings
            validation_warnings = self._generate_warnings(recommended, capabilities, context)
            warnings = ai_warnings + validation_warnings

            processing_time = (datetime.utcnow() - start_time).total_seconds()

            if pipeline:
                pipeline.record_stage_time("optimization", processing_time)

            return OptimizationResult(
                camera_id=camera.id,
                recommended_settings=recommended,
                confidence=confidence,
                explanation=explanation,
                warnings=warnings,
                provider="gemini-2.5-flash",
                processing_time_seconds=processing_time,
            )

        except Exception as e:
            error_msg = str(e)
            logger.error(f"Gemini optimization error: {error_msg}", exc_info=True)

            # Map to specific error types based on Gemini's error patterns
            if "quota" in error_msg.lower() or "rate" in error_msg.lower() or "429" in error_msg:
                raise ProviderRateLimitError(provider="gemini")
            elif "api key" in error_msg.lower() or "401" in error_msg or "403" in error_msg:
                raise ProviderAuthError(provider="gemini")
            elif "invalid" in error_msg.lower() or "parse" in error_msg.lower():
                raise InvalidResponseError(message=error_msg, provider="gemini")
            else:
                raise ProviderError(
                    provider="gemini",
                    message=error_msg,
                )

    def _parse_recommended_settings(self, settings_dict: dict) -> RecommendedSettings:
        """Parse raw settings dict into typed RecommendedSettings"""

        stream = None
        if "stream" in settings_dict:
            s = settings_dict["stream"]
            stream = StreamSettings(
                resolution=s.get("resolution", "1920x1080"),
                fps=s.get("fps", 15),
                codec=s.get("codec", "H.264"),
                bitrate_mode=s.get("bitrateMode", "VBR"),
                bitrate_mbps=s.get("bitrateMbps", 4.0),
                gop_size=s.get("gopSize") or s.get("gopSeconds"),
                profile=s.get("profile"),
            )

        exposure = None
        if "exposure" in settings_dict:
            e = settings_dict["exposure"]
            exposure = ExposureSettings(
                mode=e.get("mode", "Auto"),
                shutter=e.get("shutter"),
                iris=e.get("iris"),
                gain_limit=e.get("gainLimit"),
                wdr=e.get("wdr", "Off"),
                blc=e.get("blc", "Off"),
                hlc=e.get("hlc") or e.get("HLC"),  # Handle both cases
            )

        low_light = None
        if "lowLight" in settings_dict:
            ll = settings_dict["lowLight"]
            low_light = LowLightSettings(
                ir_mode=ll.get("irMode", "Auto"),
                ir_intensity=ll.get("irIntensity") or ll.get("irLevel"),
                day_night_mode=ll.get("dayNightMode", "Auto"),
                sensitivity=ll.get("sensitivity"),
                slow_shutter=ll.get("slowShutter", "Off"),
                dnr=ll.get("dnr", "Medium"),
            )

        image = None
        if "image" in settings_dict:
            i = settings_dict["image"]
            image = ImageSettings(
                brightness=i.get("brightness", 50),
                contrast=i.get("contrast", 50),
                saturation=i.get("saturation", 50),
                sharpness=i.get("sharpness", 50),
                white_balance=i.get("whiteBalance", "Auto"),
                defog=i.get("defog"),
            )

        return RecommendedSettings(
            stream=stream or StreamSettings(),
            exposure=exposure or ExposureSettings(),
            low_light=low_light or LowLightSettings(),
            image=image or ImageSettings(),
        )

    def _generate_warnings(
        self,
        settings: RecommendedSettings,
        capabilities: CameraCapabilities,
        context: OptimizationContext,
    ) -> List[str]:
        """Generate warnings for constraint violations"""

        warnings = []

        # Check bandwidth
        if context.bandwidth_limit_mbps and settings.stream:
            if settings.stream.bitrate_mbps:
                if settings.stream.bitrate_mbps > context.bandwidth_limit_mbps:
                    warnings.append(
                        f"Recommended bitrate ({settings.stream.bitrate_mbps} Mbps) "
                        f"exceeds bandwidth limit ({context.bandwidth_limit_mbps} Mbps). "
                        "Consider reducing resolution or FPS."
                    )

        # Check FPS capability
        if settings.stream and settings.stream.fps:
            if settings.stream.fps > capabilities.max_fps:
                warnings.append(
                    f"Recommended FPS ({settings.stream.fps}) exceeds "
                    f"camera maximum ({capabilities.max_fps})"
                )

        # Check codec support
        if settings.stream and settings.stream.codec:
            if settings.stream.codec not in capabilities.supported_codecs:
                warnings.append(
                    f"Recommended codec ({settings.stream.codec}) may not be supported. "
                    f"Camera supports: {', '.join(capabilities.supported_codecs)}"
                )

        return warnings
