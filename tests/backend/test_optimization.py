"""
Tests for the optimization service and heuristic provider.
"""

import pytest
from datetime import datetime


class TestHeuristicProvider:
    """Tests for HeuristicOptimizationProvider class."""

    @pytest.fixture
    def provider(self):
        """Create heuristic provider instance."""
        from services.providers.heuristic_provider import HeuristicOptimizationProvider
        return HeuristicOptimizationProvider()

    @pytest.fixture
    def camera_context_plates(self):
        """Camera context for LPR/plates purpose."""
        from models.pipeline import CameraContext, SceneType, CameraPurpose
        return CameraContext(
            id="CAM-001",
            ip="192.168.1.100",
            location="Parking Entrance",
            scene_type=SceneType.PARKING,
            purpose=CameraPurpose.PLATES,
            vendor="Test",
            model="TestCam-1000"
        )

    @pytest.fixture
    def camera_context_facial(self):
        """Camera context for facial recognition purpose."""
        from models.pipeline import CameraContext, SceneType, CameraPurpose
        return CameraContext(
            id="CAM-002",
            ip="192.168.1.101",
            location="Main Entrance",
            scene_type=SceneType.ENTRANCE,
            purpose=CameraPurpose.FACIAL,
            vendor="Test",
            model="TestCam-2000"
        )

    @pytest.fixture
    def camera_context_overview(self):
        """Camera context for overview purpose."""
        from models.pipeline import CameraContext, SceneType, CameraPurpose
        return CameraContext(
            id="CAM-003",
            ip="192.168.1.102",
            location="Lobby",
            scene_type=SceneType.ENTRANCE,
            purpose=CameraPurpose.OVERVIEW,
            vendor="Test",
            model="TestCam-3000"
        )

    @pytest.fixture
    def capabilities(self):
        """Sample camera capabilities."""
        from models.pipeline import CameraCapabilities
        return CameraCapabilities(
            camera_id="CAM-001",
            supported_codecs=["H.264", "H.265"],
            supported_resolutions=["1920x1080", "2560x1440", "3840x2160"],
            max_fps=30,
            has_wdr=True,
            has_ir=True,
            has_hlc=True,
        )

    @pytest.fixture
    def optimization_context(self):
        """Sample optimization context."""
        from models.pipeline import OptimizationContext
        return OptimizationContext(
            bandwidth_limit_mbps=8.0,
            target_retention_days=30,
            sample_frame=None
        )

    @pytest.mark.asyncio
    async def test_heuristic_plates_shutter_speed(self, provider, camera_context_plates, capabilities, optimization_context):
        """Test that LPR optimization enforces fast shutter speed."""
        result = await provider.optimize(
            camera=camera_context_plates,
            capabilities=capabilities,
            current_settings=None,
            context=optimization_context,
        )

        assert result.provider == "heuristic"
        assert result.recommended_settings.exposure.shutter == "1/500"
        assert result.recommended_settings.exposure.mode == "Shutter Priority"
        assert result.recommended_settings.stream.fps >= 25

    @pytest.mark.asyncio
    async def test_heuristic_plates_wdr_disabled(self, provider, camera_context_plates, capabilities, optimization_context):
        """Test that LPR optimization disables WDR to prevent ghosting."""
        result = await provider.optimize(
            camera=camera_context_plates,
            capabilities=capabilities,
            current_settings=None,
            context=optimization_context,
        )

        # WDR should be Off for LPR (prevents ghosting on moving plates)
        assert result.recommended_settings.exposure.wdr == "Off"
        # HLC should be On (masks headlight glare)
        assert result.recommended_settings.exposure.hlc == "On"

    @pytest.mark.asyncio
    async def test_heuristic_plates_purpose_overrides_scene(self, provider, camera_context_plates, capabilities, optimization_context):
        """Test that purpose rules override scene rules for LPR."""
        # Camera is in PARKING scene which normally sets WDR="Medium"
        # But PLATES purpose should override to WDR="Off"
        result = await provider.optimize(
            camera=camera_context_plates,
            capabilities=capabilities,
            current_settings=None,
            context=optimization_context,
        )

        # Purpose (PLATES) should take precedence over scene (PARKING)
        assert result.recommended_settings.exposure.wdr == "Off"

    @pytest.mark.asyncio
    async def test_heuristic_plates_warnings(self, provider, camera_context_plates, capabilities, optimization_context):
        """Test that LPR optimization includes installation warnings."""
        result = await provider.optimize(
            camera=camera_context_plates,
            capabilities=capabilities,
            current_settings=None,
            context=optimization_context,
        )

        # Should include LPR-specific warnings about physical installation
        assert len(result.warnings) > 0
        warning_text = " ".join(result.warnings).lower()
        assert "angle" in warning_text or "installation" in warning_text or "tilt" in warning_text

    @pytest.mark.asyncio
    async def test_heuristic_facial_shutter_priority(self, provider, camera_context_facial, capabilities, optimization_context):
        """Test that facial recognition uses shutter priority mode."""
        result = await provider.optimize(
            camera=camera_context_facial,
            capabilities=capabilities,
            current_settings=None,
            context=optimization_context,
        )

        assert result.recommended_settings.exposure.mode == "Shutter Priority"
        assert result.recommended_settings.exposure.shutter == "1/250"
        assert result.recommended_settings.stream.fps >= 20

    @pytest.mark.asyncio
    async def test_heuristic_entrance_scene_wdr(self, provider, camera_context_overview, capabilities, optimization_context):
        """Test that entrance scene type enables high WDR."""
        result = await provider.optimize(
            camera=camera_context_overview,
            capabilities=capabilities,
            current_settings=None,
            context=optimization_context,
        )

        # Entrance scene should have High WDR (overview purpose doesn't override it)
        assert result.recommended_settings.exposure.wdr == "High"

    @pytest.mark.asyncio
    async def test_heuristic_confidence(self, provider, camera_context_overview, capabilities, optimization_context):
        """Test that heuristic provider returns moderate confidence."""
        result = await provider.optimize(
            camera=camera_context_overview,
            capabilities=capabilities,
            current_settings=None,
            context=optimization_context,
        )

        # Heuristic should have moderate confidence (0.6)
        assert result.confidence == 0.6

    @pytest.mark.asyncio
    async def test_heuristic_no_sample_frame_warning(self, provider, camera_context_overview, capabilities, optimization_context):
        """Test that missing sample frame generates a warning."""
        result = await provider.optimize(
            camera=camera_context_overview,
            capabilities=capabilities,
            current_settings=None,
            context=optimization_context,
        )

        warning_text = " ".join(result.warnings).lower()
        assert "sample" in warning_text or "frame" in warning_text or "heuristic" in warning_text


