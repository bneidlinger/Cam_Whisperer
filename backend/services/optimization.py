# backend/services/optimization.py
"""
Camera optimization service

Orchestrates optimization pipeline using provider abstraction layer.
Supports AI-powered and heuristic camera configuration optimization.
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional
from uuid import uuid4

from models import (
    CameraContext,
    CameraCapabilities,
    CameraCurrentSettings,
    OptimizationContext,
    OptimizationResult,
    SceneType,
    CameraPurpose,
)
from models.pipeline import PipelineContext
from services.providers import (
    get_provider,
    get_available_providers,
    ProviderType,
)
from errors import (
    OptimizationError,
    ProviderError,
)
from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class OptimizationService:
    """
    Service for generating optimal camera settings.

    Manages the optimization pipeline, provider selection,
    and fallback strategies.
    """

    def __init__(self):
        """Initialize optimization service"""
        self._fallback_enabled = settings.fallback_to_heuristic

    async def optimize(
        self,
        camera: Dict[str, Any],
        capabilities: Dict[str, Any],
        current_settings: Dict[str, Any],
        context: Dict[str, Any],
        provider_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Generate optimal camera settings.

        This is the main entry point that maintains backward compatibility
        with the existing API while using the new provider abstraction internally.

        Args:
            camera: Camera metadata (id, location, sceneType, purpose)
            capabilities: Hardware capabilities
            current_settings: Current configuration
            context: Optimization context (bandwidth, retention, sample frame)
            provider_type: Optional provider override ("claude" or "heuristic")

        Returns:
            OptimizeResponse dict with recommendations
        """
        request_id = str(uuid4())
        camera_id = camera.get("id", "unknown")

        logger.info(f"[{request_id}] Starting optimization for camera {camera_id}")

        # Create pipeline context for tracking
        pipeline = PipelineContext(
            request_id=request_id,
            site_id=context.get("siteId"),
        )

        try:
            # Parse inputs into typed models
            camera_ctx = self._parse_camera_context(camera)
            caps = self._parse_capabilities(capabilities)
            current = self._parse_current_settings(current_settings)
            opt_context = self._parse_optimization_context(context)

            # Store in pipeline context
            pipeline.camera_context = camera_ctx
            pipeline.capabilities = caps

            # Get provider (handles fallback internally)
            ptype = ProviderType(provider_type) if provider_type else None
            provider = get_provider(
                provider_type=ptype,
                fallback=self._fallback_enabled,
            )

            logger.info(f"[{request_id}] Using provider: {provider.name}")

            # Execute optimization
            start_time = datetime.utcnow()

            try:
                result = await provider.optimize(
                    camera=camera_ctx,
                    capabilities=caps,
                    current_settings=current,
                    context=opt_context,
                    pipeline=pipeline,
                )
            except ProviderError as e:
                # Try fallback if enabled
                if self._fallback_enabled and provider.name != "heuristic":
                    logger.warning(
                        f"[{request_id}] Provider {provider.name} failed: {e}. "
                        "Falling back to heuristic."
                    )
                    pipeline.add_error(
                        stage="optimization",
                        error_type=type(e).__name__,
                        message=str(e),
                        recoverable=True,
                        details={"provider": provider.name},
                    )

                    fallback_provider = get_provider(
                        provider_type=ProviderType.HEURISTIC,
                        fallback=False,
                    )
                    result = await fallback_provider.optimize(
                        camera=camera_ctx,
                        capabilities=caps,
                        current_settings=current,
                        context=opt_context,
                        pipeline=pipeline,
                    )
                else:
                    raise

            processing_time = (datetime.utcnow() - start_time).total_seconds()
            pipeline.record_stage_time("optimization_total", processing_time)

            # Store result in pipeline
            pipeline.optimization_result = result

            logger.info(
                f"[{request_id}] Optimization complete. "
                f"Provider: {result.provider}, Confidence: {result.confidence:.2f}, "
                f"Time: {result.processing_time_seconds:.3f}s"
            )

            # Convert to API response format
            return self._to_response(result, pipeline)

        except Exception as e:
            logger.error(f"[{request_id}] Optimization failed: {e}", exc_info=True)
            pipeline.add_error(
                stage="optimization",
                error_type=type(e).__name__,
                message=str(e),
                recoverable=False,
            )
            raise OptimizationError(
                message=f"Optimization failed: {e}",
                details={"requestId": request_id},
            )

    async def optimize_typed(
        self,
        camera: CameraContext,
        capabilities: CameraCapabilities,
        current_settings: Optional[CameraCurrentSettings],
        context: OptimizationContext,
        pipeline: Optional[PipelineContext] = None,
        provider_type: Optional[ProviderType] = None,
    ) -> OptimizationResult:
        """
        Generate optimal camera settings using typed models.

        This is the new typed interface for internal use.

        Args:
            camera: Camera context with scene type and purpose
            capabilities: Camera hardware capabilities
            current_settings: Current camera settings (optional)
            context: Optimization constraints and sample frame
            pipeline: Pipeline context for tracking (optional)
            provider_type: Specific provider to use (optional)

        Returns:
            OptimizationResult with recommendations
        """
        if pipeline is None:
            pipeline = PipelineContext()

        provider = get_provider(
            provider_type=provider_type,
            fallback=self._fallback_enabled,
        )

        return await provider.optimize(
            camera=camera,
            capabilities=capabilities,
            current_settings=current_settings,
            context=context,
            pipeline=pipeline,
        )

    def get_available_providers(self) -> list:
        """Get list of available optimization providers"""
        return [p.to_dict() for p in get_available_providers()]

    def _parse_camera_context(self, camera: Dict[str, Any]) -> CameraContext:
        """Parse camera dict to typed CameraContext"""
        # Handle scene_type parsing with fallback
        scene_type_val = camera.get("sceneType", "generic")
        try:
            SceneType(scene_type_val)
        except ValueError:
            logger.warning(f"Unknown scene type: {scene_type_val}, using 'generic'")
            scene_type_val = "generic"

        # Handle purpose parsing with fallback
        purpose_val = camera.get("purpose", "overview")
        try:
            CameraPurpose(purpose_val)
        except ValueError:
            logger.warning(f"Unknown purpose: {purpose_val}, using 'overview'")
            purpose_val = "overview"

        return CameraContext.from_dict({
            "id": camera.get("id", "unknown"),
            "ip": camera.get("ip", "0.0.0.0"),
            "location": camera.get("location", "Unknown"),
            "sceneType": scene_type_val,
            "purpose": purpose_val,
            "vendor": camera.get("manufacturer"),
            "model": camera.get("model"),
        })

    def _parse_capabilities(self, caps: Dict[str, Any]) -> CameraCapabilities:
        """Parse capabilities dict to typed CameraCapabilities"""
        return CameraCapabilities.from_dict(caps)

    def _parse_current_settings(
        self, settings: Dict[str, Any]
    ) -> Optional[CameraCurrentSettings]:
        """Parse current settings dict to typed CameraCurrentSettings"""
        if not settings:
            return None
        return CameraCurrentSettings.from_dict(settings)

    def _parse_optimization_context(
        self, context: Dict[str, Any]
    ) -> OptimizationContext:
        """Parse context dict to typed OptimizationContext"""
        return OptimizationContext(
            bandwidth_limit_mbps=context.get("bandwidthLimitMbps"),
            target_retention_days=context.get("targetRetentionDays"),
            sample_frame=context.get("sampleFrame"),
            notes=context.get("notes"),
            lighting_condition=context.get("lightingCondition"),
            motion_level=context.get("motionLevel"),
        )

    def _to_response(
        self,
        result: OptimizationResult,
        pipeline: PipelineContext,
    ) -> Dict[str, Any]:
        """Convert OptimizationResult to API response dict"""
        response = {
            "recommendedSettings": result.recommended_settings.to_dict(),
            "confidence": result.confidence,
            "warnings": result.warnings,
            "explanation": result.explanation,
            "aiProvider": result.provider,
            "processingTime": result.processing_time_seconds,
            "generatedAt": result.generated_at.isoformat() + "Z",
        }

        # Add pipeline metadata if there were errors
        if pipeline.errors:
            response["pipelineErrors"] = [e.to_dict() for e in pipeline.errors]

        return response


# Global service instance
_optimization_service: Optional[OptimizationService] = None


def get_optimization_service() -> OptimizationService:
    """Get or create optimization service singleton"""
    global _optimization_service
    if _optimization_service is None:
        _optimization_service = OptimizationService()
    return _optimization_service
