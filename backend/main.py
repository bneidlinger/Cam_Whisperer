# backend/main.py

# Suppress ResourceWarning from wsdiscovery library (unclosed sockets in daemon threads)
# Must be done before any other imports, using simplefilter for thread safety
import warnings
import sys

# Aggressively suppress ResourceWarnings (wsdiscovery has socket cleanup issues in threads)
if not sys.warnoptions:
    warnings.simplefilter("ignore", ResourceWarning)
else:
    warnings.filterwarnings("ignore", category=ResourceWarning)

from fastapi import FastAPI, UploadFile, File, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, field_validator
from typing import Optional, List
import datetime
import logging
import traceback

from config import get_settings
from database import init_db
from services.optimization import get_optimization_service
from services.discovery import DiscoveryService
from services.apply import ApplyService, ApplyMethod
from services.datasheet_service import get_datasheet_service
from services.camera_service import get_camera_service
from utils.rate_limiter import get_discovery_rate_limiter, RateLimitError
from utils.network_filter import get_network_filter, configure_network_filter, get_known_camera_ouis

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Load settings
settings = get_settings()

# Initialize FastAPI app
app = FastAPI(
    title="PlatoniCam Backend",
    version="0.4.0",
    description="AI-powered camera optimization with Claude Vision and ONVIF integration"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins.split(","),
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global exception handler to ensure errors return proper JSON with CORS headers
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch all unhandled exceptions and return proper JSON response"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "detail": str(exc),
            "type": type(exc).__name__,
            "traceback": traceback.format_exc() if settings.debug else None
        }
    )


# Rate limit exception handler
@app.exception_handler(RateLimitError)
async def rate_limit_exception_handler(request: Request, exc: RateLimitError):
    """Handle rate limit errors with proper 429 response"""
    logger.warning(f"Rate limit exceeded for {request.client.host}: {exc}")
    return JSONResponse(
        status_code=429,
        content={
            "detail": str(exc),
            "type": "RateLimitError",
            "retry_after_seconds": exc.retry_after_seconds,
        },
        headers={
            "Retry-After": str(exc.retry_after_seconds),
        }
    )

# ---- Startup event ----

@app.on_event("startup")
async def startup_event():
    """Application startup"""
    logger.info("=" * 60)
    logger.info("PlatoniCam Backend Starting")
    logger.info("=" * 60)
    logger.info(f"Environment: {settings.app_env}")
    logger.info(f"Claude Model: {settings.claude_model}")
    logger.info(f"API Key configured: {'Yes' if settings.anthropic_api_key else 'No'}")
    logger.info(f"Fallback to heuristic: {settings.fallback_to_heuristic}")

    # Initialize database
    try:
        init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")

    logger.info("=" * 60)

    if not settings.anthropic_api_key:
        logger.warning("No Anthropic API key configured! Will use heuristic fallback only.")
        logger.warning("Set ANTHROPIC_API_KEY in .env file to enable Claude Vision.")

# ---- Pydantic models ----

class CameraRecord(BaseModel):
    id: str
    ip: str
    vendor: Optional[str] = None
    model: Optional[str] = None
    vmsSystem: Optional[str] = None
    vmsCameraId: Optional[str] = None
    location: Optional[str] = None
    sceneType: Optional[str] = None
    purpose: Optional[str] = None

class CameraCapabilities(BaseModel):
    maxResolution: Optional[str] = None
    supportedCodecs: List[str] = []
    maxFps: Optional[int] = None
    wdrLevels: List[str] = []
    irModes: List[str] = []
    hasLPRMode: Optional[bool] = None

class StreamSettings(BaseModel):
    resolution: Optional[str] = None
    codec: Optional[str] = None
    fps: Optional[int] = None
    bitrateMbps: Optional[float] = None
    bitrateMode: Optional[str] = None
    gopSize: Optional[int] = None
    keyframeInterval: Optional[int] = None
    cbr: Optional[bool] = None
    profile: Optional[str] = None

    @field_validator('fps', 'gopSize', 'keyframeInterval', mode='before')
    @classmethod
    def coerce_int(cls, v):
        """Coerce string values to int"""
        if v is None:
            return None
        if isinstance(v, int):
            return v
        if isinstance(v, (str, float)):
            import re
            match = re.match(r'^(-?\d+)', str(v))
            if match:
                return int(match.group(1))
        return None

    @field_validator('bitrateMbps', mode='before')
    @classmethod
    def coerce_float(cls, v):
        """Coerce string values to float"""
        if v is None:
            return None
        if isinstance(v, (int, float)):
            return float(v)
        if isinstance(v, str):
            import re
            match = re.match(r'^(-?\d+\.?\d*)', str(v))
            if match:
                return float(match.group(1))
        return None

class ExposureSettings(BaseModel):
    mode: Optional[str] = None
    shutter: Optional[str] = None
    iris: Optional[str] = None
    gainLimit: Optional[str] = None
    wdr: Optional[str] = None
    blc: Optional[str] = None
    backlightComp: Optional[str] = None

class LowLightSettings(BaseModel):
    irMode: Optional[str] = None
    irIntensity: Optional[str] = None
    dayNightMode: Optional[str] = None
    dnr: Optional[str] = None
    noiseReduction: Optional[str] = None
    slowShutter: Optional[str] = None

