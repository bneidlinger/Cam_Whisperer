# backend/services/providers/__init__.py
"""
PlatoniCam Optimization Providers

Provider abstraction layer for different optimization strategies.
"""

from .base import OptimizationProvider, ProviderCapability
from .claude_provider import ClaudeOptimizationProvider
from .gemini_provider import GeminiOptimizationProvider
from .heuristic_provider import HeuristicOptimizationProvider
from .factory import get_provider, get_available_providers, ProviderType

__all__ = [
    # Base
    "OptimizationProvider",
    "ProviderCapability",
    # Implementations
    "ClaudeOptimizationProvider",
    "GeminiOptimizationProvider",
    "HeuristicOptimizationProvider",
    # Factory
    "get_provider",
    "get_available_providers",
    "ProviderType",
]
