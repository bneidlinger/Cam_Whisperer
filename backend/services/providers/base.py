# backend/services/providers/base.py
"""
Abstract base class for optimization providers.

All optimization strategies (Claude AI, heuristic, future providers)
must implement this interface.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List

from models import (
    CameraContext,
    CameraCapabilities,
    CameraCurrentSettings,
    OptimizationContext,
    OptimizationResult,
)
from models.pipeline import PipelineContext


class ProviderCapability(str, Enum):
    """Capabilities that providers can support"""
    SCENE_ANALYSIS = "scene_analysis"       # Can analyze sample frames
    MULTI_CAMERA = "multi_camera"           # Can optimize multiple cameras together
    CONSTRAINT_SOLVING = "constraint_solving"  # Advanced constraint optimization
    LEARNING = "learning"                    # Can learn from feedback
    OFFLINE = "offline"                      # Works without network


@dataclass
class ProviderInfo:
    """Provider metadata and capabilities"""
    name: str
    version: str
    capabilities: List[ProviderCapability] = field(default_factory=list)
    requires_api_key: bool = False
    supports_fallback: bool = True
    description: str = ""

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "version": self.version,
            "capabilities": [c.value for c in self.capabilities],
            "requiresApiKey": self.requires_api_key,
            "supportsFallback": self.supports_fallback,
            "description": self.description,
        }


class OptimizationProvider(ABC):
    """
    Abstract base class for optimization providers.

    Providers generate optimal camera settings based on scene analysis,
    camera capabilities, and operational constraints.
    """

    @property
    @abstractmethod
    def info(self) -> ProviderInfo:
        """Return provider metadata and capabilities"""
        pass

    @property
    def name(self) -> str:
        """Provider name for identification"""
        return self.info.name

    @abstractmethod
    async def optimize(
        self,
        camera: CameraContext,
        capabilities: CameraCapabilities,
        current_settings: Optional[CameraCurrentSettings],
        context: OptimizationContext,
        pipeline: Optional[PipelineContext] = None,
    ) -> OptimizationResult:
        """
        Generate optimal camera settings.

        Args:
            camera: Camera metadata and context (scene type, purpose, location)
            capabilities: Hardware capabilities and constraints
            current_settings: Current camera configuration (optional)
            context: Optimization parameters (bandwidth, retention, sample frame)
            pipeline: Pipeline context for tracking/logging (optional)

        Returns:
            OptimizationResult with recommended settings, confidence, and explanation

        Raises:
            ProviderError: If optimization fails and cannot recover
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """
        Check if provider is currently available.

        Returns:
            True if provider can accept optimization requests
        """
        pass

    def supports_capability(self, capability: ProviderCapability) -> bool:
        """Check if provider supports a specific capability"""
        return capability in self.info.capabilities

    async def health_check(self) -> dict:
        """
        Perform health check on provider.

        Returns:
            Dict with status and details
        """
        try:
            available = self.is_available()
            return {
                "provider": self.name,
                "available": available,
                "status": "healthy" if available else "unavailable",
            }
        except Exception as e:
            return {
                "provider": self.name,
                "available": False,
                "status": "error",
                "error": str(e),
            }