class ImageSettings(BaseModel):
    sharpness: Optional[int] = None
    sharpening: Optional[int] = None  # Alias for sharpness
    contrast: Optional[int] = None
    saturation: Optional[int] = None
    brightness: Optional[int] = None
    whiteBalance: Optional[str] = None
    mirror: Optional[bool] = None
    flip: Optional[bool] = None
    rotation: Optional[int] = None
    dewarp: Optional[str] = None

    @field_validator('sharpness', 'sharpening', 'contrast', 'saturation', 'brightness', 'rotation', mode='before')
    @classmethod
    def coerce_int(cls, v):
        """Coerce string values to int (Claude sometimes returns strings)"""
        if v is None:
            return None
        if isinstance(v, int):
            return v
        if isinstance(v, str):
            # Remove any non-numeric suffixes and convert
            import re
            match = re.match(r'^(-?\d+)', str(v))
            if match:
                return int(match.group(1))
        return None

class CameraCurrentSettings(BaseModel):
    stream: StreamSettings
    exposure: ExposureSettings
    lowLight: LowLightSettings
    image: Optional[ImageSettings] = None

class OptimizeContext(BaseModel):
    bandwidthLimitMbps: Optional[float] = None
    targetRetentionDays: Optional[int] = None
    notes: Optional[str] = None
    sampleFrame: Optional[str] = None  # base64 data URL

class OptimizeRequest(BaseModel):
    camera: CameraRecord
    capabilities: CameraCapabilities
    currentSettings: Optional[CameraCurrentSettings] = None
    context: OptimizeContext

class OptimizeResponse(BaseModel):
    recommendedSettings: CameraCurrentSettings
    confidence: float
    warnings: List[str]
    explanation: str
    aiProvider: str  # "claude-sonnet-4-5" or "heuristic"
    processingTime: float  # seconds
    generatedAt: str  # ISO 8601 timestamp

# ---- Health check endpoint ----

@app.get("/api/health")
async def health_check():
    """Health check endpoint to verify backend is running"""
    return {
        "status": "ok",
        "version": "0.2.0-alpha",
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z"
    }


# ---- Discovery endpoints ----

@app.get("/api/discover")
async def discover_cameras(
    request: Request,
    timeout: int = 5,
    max_cameras: Optional[int] = 100
):
    """
    Discover ONVIF cameras on the network using WS-Discovery.

    Rate limited to prevent network flooding (max 3 requests/minute per client,
    30 second minimum between requests).

    Args:
        timeout: Discovery timeout in seconds (default: 5, max: 30)
        max_cameras: Maximum number of cameras to return (default: 100)

    Returns:
        List of discovered cameras with IP, vendor, model, etc.

    Raises:
        429: Rate limit exceeded
    """
    # Get client identifier for rate limiting
    client_id = request.client.host if request.client else "unknown"

    # Check rate limit (raises RateLimitError if exceeded)
    rate_limiter = get_discovery_rate_limiter()
    rate_limiter.check_rate_limit(client_id)

    # Enforce safe limits
    timeout = min(timeout, 30)  # Max 30 second timeout
    max_cameras = min(max_cameras or 100, 500)  # Max 500 cameras

    logger.info(f"Camera discovery requested from {client_id} (timeout={timeout}s, max={max_cameras})")

    try:
        discovery_service = DiscoveryService()
        cameras = await discovery_service.discover_onvif_cameras(
            timeout=timeout,
            max_cameras=max_cameras
        )

        # Get rate limit status for response headers
        rate_status = rate_limiter.get_status(client_id)

        logger.info(f"Discovery complete: found {len(cameras)} cameras")

        return {
            "cameras": cameras,
            "scanDuration": timeout,
            "foundCameras": len(cameras),
            "rateLimit": {
                "remaining": rate_status["requests_remaining"],
                "resetSeconds": rate_status["reset_seconds"],
            }
        }

    except Exception as e:
        logger.error(f"Discovery failed: {e}", exc_info=True)
        return {
            "cameras": [],
            "error": str(e),
            "foundCameras": 0
        }


@app.get("/api/cameras/{camera_id}/capabilities")
async def get_camera_capabilities(
    camera_id: str,
    ip: str,
    port: int = 80,
    username: str = "admin",
    password: str = ""
):
    """
    Query camera capabilities via ONVIF.

    Args:
        camera_id: Camera identifier
        ip: Camera IP address
        port: ONVIF port (default: 80)
        username: Camera username
        password: Camera password

    Returns:
        Camera capabilities (resolutions, codecs, features, etc.)
    """
    logger.info(f"Capabilities query for camera {camera_id} at {ip}:{port}")

    try:
        discovery_service = DiscoveryService()
        capabilities = await discovery_service.get_camera_capabilities(
            ip, port, username, password
        )

        return {
            "cameraId": camera_id,
            "capabilities": capabilities
        }

    except Exception as e:
        logger.error(f"Failed to query capabilities: {e}", exc_info=True)
        raise


@app.get("/api/cameras/{camera_id}/current-settings")
async def get_current_settings(
    camera_id: str,
    ip: str,
    port: int = 80,
    username: str = "admin",
    password: str = ""
):
    """
    Query current camera settings via ONVIF.

    Args:
        camera_id: Camera identifier
        ip: Camera IP address
        port: ONVIF port (default: 80)
        username: Camera username
        password: Camera password

    Returns:
        Current camera configuration
    """
    logger.info(f"Current settings query for camera {camera_id} at {ip}:{port}")

    try:
        discovery_service = DiscoveryService()
        current_settings = await discovery_service.get_current_settings(
            ip, port, username, password
        )

        return {
            "cameraId": camera_id,
            "currentSettings": current_settings
        }

    except Exception as e:
        logger.error(f"Failed to query current settings: {e}", exc_info=True)
        raise

