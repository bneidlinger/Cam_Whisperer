# backend/services/pipeline_logger.py
"""
Pipeline logging and metrics.

Provides structured logging, timing metrics, and performance tracking
for the optimization pipeline.
"""

import logging
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Generator
from functools import wraps

logger = logging.getLogger("platonicam.pipeline")


@dataclass
class StageMetrics:
    """Metrics for a single pipeline stage"""
    stage: str
    started_at: datetime
    ended_at: Optional[datetime] = None
    duration_ms: Optional[float] = None
    success: bool = True
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def complete(self, success: bool = True, error: Optional[str] = None) -> None:
        """Mark stage as complete"""
        self.ended_at = datetime.utcnow()
        self.duration_ms = (self.ended_at - self.started_at).total_seconds() * 1000
        self.success = success
        self.error = error

    def to_dict(self) -> Dict[str, Any]:
        return {
            "stage": self.stage,
            "startedAt": self.started_at.isoformat() + "Z",
            "endedAt": self.ended_at.isoformat() + "Z" if self.ended_at else None,
            "durationMs": self.duration_ms,
            "success": self.success,
            "error": self.error,
            "metadata": self.metadata,
        }


@dataclass
class PipelineMetrics:
    """Aggregated metrics for an entire pipeline run"""
    request_id: str
    camera_id: str
    started_at: datetime = field(default_factory=datetime.utcnow)
    ended_at: Optional[datetime] = None
    total_duration_ms: Optional[float] = None
    stages: List[StageMetrics] = field(default_factory=list)
    success: bool = True
    provider_used: Optional[str] = None
    fallback_triggered: bool = False

    def add_stage(self, stage: StageMetrics) -> None:
        """Add a stage metrics record"""
        self.stages.append(stage)

    def complete(self, success: bool = True) -> None:
        """Mark pipeline as complete"""
        self.ended_at = datetime.utcnow()
        self.total_duration_ms = (self.ended_at - self.started_at).total_seconds() * 1000
        self.success = success

    def to_dict(self) -> Dict[str, Any]:
        return {
            "requestId": self.request_id,
            "cameraId": self.camera_id,
            "startedAt": self.started_at.isoformat() + "Z",
            "endedAt": self.ended_at.isoformat() + "Z" if self.ended_at else None,
            "totalDurationMs": self.total_duration_ms,
            "stages": [s.to_dict() for s in self.stages],
            "success": self.success,
            "providerUsed": self.provider_used,
            "fallbackTriggered": self.fallback_triggered,
        }

    def summary(self) -> str:
        """Generate human-readable summary"""
        lines = [
            f"Pipeline {self.request_id} for camera {self.camera_id}",
            f"  Status: {'SUCCESS' if self.success else 'FAILED'}",
            f"  Provider: {self.provider_used or 'unknown'}",
            f"  Total time: {self.total_duration_ms:.1f}ms" if self.total_duration_ms else "  Total time: in progress",
        ]

        if self.fallback_triggered:
            lines.append("  Fallback: triggered")

        if self.stages:
            lines.append("  Stages:")
            for stage in self.stages:
                status = "OK" if stage.success else "FAILED"
                duration = f"{stage.duration_ms:.1f}ms" if stage.duration_ms else "..."
                lines.append(f"    - {stage.stage}: {status} ({duration})")

        return "\n".join(lines)


class PipelineLogger:
    """
    Structured logger for pipeline operations.

    Provides contextual logging with request tracking and timing.
    """

    def __init__(self, request_id: str, camera_id: str = "unknown"):
        self.request_id = request_id
        self.camera_id = camera_id
        self.metrics = PipelineMetrics(
            request_id=request_id,
            camera_id=camera_id,
        )
        self._current_stage: Optional[StageMetrics] = None

    def _log(self, level: int, message: str, **kwargs: Any) -> None:
        """Log with request context"""
        extra = {
            "request_id": self.request_id,
            "camera_id": self.camera_id,
            **kwargs,
        }
        logger.log(level, f"[{self.request_id}] {message}", extra=extra)

    def info(self, message: str, **kwargs: Any) -> None:
        """Log info message"""
        self._log(logging.INFO, message, **kwargs)

    def warning(self, message: str, **kwargs: Any) -> None:
        """Log warning message"""
        self._log(logging.WARNING, message, **kwargs)

    def error(self, message: str, **kwargs: Any) -> None:
        """Log error message"""
        self._log(logging.ERROR, message, **kwargs)

    def debug(self, message: str, **kwargs: Any) -> None:
        """Log debug message"""
        self._log(logging.DEBUG, message, **kwargs)

    @contextmanager
    def stage(
        self,
        name: str,
        **metadata: Any,
    ) -> Generator[StageMetrics, None, None]:
        """
        Context manager for timing pipeline stages.

        Usage:
            with logger.stage("discovery") as stage:
                # do work
                stage.metadata["cameras_found"] = 5
        """
        stage_metrics = StageMetrics(
            stage=name,
            started_at=datetime.utcnow(),
            metadata=metadata,
        )
        self._current_stage = stage_metrics
        self.info(f"Stage '{name}' started")

        try:
            yield stage_metrics
            stage_metrics.complete(success=True)
            self.info(
                f"Stage '{name}' completed in {stage_metrics.duration_ms:.1f}ms"
            )
        except Exception as e:
            stage_metrics.complete(success=False, error=str(e))
            self.error(f"Stage '{name}' failed: {e}")
            raise
        finally:
            self.metrics.add_stage(stage_metrics)
            self._current_stage = None

    def set_provider(self, provider: str) -> None:
        """Record the provider being used"""
        self.metrics.provider_used = provider
        self.info(f"Using provider: {provider}")

    def set_fallback(self, triggered: bool = True) -> None:
        """Record if fallback was triggered"""
        self.metrics.fallback_triggered = triggered
        if triggered:
            self.warning("Fallback triggered")

    def complete(self, success: bool = True) -> PipelineMetrics:
        """Complete pipeline and return metrics"""
        self.metrics.complete(success=success)
        self.info(f"Pipeline completed: {'SUCCESS' if success else 'FAILED'}")
        self.debug(self.metrics.summary())
        return self.metrics

    def get_metrics(self) -> PipelineMetrics:
        """Get current metrics"""
        return self.metrics


def timed_stage(stage_name: str):
    """
    Decorator for timing async functions as pipeline stages.

    Usage:
        @timed_stage("discovery")
        async def discover_cameras(self, ...):
            ...
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start = time.perf_counter()
            try:
                result = await func(*args, **kwargs)
                duration_ms = (time.perf_counter() - start) * 1000
                logger.debug(
                    f"Stage '{stage_name}' completed in {duration_ms:.1f}ms"
                )
                return result
            except Exception as e:
                duration_ms = (time.perf_counter() - start) * 1000
                logger.error(
                    f"Stage '{stage_name}' failed after {duration_ms:.1f}ms: {e}"
                )
                raise
        return wrapper
    return decorator


def configure_pipeline_logging(
    level: int = logging.INFO,
    format_string: Optional[str] = None,
) -> None:
    """
    Configure pipeline logging.

    Args:
        level: Logging level
        format_string: Optional custom format string
    """
    if format_string is None:
        format_string = (
            "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
        )

    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(format_string))

    pipeline_logger = logging.getLogger("platonicam.pipeline")
    pipeline_logger.setLevel(level)
    pipeline_logger.addHandler(handler)
    pipeline_logger.propagate = False