class TestCodecWarnings:
    """Tests for codec-related warnings."""

    @pytest.fixture
    def provider(self):
        """Create heuristic provider instance."""
        from services.providers.heuristic_provider import HeuristicOptimizationProvider
        return HeuristicOptimizationProvider()

    @pytest.fixture
    def camera_context(self):
        """Camera context for testing."""
        from models.pipeline import CameraContext, SceneType, CameraPurpose
        return CameraContext(
            id="CAM-001",
            ip="192.168.1.100",
            location="Test Location",
            scene_type=SceneType.GENERIC,
            purpose=CameraPurpose.GENERAL,
        )

    @pytest.fixture
    def capabilities_with_h266(self):
        """Capabilities with H.266 support."""
        from models.pipeline import CameraCapabilities
        return CameraCapabilities(
            camera_id="CAM-001",
            supported_codecs=["H.264", "H.265", "H.266"],
            max_fps=30,
        )

    @pytest.fixture
    def context_bandwidth_limited(self):
        """Context with low bandwidth limit."""
        from models.pipeline import OptimizationContext
        return OptimizationContext(
            bandwidth_limit_mbps=2.0,
        )

    @pytest.mark.asyncio
    async def test_h264_low_bandwidth_warning(self, provider, camera_context, capabilities_with_h266, context_bandwidth_limited):
        """Test that H.264 with low bandwidth suggests H.265."""
        from models.pipeline import CameraCurrentSettings, StreamSettings

        current = CameraCurrentSettings(
            camera_id="CAM-001",
            stream=StreamSettings(codec="H.264", fps=15),
        )

        result = await provider.optimize(
            camera=camera_context,
            capabilities=capabilities_with_h266,
            current_settings=current,
            context=context_bandwidth_limited,
        )

        # Should warn about H.265 being more efficient
        warning_text = " ".join(result.warnings).lower()
        assert "h.265" in warning_text or "compression" in warning_text


class TestOptimizationResponse:
    """Tests for optimization response format."""

    @pytest.fixture
    def provider(self):
        """Create heuristic provider instance."""
        from services.providers.heuristic_provider import HeuristicOptimizationProvider
        return HeuristicOptimizationProvider()

    @pytest.fixture
    def camera_context(self):
        """Camera context for testing."""
        from models.pipeline import CameraContext, SceneType, CameraPurpose
        return CameraContext(
            id="CAM-001",
            ip="192.168.1.100",
            location="Test Location",
            scene_type=SceneType.GENERIC,
            purpose=CameraPurpose.GENERAL,
        )

    @pytest.fixture
    def capabilities(self):
        """Sample camera capabilities."""
        from models.pipeline import CameraCapabilities
        return CameraCapabilities(camera_id="CAM-001")

    @pytest.fixture
    def optimization_context(self):
        """Sample optimization context."""
        from models.pipeline import OptimizationContext
        return OptimizationContext()

    @pytest.mark.asyncio
    async def test_response_has_required_fields(self, provider, camera_context, capabilities, optimization_context):
        """Test that optimization response has all required fields."""
        result = await provider.optimize(
            camera=camera_context,
            capabilities=capabilities,
            current_settings=None,
            context=optimization_context,
        )

        # Check result structure
        assert result.camera_id == "CAM-001"
        assert result.recommended_settings is not None
        assert result.recommended_settings.stream is not None
        assert result.recommended_settings.exposure is not None
        assert result.recommended_settings.low_light is not None
        assert result.recommended_settings.image is not None
        assert result.confidence is not None
        assert result.explanation is not None
        assert result.provider == "heuristic"
        assert result.processing_time_seconds >= 0

    @pytest.mark.asyncio
    async def test_confidence_range(self, provider, camera_context, capabilities, optimization_context):
        """Test that confidence is within valid range."""
        result = await provider.optimize(
            camera=camera_context,
            capabilities=capabilities,
            current_settings=None,
            context=optimization_context,
        )

        assert 0.0 <= result.confidence <= 1.0

    @pytest.mark.asyncio
    async def test_to_dict_serialization(self, provider, camera_context, capabilities, optimization_context):
        """Test that result can be serialized to dict."""
        result = await provider.optimize(
            camera=camera_context,
            capabilities=capabilities,
            current_settings=None,
            context=optimization_context,
        )

        result_dict = result.to_dict()

        assert "cameraId" in result_dict
        assert "recommendedSettings" in result_dict
        assert "confidence" in result_dict
        assert "warnings" in result_dict
        assert "explanation" in result_dict
        assert "aiProvider" in result_dict
        assert "processingTime" in result_dict
        assert "generatedAt" in result_dict
