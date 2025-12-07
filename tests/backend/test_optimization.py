"""
Tests for the optimization service.
"""

import pytest
from unittest.mock import patch, MagicMock


class TestOptimizationService:
    """Tests for OptimizationService class."""

    def test_heuristic_fallback_plates(self, sample_camera, sample_capabilities, sample_context):
        """Test heuristic optimization for license plate recognition."""
        from services.optimization import OptimizationService

        service = OptimizationService()
        sample_camera["purpose"] = "plates"

        result = service._optimize_with_heuristic(
            sample_camera,
            sample_capabilities,
            {"stream": {"fps": 15}},
            sample_context
        )

        assert result["aiProvider"] == "heuristic"
        assert result["confidence"] == 0.5
        assert result["recommendedSettings"]["stream"]["fps"] >= 20
        assert "shutter" in result["recommendedSettings"]["exposure"]

    def test_heuristic_fallback_facial(self, sample_camera, sample_capabilities, sample_context):
        """Test heuristic optimization for facial recognition."""
        from services.optimization import OptimizationService

        service = OptimizationService()
        sample_camera["purpose"] = "facial"

        result = service._optimize_with_heuristic(
            sample_camera,
            sample_capabilities,
            {"stream": {"fps": 15}},
            sample_context
        )

        assert result["aiProvider"] == "heuristic"
        assert result["recommendedSettings"]["stream"]["fps"] >= 20

    def test_heuristic_entrance_scene(self, sample_camera, sample_capabilities, sample_context):
        """Test heuristic optimization for entrance scene type."""
        from services.optimization import OptimizationService

        service = OptimizationService()
        sample_camera["sceneType"] = "entrance"
        sample_camera["purpose"] = "overview"

        result = service._optimize_with_heuristic(
            sample_camera,
            sample_capabilities,
            {},
            sample_context
        )

        assert result["recommendedSettings"]["exposure"]["wdr"] == "High"

    def test_generate_warnings_bandwidth_exceeded(self, sample_capabilities):
        """Test warning generation when bandwidth is exceeded."""
        from services.optimization import OptimizationService

        service = OptimizationService()

        settings = {
            "stream": {"bitrateMbps": 10}
        }
        context = {"bandwidthLimitMbps": 8}

        warnings = service._generate_warnings(settings, sample_capabilities, context)

        assert len(warnings) > 0
        assert "bandwidth" in warnings[0].lower() or "bitrate" in warnings[0].lower()

    def test_generate_warnings_fps_exceeded(self, sample_capabilities):
        """Test warning generation when FPS exceeds camera max."""
        from services.optimization import OptimizationService

        service = OptimizationService()

        settings = {
            "stream": {"fps": 60}  # Exceeds maxFps of 30
        }
        context = {}

        warnings = service._generate_warnings(settings, sample_capabilities, context)

        assert len(warnings) > 0
        assert "fps" in warnings[0].lower()

    def test_generate_warnings_unsupported_codec(self):
        """Test warning generation for unsupported codec."""
        from services.optimization import OptimizationService

        service = OptimizationService()

        settings = {
            "stream": {"codec": "H.266"}
        }
        capabilities = {"supportedCodecs": ["H.264", "H.265"]}
        context = {}

        warnings = service._generate_warnings(settings, capabilities, context)

        assert len(warnings) > 0
        assert "codec" in warnings[0].lower()


class TestOptimizationResponse:
    """Tests for optimization response format."""

    def test_response_has_required_fields(self, sample_camera, sample_capabilities, sample_context):
        """Test that optimization response has all required fields."""
        from services.optimization import OptimizationService

        service = OptimizationService()

        result = service._optimize_with_heuristic(
            sample_camera,
            sample_capabilities,
            {},
            sample_context
        )

        assert "recommendedSettings" in result
        assert "confidence" in result
        assert "warnings" in result
        assert "explanation" in result
        assert "aiProvider" in result
        assert "processingTime" in result
        assert "generatedAt" in result

    def test_confidence_range(self, sample_camera, sample_capabilities, sample_context):
        """Test that confidence is within valid range."""
        from services.optimization import OptimizationService

        service = OptimizationService()

        result = service._optimize_with_heuristic(
            sample_camera,
            sample_capabilities,
            {},
            sample_context
        )

        assert 0.0 <= result["confidence"] <= 1.0
