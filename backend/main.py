# backend/main.py
from fastapi import FastAPI, UploadFile, File, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, List
import datetime
import logging
import traceback

from config import get_settings
from services.optimization import get_optimization_service
from services.discovery import DiscoveryService
from services.apply import ApplyService, ApplyMethod

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
    logger.info("=" * 60)

    if not settings.anthropic_api_key:
        logger.warning("⚠️  No Anthropic API key configured! Will use heuristic fallback only.")
        logger.warning("⚠️  Set ANTHROPIC_API_KEY in .env file to enable Claude Vision.")

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
    timeout: int = 5,
    max_cameras: Optional[int] = None
):
    """
    Discover ONVIF cameras on the network using WS-Discovery.

    Args:
        timeout: Discovery timeout in seconds (default: 5)
        max_cameras: Maximum number of cameras to return (default: all)

    Returns:
        List of discovered cameras with IP, vendor, model, etc.
    """
    logger.info(f"Camera discovery requested (timeout={timeout}s, max={max_cameras})")

    try:
        discovery_service = DiscoveryService()
        cameras = await discovery_service.discover_onvif_cameras(
            timeout=timeout,
            max_cameras=max_cameras
        )

        logger.info(f"Discovery complete: found {len(cameras)} cameras")

        return {
            "cameras": cameras,
            "scanDuration": timeout,
            "foundCameras": len(cameras)
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

# ---- Snapshot endpoint (for HTML UI to call if you want) ----

@app.post("/api/camera/{camera_id}/snapshot")
async def snapshot(camera_id: str):
    # TODO: Pull real JPEG from RTSP / camera API / VMS
    return {"cameraId": camera_id, "snapshotUrl": f"/static/mock_{camera_id}.jpg"}

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
        raise HTTPException(status_code=500, detail=str(e))

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
        job_id: Apply job identifier

    Returns:
        Job status (pending, in_progress, completed, failed)
    """
    apply_service = ApplyService()
    job = apply_service.get_job_status(job_id)

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
    server_ip: str,
    port: int = 7001,
    username: str = "admin",
    password: str = "",
    use_https: bool = True
):
    """
    Discover cameras via Hanwha WAVE VMS

    Args:
        server_ip: WAVE server IP address
        port: WAVE API port (default: 7001)
        username: WAVE username
        password: WAVE password
        use_https: Use HTTPS (default: True)

    Returns:
        List of cameras in WAVE system
    """
    logger.info(f"WAVE camera discovery requested for server {server_ip}:{port}")

    try:
        discovery_service = DiscoveryService()
        cameras = await discovery_service.discover_wave_cameras(
            server_ip=server_ip,
            port=port,
            username=username,
            password=password,
            use_https=use_https
        )

        logger.info(f"WAVE discovery complete: found {len(cameras)} cameras")

        return {
            "cameras": cameras,
            "foundCameras": len(cameras),
            "vmsSystem": "hanwha-wave",
            "serverIp": server_ip
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
