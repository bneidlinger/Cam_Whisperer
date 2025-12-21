# backend/services/providers/factory.py
"""
Provider factory for creating and managing optimization providers.
"""

import logging
from enum import Enum
from typing import Optional, List, Dict

from .base import OptimizationProvider, ProviderInfo
from .claude_provider import ClaudeOptimizationProvider
from .gemini_provider import GeminiOptimizationProvider
from .heuristic_provider import HeuristicOptimizationProvider

logger = logging.getLogger(__name__)


class ProviderType(str, Enum):
    """Available provider types"""
    CLAUDE = "claude"
    GEMINI = "gemini"
    HEURISTIC = "heuristic"


# Provider registry
_providers: Dict[ProviderType, OptimizationProvider] = {}


def _get_or_create_provider(provider_type: ProviderType) -> OptimizationProvider:
    """Get or create a provider instance (singleton pattern)"""
    if provider_type not in _providers:
        if provider_type == ProviderType.CLAUDE:
            _providers[provider_type] = ClaudeOptimizationProvider()
        elif provider_type == ProviderType.GEMINI:
            _providers[provider_type] = GeminiOptimizationProvider()
        elif provider_type == ProviderType.HEURISTIC:
            _providers[provider_type] = HeuristicOptimizationProvider()
        else:
            raise ValueError(f"Unknown provider type: {provider_type}")

    return _providers[provider_type]


def get_provider(
    provider_type: Optional[ProviderType] = None,
    fallback: bool = True,
) -> OptimizationProvider:
    """
    Get an optimization provider.

    Args:
        provider_type: Specific provider to use. If None, uses best available.
        fallback: If True and requested provider unavailable, fall back to heuristic.

    Returns:
        OptimizationProvider instance

    Raises:
        ValueError: If requested provider unavailable and fallback disabled
    """
    # If no specific provider requested, try Claude first, then Gemini, then heuristic
    if provider_type is None:
        claude = _get_or_create_provider(ProviderType.CLAUDE)
        if claude.is_available():
            logger.debug("Using Claude provider (auto-selected)")
            return claude

        gemini = _get_or_create_provider(ProviderType.GEMINI)
        if gemini.is_available():
            logger.debug("Using Gemini provider (auto-selected)")
            return gemini

        if fallback:
            logger.info("No AI provider available, falling back to heuristic provider")
            return _get_or_create_provider(ProviderType.HEURISTIC)
        else:
            raise ValueError("No AI provider available and fallback disabled")

    # Specific provider requested
    provider = _get_or_create_provider(provider_type)

    if not provider.is_available():
        if fallback and provider_type != ProviderType.HEURISTIC:
            logger.warning(
                f"{provider_type.value} provider unavailable, falling back to heuristic"
            )
            return _get_or_create_provider(ProviderType.HEURISTIC)
        else:
            raise ValueError(f"Provider {provider_type.value} is not available")

    return provider


def get_available_providers() -> List[ProviderInfo]:
    """
    Get list of all available providers with their capabilities.

    Returns:
        List of ProviderInfo for available providers
    """
    available = []

    for provider_type in ProviderType:
        try:
            provider = _get_or_create_provider(provider_type)
            if provider.is_available():
                available.append(provider.info)
        except Exception as e:
            logger.debug(f"Provider {provider_type.value} not available: {e}")

    return available


async def check_all_providers() -> Dict[str, dict]:
    """
    Perform health check on all providers.

    Returns:
        Dict mapping provider name to health status
    """
    results = {}

    for provider_type in ProviderType:
        try:
            provider = _get_or_create_provider(provider_type)
            results[provider_type.value] = await provider.health_check()
        except Exception as e:
            results[provider_type.value] = {
                "provider": provider_type.value,
                "available": False,
                "status": "error",
                "error": str(e),
            }

    return results