# ---- Camera Connect & Snapshot endpoints ----

class CameraConnectRequest(BaseModel):
    """Request to connect to a camera and fetch all details"""
    ip: str
    port: int = 80
    username: str
    password: str
    vmsSystem: Optional[str] = None  # "hanwha-wave" or None for direct ONVIF
    vmsCameraId: Optional[str] = None
    waveServerIp: Optional[str] = None
    wavePort: Optional[int] = 7001

@app.post("/api/camera/connect")
async def connect_camera(req: CameraConnectRequest):
    """
    Connect to a camera and fetch all available information.

    Returns capabilities, current settings, and a snapshot.
    This is the main endpoint for the "Camera Bay" feature.
    """
    logger.info(f"Connecting to camera at {req.ip}:{req.port}")

    result = {
        "ip": req.ip,
        "port": req.port,
        "connected": False,
        "deviceInfo": None,
        "capabilities": None,
        "currentSettings": None,
        "snapshot": None,
        "snapshotMediaType": None,
        "profiles": None,
        "errors": []
    }

    try:
        discovery_service = DiscoveryService()

        # Get device info and capabilities via ONVIF
        try:
            # Create camera connection
            camera_id = f"CAM-{req.ip.replace('.', '-')}"

            # Get capabilities
            caps = await discovery_service.get_camera_capabilities(
                ip=req.ip,
                port=req.port,
                username=req.username,
                password=req.password
            )
            result["capabilities"] = caps
            result["connected"] = True

            # Extract device info from caps if available
            if caps:
                device = caps.get("device", {})
                result["deviceInfo"] = {
                    "vendor": device.get("manufacturer"),
                    "model": device.get("model"),
                    "firmware": device.get("firmware"),
                    "serialNumber": device.get("serial"),
                    "hardwareId": device.get("hardware_id"),
                }
                # Also add flattened capabilities for easier frontend access
                result["capabilities"] = {
                    **caps,
                    "vendor": device.get("manufacturer"),
                    "model": device.get("model"),
                    "resolutions": [caps.get("max_resolution")] if caps.get("max_resolution") else [],
                    "codecs": caps.get("supported_codecs", []),
                    "maxFps": caps.get("max_fps"),
                }

        except Exception as e:
            logger.warning(f"Failed to get capabilities: {e}")
            result["errors"].append(f"Capabilities: {str(e)}")

        # Get current settings
        try:
            settings = await discovery_service.get_current_settings(
                ip=req.ip,
                port=req.port,
                username=req.username,
                password=req.password
            )
            result["currentSettings"] = settings
        except Exception as e:
            logger.warning(f"Failed to get current settings: {e}")
            result["errors"].append(f"Settings: {str(e)}")

        # Get snapshot via ONVIF
        try:
            snapshot_data = await get_camera_snapshot_onvif(
                camera_ip=req.ip,
                port=req.port,
                username=req.username,
                password=req.password
            )
            if snapshot_data:
                result["snapshot"] = snapshot_data["base64"]
                result["snapshotMediaType"] = snapshot_data["mediaType"]
        except Exception as e:
            logger.warning(f"Failed to get snapshot: {e}")
            result["errors"].append(f"Snapshot: {str(e)}")

        # Get media profiles for future use
        try:
            from integrations.onvif_client import ONVIFClient
            client = ONVIFClient()
            camera = await client.connect_camera(
                ip=req.ip,
                port=req.port,
                username=req.username,
                password=req.password
            )
            profiles = await client.get_media_profiles(camera)
            result["profiles"] = profiles
        except Exception as e:
            logger.warning(f"Failed to get profiles: {e}")
            # Don't add to errors - profiles are optional

        return result

    except Exception as e:
        logger.error(f"Camera connect failed: {e}", exc_info=True)
        result["errors"].append(str(e))
        return result


async def get_camera_snapshot_onvif(
    camera_ip: str,
    port: int,
    username: str,
    password: str
) -> Optional[dict]:
    """
    Get snapshot from camera via ONVIF.

    Returns dict with base64 data and media type, or None if failed.
    """
    import base64
    import httpx
    from integrations.onvif_client import ONVIFClient

    try:
        client = ONVIFClient()
        camera = await client.connect_camera(
            ip=camera_ip,
            port=port,
            username=username,
            password=password
        )

        # Get first profile
        profiles = await client.get_media_profiles(camera)
        if not profiles:
            logger.warning("No media profiles found")
            return None

        profile_token = profiles[0].get("token")
        if not profile_token:
            logger.warning("No profile token found")
            return None

        # Get snapshot URI
        snapshot_uri = await client.get_snapshot_uri(camera, profile_token)

        if not snapshot_uri:
            logger.warning("No snapshot URI returned")
            return None

        logger.info(f"Fetching snapshot from: {snapshot_uri}")

        # Fetch the actual image
        async with httpx.AsyncClient(verify=False, timeout=15.0) as http_client:
            # Most cameras require auth for snapshot
            response = await http_client.get(
                snapshot_uri,
                auth=httpx.DigestAuth(username, password)
            )

            if response.status_code == 200:
                content_type = response.headers.get("content-type", "image/jpeg")
                # Normalize content type
                if "jpeg" in content_type.lower() or "jpg" in content_type.lower():
                    media_type = "image/jpeg"
                elif "png" in content_type.lower():
                    media_type = "image/png"
                else:
                    media_type = "image/jpeg"  # Default

                image_base64 = base64.b64encode(response.content).decode("utf-8")
                return {
                    "base64": f"data:{media_type};base64,{image_base64}",
                    "mediaType": media_type,
                    "size": len(response.content)
                }
            else:
                logger.warning(f"Snapshot request failed: {response.status_code}")
                return None

    except Exception as e:
        logger.error(f"Failed to get ONVIF snapshot: {e}", exc_info=True)
        return None


