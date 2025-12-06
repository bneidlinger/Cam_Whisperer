# backend/services/optimization.py
"""
Camera optimization service
Handles AI-powered and heuristic camera configuration optimization
"""

import logging
from typing import Dict, Any, List, Tuple
from datetime import datetime

from integrations.claude_client import get_claude_client
from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class OptimizationService:
    """Service for generating optimal camera settings"""

    def __init__(self):
        """Initialize optimization service"""
        self.claude_client = get_claude_client()

    async def optimize(
        self,
        camera: Dict[str, Any],
        capabilities: Dict[str, Any],
        current_settings: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Generate optimal camera settings

        Args:
            camera: Camera metadata (id, location, sceneType, purpose)
            capabilities: Hardware capabilities
            current_settings: Current configuration
            context: Optimization context (bandwidth, retention, sample frame)

        Returns:
            OptimizeResponse dict with recommendations
        """

        camera_id = camera.get("id", "unknown")
        logger.info(f"Starting optimization for camera {camera_id}")

        # Try Claude Vision first
        if settings.fallback_to_heuristic:
            try:
                return await self._optimize_with_claude(
                    camera, capabilities, current_settings, context
                )
            except Exception as e:
                logger.warning(
                    f"Claude optimization failed: {e}. Falling back to heuristic."
                )
                return self._optimize_with_heuristic(
                    camera, capabilities, current_settings, context
                )
        else:
            # No fallback - fail if Claude fails
            return await self._optimize_with_claude(
                camera, capabilities, current_settings, context
            )

    async def _optimize_with_claude(
        self,
        camera: Dict[str, Any],
        capabilities: Dict[str, Any],
        current_settings: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Optimize using Claude Vision AI"""

        start_time = datetime.utcnow()

        try:
            # Call Claude API
            recommended_settings, confidence, explanation = (
                self.claude_client.optimize_camera_settings(
                    camera_context=camera,
                    current_settings=current_settings,
                    capabilities=capabilities,
                    constraints={
                        "bandwidthLimitMbps": context.get("bandwidthLimitMbps"),
                        "targetRetentionDays": context.get("targetRetentionDays"),
                    },
                    sample_frame=context.get("sampleFrame"),
                )
            )

            # Generate warnings
            warnings = self._generate_warnings(
                recommended_settings, capabilities, context
            )

            processing_time = (datetime.utcnow() - start_time).total_seconds()

            return {
                "recommendedSettings": recommended_settings,
                "confidence": confidence,
                "warnings": warnings,
                "explanation": explanation,
                "aiProvider": "claude-sonnet-4-5",
                "processingTime": processing_time,
                "generatedAt": datetime.utcnow().isoformat() + "Z",
            }

        except Exception as e:
            logger.error(f"Claude optimization error: {e}", exc_info=True)
            raise

    def _optimize_with_heuristic(
        self,
        camera: Dict[str, Any],
        capabilities: Dict[str, Any],
        current_settings: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Fallback heuristic optimization (same as original main.py logic)"""

        start_time = datetime.utcnow()

        # Copy current settings as baseline
        rec = current_settings.copy()

        # Apply simple heuristic rules based on purpose
        purpose = camera.get("purpose", "overview")
        scene_type = camera.get("sceneType", "interior")

        if purpose == "plates":
            # License plate recognition needs fast shutter, high FPS
            if "stream" not in rec:
                rec["stream"] = {}
            rec["stream"]["fps"] = max(rec.get("stream", {}).get("fps", 15), 20)

            if "exposure" not in rec:
                rec["exposure"] = {}
            rec["exposure"]["shutter"] = "1/250 to 1/500"

            if "lowLight" not in rec:
                rec["lowLight"] = {}
            rec["lowLight"]["slowShutter"] = "Off"

        elif purpose == "facial":
            # Face recognition needs good detail, fast shutter
            if "stream" not in rec:
                rec["stream"] = {}
            rec["stream"]["fps"] = max(rec.get("stream", {}).get("fps", 15), 20)

            if "exposure" not in rec:
                rec["exposure"] = {}
            rec["exposure"]["shutter"] = "1/250"

        # Scene type adjustments
        if scene_type == "entrance":
            if "exposure" not in rec:
                rec["exposure"] = {}
            rec["exposure"]["wdr"] = "High"

        warnings = []
        explanation = (
            "Heuristic-based optimization applied. "
            f"Settings adjusted for {purpose} purpose and {scene_type} scene type. "
            "For best results, use AI optimization with a sample frame."
        )

        processing_time = (datetime.utcnow() - start_time).total_seconds()

        return {
            "recommendedSettings": rec,
            "confidence": 0.5,
            "warnings": warnings,
            "explanation": explanation,
            "aiProvider": "heuristic",
            "processingTime": processing_time,
            "generatedAt": datetime.utcnow().isoformat() + "Z",
        }

    def _generate_warnings(
        self,
        settings: Dict[str, Any],
        capabilities: Dict[str, Any],
        context: Dict[str, Any],
    ) -> List[str]:
        """Generate warnings for constraint violations"""

        warnings = []

        # Check bandwidth
        bandwidth_limit = context.get("bandwidthLimitMbps")
        recommended_bitrate = settings.get("stream", {}).get("bitrateMbps")

        if bandwidth_limit and recommended_bitrate:
            if recommended_bitrate > bandwidth_limit:
                warnings.append(
                    f"Recommended bitrate ({recommended_bitrate} Mbps) exceeds "
                    f"bandwidth limit ({bandwidth_limit} Mbps). "
                    "Consider reducing resolution or FPS."
                )

        # Check FPS capability
        max_fps = capabilities.get("maxFps", 30)
        recommended_fps = settings.get("stream", {}).get("fps", 0)

        if recommended_fps > max_fps:
            warnings.append(
                f"Recommended FPS ({recommended_fps}) exceeds camera maximum ({max_fps})"
            )

        # Check codec support
        recommended_codec = settings.get("stream", {}).get("codec")
        supported_codecs = capabilities.get("supportedCodecs", [])

        if recommended_codec and recommended_codec not in supported_codecs:
            warnings.append(
                f"Recommended codec ({recommended_codec}) may not be supported. "
                f"Camera supports: {', '.join(supported_codecs)}"
            )

        return warnings


# Global service instance
_optimization_service: Any = None


def get_optimization_service() -> OptimizationService:
    """Get or create optimization service singleton"""
    global _optimization_service
    if _optimization_service is None:
        _optimization_service = OptimizationService()
    return _optimization_service
