# backend/errors.py
"""
PlatoniCam Exception Hierarchy

Custom exceptions for the optimization pipeline with recovery hints.
"""

from typing import Any, Dict, Optional


class PlatoniCamError(Exception):
    """Base exception for all PlatoniCam errors"""

    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        recoverable: bool = True,
        recovery_hint: Optional[str] = None
    ):
        super().__init__(message)
        self.message = message
        self.details = details or {}
        self.recoverable = recoverable
        self.recovery_hint = recovery_hint

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "error": self.__class__.__name__,
            "message": self.message,
            "recoverable": self.recoverable,
        }
        if self.details:
            result["details"] = self.details
        if self.recovery_hint:
            result["recoveryHint"] = self.recovery_hint
        return result


# =============================================================================
# PIPELINE ERRORS
# =============================================================================

class PipelineError(PlatoniCamError):
    """Base exception for pipeline errors"""

    def __init__(
        self,
        message: str,
        stage: str,
        details: Optional[Dict[str, Any]] = None,
        recoverable: bool = True,
        recovery_hint: Optional[str] = None
    ):
        super().__init__(message, details, recoverable, recovery_hint)
        self.stage = stage

    def to_dict(self) -> Dict[str, Any]:
        result = super().to_dict()
        result["stage"] = self.stage
        return result


# =============================================================================
# DISCOVERY ERRORS
# =============================================================================

class DiscoveryError(PipelineError):
    """Camera discovery failed"""

    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        recovery_hint: str = "Try manual camera registration or check network connectivity"
    ):
        super().__init__(
            message=message,
            stage="discovery",
            details=details,
            recoverable=True,
            recovery_hint=recovery_hint
        )


class NetworkScanError(DiscoveryError):
    """Network scan failed"""

    def __init__(self, message: str = "Network scan failed", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            details=details,
            recovery_hint="Check network permissions and firewall settings"
        )


class VmsConnectionError(DiscoveryError):
    """Failed to connect to VMS"""

    def __init__(
        self,
        vms_type: str,
        message: str = "Failed to connect to VMS",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=f"{message}: {vms_type}",
            details={"vmsType": vms_type, **(details or {})},
            recovery_hint=f"Verify {vms_type} server is running and credentials are correct"
        )


# =============================================================================
# CAPABILITY ERRORS
# =============================================================================

class CapabilityQueryError(PipelineError):
    """Failed to query camera capabilities"""

    def __init__(
        self,
        message: str,
        camera_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        recovery_hint: str = "Using default capabilities; results may not be optimal"
    ):
        super().__init__(
            message=message,
            stage="capabilities",
            details={"cameraId": camera_id, **(details or {})} if camera_id else details,
            recoverable=True,
            recovery_hint=recovery_hint
        )


class UnsupportedProtocolError(CapabilityQueryError):
    """Camera protocol not supported"""

    def __init__(self, protocol: str, camera_id: Optional[str] = None):
        super().__init__(
            message=f"Protocol not supported: {protocol}",
            camera_id=camera_id,
            details={"protocol": protocol},
            recovery_hint="Use manual capability entry or check camera documentation"
        )


# =============================================================================
# OPTIMIZATION ERRORS
# =============================================================================

class OptimizationError(PipelineError):
    """Optimization generation failed"""

    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        recoverable: bool = True,
        recovery_hint: str = "Falling back to heuristic optimization"
    ):
        super().__init__(
            message=message,
            stage="optimization",
            details=details,
            recoverable=recoverable,
            recovery_hint=recovery_hint
        )


class ProviderError(OptimizationError):
    """AI provider error (Claude API, etc.)"""

    def __init__(
        self,
        provider: str,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        status_code: Optional[int] = None
    ):
        super().__init__(
            message=f"{provider} error: {message}",
            details={"provider": provider, "statusCode": status_code, **(details or {})},
            recoverable=True,
            recovery_hint="Using heuristic fallback; consider checking API key and quota"
        )


class ProviderRateLimitError(ProviderError):
    """AI provider rate limit exceeded"""

    def __init__(self, provider: str, retry_after: Optional[int] = None):
        super().__init__(
            provider=provider,
            message="Rate limit exceeded",
            details={"retryAfter": retry_after},
            status_code=429
        )
        self.retry_after = retry_after
        self.recovery_hint = f"Rate limited; retry after {retry_after}s" if retry_after else "Rate limited; try again later"


class ProviderAuthError(ProviderError):
    """AI provider authentication failed"""

    def __init__(self, provider: str):
        super().__init__(
            provider=provider,
            message="Authentication failed",
            status_code=401
        )
        self.recoverable = False
        self.recovery_hint = "Check API key configuration in .env file"


class InvalidResponseError(OptimizationError):
    """AI provider returned invalid response"""

    def __init__(self, message: str = "Invalid response from AI provider", raw_response: Optional[str] = None):
        super().__init__(
            message=message,
            details={"rawResponse": raw_response[:500] if raw_response else None},
            recovery_hint="AI response could not be parsed; using heuristic fallback"
        )