@app.post("/api/camera/{camera_ip}/snapshot")
async def get_snapshot(
    camera_ip: str,
    username: str = "",
    password: str = "",
    port: int = 80
):
    """
    Get a snapshot from camera via ONVIF.

    Returns base64-encoded image data.
    """
    logger.info(f"Snapshot request for camera {camera_ip}")

    if not username or not password:
        raise HTTPException(status_code=400, detail="Username and password required")

    try:
        snapshot_data = await get_camera_snapshot_onvif(
            camera_ip=camera_ip,
            port=port,
            username=username,
            password=password
        )

        if snapshot_data:
            return {
                "cameraIp": camera_ip,
                "snapshot": snapshot_data["base64"],
                "mediaType": snapshot_data["mediaType"],
                "size": snapshot_data.get("size")
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to capture snapshot")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Snapshot failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ---- AI Optimizer endpoint ----

@app.post("/api/optimize", response_model=OptimizeResponse)
async def optimize_camera(req: OptimizeRequest):
    """
    Generate optimal camera settings using Claude Vision AI.

    Falls back to heuristic engine if AI is unavailable.
    """
    logger.info(f"Optimization request for camera: {req.camera.id}")

    try:
        # Get optimization service
        optimization_service = get_optimization_service()

        # Convert request to dicts for service
        camera_dict = req.camera.model_dump()
        capabilities_dict = req.capabilities.model_dump()
        current_settings_dict = req.currentSettings.model_dump() if req.currentSettings else {}
        context_dict = req.context.model_dump()

        # Call optimization service
        result = await optimization_service.optimize(
            camera=camera_dict,
            capabilities=capabilities_dict,
            current_settings=current_settings_dict,
            context=context_dict
        )

        # Convert result back to response model
        # Use model_validate to properly parse nested dicts into Pydantic models
        recommended = result["recommendedSettings"]
        response = OptimizeResponse(
            recommendedSettings=CameraCurrentSettings.model_validate(recommended),
            confidence=result["confidence"],
            warnings=result["warnings"],
            explanation=result["explanation"],
            aiProvider=result["aiProvider"],
            processingTime=result["processingTime"],
            generatedAt=result["generatedAt"]
        )

        logger.info(
            f"Optimization complete for {req.camera.id} "
            f"(provider: {result['aiProvider']}, confidence: {result['confidence']:.2f})"
        )

        return response

    except Exception as e:
        logger.error(f"Optimization failed: {e}", exc_info=True)
        # Include more detail for debugging
        error_detail = str(e)
        if hasattr(e, '__class__'):
            error_detail = f"{e.__class__.__name__}: {e}"
        # For Pydantic validation errors, include field info
        if 'ValidationError' in str(type(e)):
            try:
                error_detail = f"Validation error: {e.errors()}"
            except:
                pass
        raise HTTPException(status_code=500, detail=error_detail)

# ---- Apply settings endpoints ----

class ApplyRequest(BaseModel):
    camera: CameraRecord
    settings: CameraCurrentSettings
    applyVia: str  # "onvif", "vms", "vendor"
    credentials: Optional[dict] = None  # {"username": "admin", "password": "..."}
    verifyAfterApply: bool = True

@app.post("/api/apply")
async def apply_settings(req: ApplyRequest):
    """
    Apply recommended settings to camera.

    Supports:
    - ONVIF protocol (applyVia="onvif")
    - VMS APIs (applyVia="vms") - future
    - Vendor APIs (applyVia="vendor") - future

    Returns:
        Apply job status with job ID for tracking
    """
    logger.info(f"Apply request for camera {req.camera.id} via {req.applyVia}")

    apply_service = ApplyService()

    try:
        if req.applyVia == ApplyMethod.ONVIF:
            # Extract credentials
            credentials = req.credentials or {}
            username = credentials.get("username", "admin")
            password = credentials.get("password", "")
            port = credentials.get("port", 80)

            # Apply via ONVIF
            result = await apply_service.apply_settings_onvif(
                camera_id=req.camera.id,
                ip=req.camera.ip,
                port=port,
                username=username,
                password=password,
                settings=req.settings.model_dump(),
                verify=req.verifyAfterApply
            )

            return result

        elif req.applyVia == ApplyMethod.VMS:
            # Apply via VMS (Hanwha WAVE supported)
            credentials = req.credentials or {}

            result = await apply_service.apply_settings_vms(
                camera_id=req.camera.id,
                vms_system=req.camera.vmsSystem or "unknown",
                vms_camera_id=req.camera.vmsCameraId or "",
                settings=req.settings.model_dump(),
                server_ip=credentials.get("server_ip", req.camera.ip),
                port=credentials.get("port", 7001),
                username=credentials.get("username", "admin"),
                password=credentials.get("password", ""),
                verify=req.verifyAfterApply
            )

            return result

        else:
            return {
                "status": "error",
                "error": {
                    "code": "INVALID_METHOD",
                    "message": f"Apply method '{req.applyVia}' not supported. Use 'onvif' or 'vms'."
                }
            }

    except Exception as e:
        logger.error(f"Apply failed: {e}", exc_info=True)
        return {
            "status": "error",
            "error": {
                "code": "APPLY_FAILED",
                "message": str(e)
            }
        }


@app.get("/api/apply/status/{job_id}")
async def get_apply_status(job_id: str):
    """
    Get status of an apply job.

    Args:
        job_id: Apply job identifier (int ID or legacy string format)

    Returns:
        Job status (pending, in_progress, completed, failed)
    """
    apply_service = ApplyService()

    # Try to parse as int (new format)
    try:
        int_job_id = int(job_id)
        job = apply_service.get_job_status(int_job_id)
    except ValueError:
        # Legacy string format (e.g., "apply-camera1-1234567890")
        job = apply_service.get_job_status_by_legacy_id(job_id)

    if not job:
        return {
            "status": "error",
            "error": {
                "code": "JOB_NOT_FOUND",
                "message": f"Apply job '{job_id}' not found"
            }
        }

    return job

# ---- Passive monitoring tick (could be cron-triggered) ----

@app.post("/api/monitor/tick")
async def monitor_tick():
    """
    Placeholder: check a set of cameras, pull stats & frames,
    and decide if re-optimization is needed.
    """
    # In reality you'd:
    # - read from DB: list of cameras under monitoring
    # - pull live stats/snapshots
    # - feed into AI / rules
    # - generate "attention needed" events
    return {"status": "ok", "checkedCameras": 0}


# ---- Hanwha WAVE VMS endpoints ----

@app.get("/api/wave/discover")
async def discover_wave_cameras(
    request: Request,
    server_ip: str,
    port: int = 7001,
    username: str = "admin",
    password: str = "",
    use_https: bool = True
):
    """
    Discover cameras via Hanwha WAVE VMS

    Rate limited to prevent abuse (max 3 requests/minute per client).

    Args:
        server_ip: WAVE server IP address
        port: WAVE API port (default: 7001)
        username: WAVE username
        password: WAVE password
        use_https: Use HTTPS (default: True)

    Returns:
        List of cameras in WAVE system

    Raises:
        429: Rate limit exceeded
    """
    # Get client identifier for rate limiting
    client_id = request.client.host if request.client else "unknown"

    # Check rate limit (raises RateLimitError if exceeded)
    rate_limiter = get_discovery_rate_limiter()
    rate_limiter.check_rate_limit(client_id)

    logger.info(f"WAVE camera discovery requested from {client_id} for server {server_ip}:{port}")

    try:
        discovery_service = DiscoveryService()
        cameras = await discovery_service.discover_wave_cameras(
            server_ip=server_ip,
            port=port,
            username=username,
            password=password,
            use_https=use_https
        )

        # Get rate limit status for response
        rate_status = rate_limiter.get_status(client_id)

        logger.info(f"WAVE discovery complete: found {len(cameras)} cameras")

        return {
            "cameras": cameras,
            "foundCameras": len(cameras),
            "vmsSystem": "hanwha-wave",
            "serverIp": server_ip,
            "rateLimit": {
                "remaining": rate_status["requests_remaining"],
                "resetSeconds": rate_status["reset_seconds"],
            }
        }

    except Exception as e:
        logger.error(f"WAVE discovery failed: {e}", exc_info=True)
        return {
            "cameras": [],
            "error": str(e),
            "foundCameras": 0
        }


@app.get("/api/wave/cameras/{camera_id}/capabilities")
async def get_wave_camera_capabilities(
    camera_id: str,
    server_ip: str,
    port: int = 7001,
    username: str = "admin",
    password: str = ""
):
    """
    Query camera capabilities via Hanwha WAVE VMS

    Args:
        camera_id: Camera ID in WAVE system
        server_ip: WAVE server IP address
        port: WAVE API port (default: 7001)
        username: WAVE username
        password: WAVE password

    Returns:
        Camera capabilities
    """
    logger.info(f"WAVE capabilities query for camera {camera_id} from {server_ip}:{port}")

    try:
        discovery_service = DiscoveryService()
        capabilities = await discovery_service.get_wave_camera_capabilities(
            server_ip=server_ip,
            camera_id=camera_id,
            port=port,
            username=username,
            password=password
        )

        return {
            "cameraId": camera_id,
            "capabilities": capabilities,
            "vmsSystem": "hanwha-wave"
        }

    except Exception as e:
        logger.error(f"Failed to query WAVE camera capabilities: {e}", exc_info=True)
        raise


@app.get("/api/wave/cameras/{camera_id}/current-settings")
async def get_wave_current_settings(
    camera_id: str,
    server_ip: str,
    port: int = 7001,
    username: str = "admin",
    password: str = ""
):
    """
    Query current camera settings via Hanwha WAVE VMS

    Args:
        camera_id: Camera ID in WAVE system
        server_ip: WAVE server IP address
        port: WAVE API port (default: 7001)
        username: WAVE username
        password: WAVE password

    Returns:
        Current camera configuration
    """
    logger.info(f"WAVE current settings query for camera {camera_id} from {server_ip}:{port}")

    try:
        discovery_service = DiscoveryService()
        current_settings = await discovery_service.get_wave_current_settings(
            server_ip=server_ip,
            camera_id=camera_id,
            port=port,
            username=username,
            password=password
        )

        return {
            "cameraId": camera_id,
            "currentSettings": current_settings,
            "vmsSystem": "hanwha-wave"
        }

    except Exception as e:
        logger.error(f"Failed to query WAVE current settings: {e}", exc_info=True)
        raise


# ---- Datasheet API endpoints ----

class DatasheetSpecs(BaseModel):
    """Manual datasheet specifications"""
    sensor_size: Optional[str] = None
    max_resolution: Optional[str] = None
    min_illumination: Optional[str] = None
    wdr_max_db: Optional[int] = None
    supported_codecs: Optional[List[str]] = None
    max_bitrate_mbps: Optional[float] = None
    ir_range_meters: Optional[float] = None
    onvif_profiles: Optional[List[str]] = None
    raw_specs_text: Optional[str] = None


class DatasheetUpload(BaseModel):
    """Request body for manual datasheet upload"""
    manufacturer: str
    model: str
    specs: DatasheetSpecs
    pdf_url: Optional[str] = None


@app.get("/api/datasheets/{manufacturer}/{model}")
async def get_datasheet(manufacturer: str, model: str):
    """
    Get cached datasheet for a camera model.

    Args:
        manufacturer: Camera manufacturer name
        model: Camera model name

    Returns:
        Cached datasheet specs or 404 if not found
    """
    logger.info(f"Datasheet query for {manufacturer} {model}")

    datasheet_service = get_datasheet_service()
    specs = datasheet_service.get_datasheet(manufacturer, model)

    if not specs:
        raise HTTPException(
            status_code=404,
            detail=f"No datasheet found for {manufacturer} {model}"
        )

    return {
        "manufacturer": manufacturer,
        "model": model,
        "specs": specs,
        "cached": True
    }


@app.post("/api/datasheets/fetch")
async def fetch_datasheet(manufacturer: str, model: str, force: bool = False):
    """
    Fetch and cache datasheet from web.

    Args:
        manufacturer: Camera manufacturer name
        model: Camera model name
        force: Force re-fetch even if cached

    Returns:
        Fetched datasheet specs or error
    """
    logger.info(f"Datasheet fetch requested for {manufacturer} {model} (force={force})")

    datasheet_service = get_datasheet_service()

    try:
        specs = await datasheet_service.fetch_and_cache(manufacturer, model, force=force)

        if specs:
            return {
                "manufacturer": manufacturer,
                "model": model,
                "specs": specs,
                "fetched": True
            }
        else:
            return {
                "manufacturer": manufacturer,
                "model": model,
                "specs": None,
                "fetched": False,
                "error": "Could not find or parse datasheet"
            }

    except Exception as e:
        logger.error(f"Datasheet fetch failed: {e}", exc_info=True)
        return {
            "manufacturer": manufacturer,
            "model": model,
            "specs": None,
            "fetched": False,
            "error": str(e)
        }


@app.post("/api/datasheets/upload")
async def upload_datasheet(data: DatasheetUpload):
    """
    Manually upload datasheet specifications.

    Args:
        data: Datasheet upload request with manufacturer, model, and specs

    Returns:
        Saved datasheet specs
    """
    logger.info(f"Manual datasheet upload for {data.manufacturer} {data.model}")

    datasheet_service = get_datasheet_service()

    # Convert Pydantic model to dict
    specs_dict = data.specs.model_dump(exclude_none=True)

    specs = datasheet_service.save_manual_datasheet(
        manufacturer=data.manufacturer,
        model=data.model,
        specs=specs_dict,
        pdf_url=data.pdf_url
    )

    return {
        "manufacturer": data.manufacturer,
        "model": data.model,
        "specs": specs,
        "source": "manual_upload"
    }


@app.delete("/api/datasheets/{manufacturer}/{model}")
async def delete_datasheet(manufacturer: str, model: str):
    """
    Delete cached datasheet.

    Args:
        manufacturer: Camera manufacturer name
        model: Camera model name

    Returns:
        Deletion status
    """
    logger.info(f"Datasheet delete requested for {manufacturer} {model}")

    datasheet_service = get_datasheet_service()
    deleted = datasheet_service.delete_datasheet(manufacturer, model)

    if deleted:
        return {
            "manufacturer": manufacturer,
            "model": model,
            "deleted": True
        }
    else:
        raise HTTPException(
            status_code=404,
            detail=f"No datasheet found for {manufacturer} {model}"
        )


@app.get("/api/datasheets")
async def list_datasheets(manufacturer: Optional[str] = None):
    """
    List all cached datasheets.

    Args:
        manufacturer: Optional filter by manufacturer

    Returns:
        List of cached datasheets
    """
    logger.info(f"Listing datasheets (manufacturer filter: {manufacturer})")

    datasheet_service = get_datasheet_service()
    datasheets = datasheet_service.list_cached_datasheets(manufacturer=manufacturer)

    return {
        "datasheets": datasheets,
        "count": len(datasheets)
    }


# ---- Network Security Endpoints ----

class NetworkFilterConfigRequest(BaseModel):
    """Request body for configuring network filter"""
    enabled: bool = False
    allowed_ouis: Optional[List[str]] = None
    allowed_macs: Optional[List[str]] = None
    blocked_macs: Optional[List[str]] = None
    allowed_subnets: Optional[List[str]] = None
    vendor_filter: Optional[List[str]] = None
    allow_unknown_oui: bool = True


@app.get("/api/security/rate-limit/status")
async def get_rate_limit_status(request: Request):
    """
    Get rate limit status for the current client.

    Returns:
        Rate limit status including remaining requests and reset time
    """
    client_id = request.client.host if request.client else "unknown"
    rate_limiter = get_discovery_rate_limiter()
    status = rate_limiter.get_status(client_id)

    return {
        "client_id": client_id,
        "status": status,
    }


@app.get("/api/security/network-filter")
async def get_network_filter_config():
    """
    Get current network filter configuration.

    Returns:
        Current filter settings and state
    """
    network_filter = get_network_filter()
    config = network_filter.config

    return {
        "enabled": config.enabled,
        "mode": config.mode,
        "allowed_ouis": list(config.allowed_ouis),
        "allowed_macs": list(config.allowed_macs),
        "blocked_macs": list(config.blocked_macs),
        "allowed_subnets": list(config.allowed_subnets),
        "vendor_filter": list(config.vendor_filter),
        "allow_unknown_oui": config.allow_unknown_oui,
    }


@app.put("/api/security/network-filter")
async def update_network_filter_config(req: NetworkFilterConfigRequest):
    """
    Update network filter configuration.

    This controls which discovered cameras are allowed/blocked based on:
    - MAC address whitelist/blacklist
    - OUI (vendor) prefix filtering
    - IP subnet restrictions
    - Vendor name filtering

    Args:
        req: Filter configuration

    Returns:
        Updated configuration
    """
    logger.info(f"Updating network filter: enabled={req.enabled}")

    configure_network_filter(
        enabled=req.enabled,
        allowed_ouis=req.allowed_ouis,
        allowed_macs=req.allowed_macs,
        blocked_macs=req.blocked_macs,
        allowed_subnets=req.allowed_subnets,
        vendor_filter=req.vendor_filter,
        allow_unknown_oui=req.allow_unknown_oui,
    )

    return {
        "message": "Network filter configuration updated",
        "enabled": req.enabled,
    }


@app.get("/api/security/known-ouis")
async def get_known_ouis():
    """
    Get list of known camera manufacturer OUIs.

    These are the first 3 bytes of MAC addresses mapped to vendor names.
    Useful for configuring OUI-based filtering.

    Returns:
        Dictionary of OUI prefixes to vendor names
    """
    ouis = get_known_camera_ouis()

    # Group by vendor for easier reading
    by_vendor = {}
    for oui, vendor in ouis.items():
        if vendor not in by_vendor:
            by_vendor[vendor] = []
        by_vendor[vendor].append(oui)

    return {
        "ouis": ouis,
        "by_vendor": by_vendor,
        "total_ouis": len(ouis),
        "total_vendors": len(by_vendor),
    }


# ---- Camera Management Endpoints ----

class CameraRegisterRequest(BaseModel):
    """Request body for camera registration"""
    ip: str
    port: int = 80
    vendor: Optional[str] = None
    model: Optional[str] = None
    location: Optional[str] = None
    scene_type: Optional[str] = None
    purpose: Optional[str] = None
    onvif_username: Optional[str] = None
    onvif_password: Optional[str] = None
    discovery_method: Optional[str] = "manual"
    vms_system: Optional[str] = None
    vms_camera_id: Optional[str] = None
    camera_id: Optional[str] = None  # Optional custom ID


class CameraUpdateRequest(BaseModel):
    """Request body for camera update"""
    location: Optional[str] = None
    scene_type: Optional[str] = None
    purpose: Optional[str] = None
    vendor: Optional[str] = None
    model: Optional[str] = None
    port: Optional[int] = None
    onvif_username: Optional[str] = None
    onvif_password_encrypted: Optional[str] = None
    vms_system: Optional[str] = None
    vms_camera_id: Optional[str] = None


@app.get("/api/cameras")
async def list_cameras(
    scene_type: Optional[str] = None,
    purpose: Optional[str] = None,
    vendor: Optional[str] = None,
    discovery_method: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
):
    """
    List registered cameras with optional filters.

    Args:
        scene_type: Filter by scene type
        purpose: Filter by purpose
        vendor: Filter by vendor
        discovery_method: Filter by discovery method
        limit: Max results (default: 100)
        offset: Pagination offset

    Returns:
        List of registered cameras
    """
    logger.info(f"Listing cameras (filters: scene_type={scene_type}, purpose={purpose})")

    camera_service = get_camera_service()
    cameras = camera_service.list_cameras(
        scene_type=scene_type,
        purpose=purpose,
        vendor=vendor,
        discovery_method=discovery_method,
        limit=limit,
        offset=offset,
    )

    return {
        "cameras": [c.to_dict() for c in cameras],
        "count": len(cameras),
        "offset": offset,
        "limit": limit,
    }


@app.post("/api/cameras")
async def register_camera(req: CameraRegisterRequest):
    """
    Register a new camera or update existing by IP.

    Args:
        req: Camera registration details

    Returns:
        Registered camera data
    """
    logger.info(f"Registering camera at {req.ip}:{req.port}")

    camera_service = get_camera_service()

    try:
        camera = camera_service.register_camera(
            ip=req.ip,
            port=req.port,
            vendor=req.vendor,
            model=req.model,
            location=req.location,
            scene_type=req.scene_type,
            purpose=req.purpose,
            onvif_username=req.onvif_username,
            onvif_password=req.onvif_password,
            discovery_method=req.discovery_method,
            vms_system=req.vms_system,
            vms_camera_id=req.vms_camera_id,
            camera_id=req.camera_id,
        )

        return {
            "camera": camera.to_dict(),
            "registered": True,
        }

    except Exception as e:
        logger.error(f"Camera registration failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/cameras/{camera_id}")
async def get_camera(camera_id: str):
    """
    Get camera by ID.

    Args:
        camera_id: Camera identifier

    Returns:
        Camera data or 404 if not found
    """
    logger.info(f"Getting camera {camera_id}")

    camera_service = get_camera_service()
    camera = camera_service.get_camera(camera_id)

    if not camera:
        raise HTTPException(
            status_code=404,
            detail=f"Camera '{camera_id}' not found"
        )

    return {
        "camera": camera.to_dict(),
    }


@app.put("/api/cameras/{camera_id}")
async def update_camera(camera_id: str, req: CameraUpdateRequest):
    """
    Update camera metadata.

    Args:
        camera_id: Camera identifier
        req: Fields to update

    Returns:
        Updated camera data or 404 if not found
    """
    logger.info(f"Updating camera {camera_id}")

    camera_service = get_camera_service()

    # Convert request to dict, excluding None values
    updates = req.model_dump(exclude_none=True)

    camera = camera_service.update_camera(camera_id, **updates)

    if not camera:
        raise HTTPException(
            status_code=404,
            detail=f"Camera '{camera_id}' not found"
        )

    return {
        "camera": camera.to_dict(),
        "updated": True,
    }


@app.delete("/api/cameras/{camera_id}")
async def delete_camera(camera_id: str, hard: bool = False):
    """
    Delete camera (soft delete by default).

    Args:
        camera_id: Camera identifier
        hard: If True, permanently delete

    Returns:
        Deletion status
    """
    logger.info(f"Deleting camera {camera_id} (hard={hard})")

    camera_service = get_camera_service()
    deleted = camera_service.delete_camera(camera_id, hard=hard)

    if not deleted:
        raise HTTPException(
            status_code=404,
            detail=f"Camera '{camera_id}' not found"
        )

    return {
        "camera_id": camera_id,
        "deleted": True,
        "hard_delete": hard,
    }


# ---- Optimization History Endpoints ----

@app.get("/api/optimizations")
async def list_optimizations(
    camera_id: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
):
    """
    List optimization history.

    Args:
        camera_id: Optional filter by camera ID
        limit: Max results (default: 50)
        offset: Pagination offset

    Returns:
        List of optimization records
    """
    logger.info(f"Listing optimizations (camera_id={camera_id})")

    optimization_service = get_optimization_service()
    optimizations = optimization_service.get_optimization_history(
        camera_id=camera_id,
        limit=limit,
        offset=offset,
    )

    return {
        "optimizations": optimizations,
        "count": len(optimizations),
        "offset": offset,
        "limit": limit,
    }


@app.get("/api/optimizations/{optimization_id}")
async def get_optimization(optimization_id: int):
    """
    Get single optimization by ID.

    Args:
        optimization_id: Optimization ID

    Returns:
        Optimization record or 404 if not found
    """
    logger.info(f"Getting optimization {optimization_id}")

    optimization_service = get_optimization_service()
    optimization = optimization_service.get_optimization(optimization_id)

    if not optimization:
        raise HTTPException(
            status_code=404,
            detail=f"Optimization '{optimization_id}' not found"
        )

    return {
        "optimization": optimization,
    }


@app.get("/api/cameras/{camera_id}/optimizations")
async def get_camera_optimizations(camera_id: str, limit: int = 20):
    """
    Get optimization history for a specific camera.

    Args:
        camera_id: Camera identifier
        limit: Max results (default: 20)

    Returns:
        List of optimizations for the camera
    """
    logger.info(f"Getting optimizations for camera {camera_id}")

    optimization_service = get_optimization_service()
    optimizations = optimization_service.get_optimization_history(
        camera_id=camera_id,
        limit=limit,
    )

    return {
        "camera_id": camera_id,
        "optimizations": optimizations,
        "count": len(optimizations),
    }


# ---- Apply Job Endpoints ----

@app.get("/api/apply/jobs")
async def list_apply_jobs(
    camera_id: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
):
    """
    List apply jobs with optional filters.

    Args:
        camera_id: Filter by camera ID
        status: Filter by status (pending, applying, success, failed, partial)
        limit: Max results (default: 50)
        offset: Pagination offset

    Returns:
        List of apply job records
    """
    logger.info(f"Listing apply jobs (camera_id={camera_id}, status={status})")

    apply_service = ApplyService()
    jobs = apply_service.list_jobs(
        camera_id=camera_id,
        status=status,
        limit=limit,
        offset=offset,
    )

    return {
        "jobs": jobs,
        "count": len(jobs),
        "offset": offset,
        "limit": limit,
    }