class ConstraintViolationError(OptimizationError):
    """Optimization violates constraints"""

    def __init__(self, violations: list):
        super().__init__(
            message="Optimization violates constraints",
            details={"violations": violations},
            recoverable=True,
            recovery_hint="Review constraints or accept warnings"
        )
        self.violations = violations


# =============================================================================
# APPLY ERRORS
# =============================================================================

class ApplyError(PipelineError):
    """Failed to apply settings"""

    def __init__(
        self,
        message: str,
        camera_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        recoverable: bool = True,
        recovery_hint: str = "Check camera connectivity and credentials"
    ):
        super().__init__(
            message=message,
            stage="apply",
            details={"cameraId": camera_id, **(details or {})} if camera_id else details,
            recoverable=recoverable,
            recovery_hint=recovery_hint
        )


class PartialApplyError(ApplyError):
    """Some settings applied, some failed"""

    def __init__(
        self,
        camera_id: str,
        applied: list,
        failed: list,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message="Partial apply: some settings failed",
            camera_id=camera_id,
            details={"applied": applied, "failed": failed, **(details or {})},
            recoverable=True,
            recovery_hint="Some settings were applied; review failed settings and retry"
        )
        self.applied = applied
        self.failed = failed


class ApplyTimeoutError(ApplyError):
    """Apply operation timed out"""

    def __init__(self, camera_id: str, timeout_seconds: int):
        super().__init__(
            message=f"Apply timed out after {timeout_seconds}s",
            camera_id=camera_id,
            details={"timeoutSeconds": timeout_seconds},
            recovery_hint="Camera may be slow to respond; increase timeout or retry"
        )


class ApplyRollbackError(ApplyError):
    """Failed to rollback settings after apply failure"""

    def __init__(self, camera_id: str, original_error: str):
        super().__init__(
            message="Failed to rollback settings",
            camera_id=camera_id,
            details={"originalError": original_error},
            recoverable=False,
            recovery_hint="Manual intervention required; camera may be in inconsistent state"
        )


# =============================================================================
# VERIFICATION ERRORS
# =============================================================================

class VerificationError(PipelineError):
    """Settings verification failed"""

    def __init__(
        self,
        message: str,
        camera_id: Optional[str] = None,
        mismatches: Optional[list] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            stage="verification",
            details={"cameraId": camera_id, "mismatches": mismatches, **(details or {})},
            recoverable=True,
            recovery_hint="Settings may not have applied correctly; review and retry"
        )
        self.mismatches = mismatches or []


# =============================================================================
# AUTHENTICATION ERRORS
# =============================================================================

class AuthenticationError(PlatoniCamError):
    """Authentication failed"""

    def __init__(
        self,
        message: str = "Authentication failed",
        target: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            details={"target": target, **(details or {})} if target else details,
            recoverable=True,
            recovery_hint="Check username and password"
        )


class CameraAuthError(AuthenticationError):
    """Camera authentication failed"""

    def __init__(self, camera_id: str, ip: Optional[str] = None):
        super().__init__(
            message=f"Camera authentication failed: {camera_id}",
            target=f"camera:{camera_id}",
            details={"cameraId": camera_id, "ip": ip}
        )
        self.recovery_hint = "Verify camera credentials (default: admin/admin)"


class VmsAuthError(AuthenticationError):
    """VMS authentication failed"""

    def __init__(self, vms_type: str, host: Optional[str] = None):
        super().__init__(
            message=f"VMS authentication failed: {vms_type}",
            target=f"vms:{vms_type}",
            details={"vmsType": vms_type, "host": host}
        )


# =============================================================================
# TIMEOUT ERRORS
# =============================================================================

class TimeoutError(PlatoniCamError):
    """Operation timed out"""

    def __init__(
        self,
        operation: str,
        timeout_seconds: int,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=f"Operation timed out: {operation} ({timeout_seconds}s)",
            details={"operation": operation, "timeoutSeconds": timeout_seconds, **(details or {})},
            recoverable=True,
            recovery_hint="Increase timeout or check network connectivity"
        )


# =============================================================================
# VALIDATION ERRORS
# =============================================================================

class ValidationError(PlatoniCamError):
    """Input validation failed"""

    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        value: Optional[Any] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            details={"field": field, "value": value, **(details or {})},
            recoverable=True,
            recovery_hint="Check input values and try again"
        )


class InvalidImageError(ValidationError):
    """Invalid image data"""

    def __init__(self, reason: str):
        super().__init__(
            message=f"Invalid image: {reason}",
            field="sampleFrame",
            details={"reason": reason}
        )
        self.recovery_hint = "Ensure image is JPEG/PNG and under size limit"


# =============================================================================
# CONFIGURATION ERRORS
# =============================================================================

class ConfigurationError(PlatoniCamError):
    """Configuration error"""

    def __init__(
        self,
        message: str,
        setting: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            details={"setting": setting, **(details or {})},
            recoverable=False,
            recovery_hint="Check .env configuration file"
        )


class MissingApiKeyError(ConfigurationError):
    """API key not configured"""

    def __init__(self, service: str):
        super().__init__(
            message=f"API key not configured for {service}",
            setting=f"{service.upper()}_API_KEY"
        )
        self.recovery_hint = f"Add {service.upper()}_API_KEY to .env file"
