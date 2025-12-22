"""
Camera Settings Apply Service

Handles applying optimized settings to cameras via:
- ONVIF protocol
- Hanwha WAVE VMS API
- Future: Genetec, Milestone, etc.
"""

import logging
from typing import Dict, Optional, List, Any
from datetime import datetime
import asyncio
from enum import Enum

from integrations.onvif_client import ONVIFClient
from integrations.hanwha_wave_client import HanwhaWAVEClient
from integrations.verkada_client import VerkadaClient
from integrations.rhombus_client import RhombusClient
from integrations.genetec_client import GenetecNotImplementedError
from database import get_db_session
from models.orm import AppliedConfig

logger = logging.getLogger(__name__)


class ApplyMethod(str, Enum):
    """Methods for applying camera settings"""
    ONVIF = "onvif"
    VMS = "vms"
    VENDOR = "vendor"
    MANUAL = "manual"


class ApplyStatus(str, Enum):
    """Status of settings apply job"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"


class ApplyService:
    """
    Service for applying camera settings

    Handles:
    - Settings translation to vendor/protocol format
    - Apply execution via ONVIF/VMS
    - Verification of applied settings
    - Error handling and rollback
    """

    def __init__(self):
        self.onvif_client = ONVIFClient()
        # Job tracking now uses database (AppliedConfig table)
        # In-memory cache for quick lookups during active operations
        self._job_cache: Dict[int, Dict] = {}

    def _create_job(
        self,
        camera_id: str,
        settings: Dict,
        apply_method: str,
        optimization_id: Optional[int] = None,
    ) -> int:
        """
        Create a new apply job in the database.

        Args:
            camera_id: Camera identifier
            settings: Settings being applied
            apply_method: Method of application (onvif, wave, etc.)
            optimization_id: Optional optimization ID this job relates to

        Returns:
            Job ID (database primary key)
        """
        try:
            with get_db_session() as session:
                job = AppliedConfig(
                    camera_id=camera_id,
                    optimization_id=optimization_id,
                    settings=settings,
                    apply_method=apply_method,
                    status="pending",
                )
                session.add(job)
                session.flush()
                job_id = job.id
                logger.info(f"Created apply job {job_id} for camera {camera_id}")
                return job_id
        except Exception as e:
            logger.error(f"Failed to create apply job: {e}")
            raise

    def _update_job_status(
        self,
        job_id: int,
        status: str,
        error_message: Optional[str] = None,
        verification_result: Optional[Dict] = None,
    ) -> None:
        """
        Update job status in database.

        Args:
            job_id: Job ID
            status: New status (pending, applying, success, failed, partial)
            error_message: Optional error message if failed
            verification_result: Optional verification results
        """
        try:
            with get_db_session() as session:
                job = session.query(AppliedConfig).filter(AppliedConfig.id == job_id).first()
                if job:
                    job.status = status
                    if error_message:
                        job.error_message = error_message
                    if verification_result:
                        job.verification_result = verification_result
                    if status == "applying":
                        job.applied_at = datetime.utcnow()
                    if status in ("success", "failed", "partial"):
                        job.completed_at = datetime.utcnow()
                    logger.debug(f"Updated job {job_id} status to {status}")
        except Exception as e:
            logger.error(f"Failed to update job {job_id}: {e}")


    async def apply_settings_onvif(
        self,
        camera_id: str,
        ip: str,
        port: int,
        username: str,
        password: str,
        settings: Dict,
        verify: bool = True,
        optimization_id: Optional[int] = None,
    ) -> Dict:
        """
        Apply settings to camera via ONVIF

        Args:
            camera_id: Camera identifier
            ip: Camera IP address
            port: ONVIF port
            username: Camera username
            password: Camera password
            settings: Settings to apply (CamOpt format)
            verify: Whether to verify settings after apply
            optimization_id: Optional optimization ID this job relates to

        Returns:
            Apply result dictionary
        """
        # Create job in database
        job_id = self._create_job(
            camera_id=camera_id,
            settings=settings,
            apply_method="onvif",
            optimization_id=optimization_id,
        )

        logger.info(f"Starting settings apply job {job_id} for camera {camera_id} at {ip}:{port}")

        # Update status to applying
        self._update_job_status(job_id, "applying")

        # Create in-memory job tracking for step details
        job = {
            "id": job_id,
            "job_id": job_id,  # For backward compatibility
            "camera_id": camera_id,
            "status": ApplyStatus.IN_PROGRESS,
            "progress": 0,
            "steps": [],
            "started_at": datetime.utcnow().isoformat() + "Z",
            "completed_at": None,
            "error": None
        }

        self._job_cache[job_id] = job

        try:
            # Step 1: Connect to camera
            job["steps"].append({"name": "Connect to camera", "status": "in_progress"})
            job["progress"] = 10

            camera = await self.onvif_client.connect_camera(ip, port, username, password)

            job["steps"][-1]["status"] = "completed"
            job["progress"] = 20

            # Step 2: Get current encoder config
            job["steps"].append({"name": "Query current configuration", "status": "in_progress"})

            encoder_configs = await self.onvif_client.get_video_encoder_configs(camera)

            if not encoder_configs:
                raise ValueError("No video encoder configurations found on camera")

            # Use first config (main stream)
            main_config = encoder_configs[0]
            config_token = main_config["token"]

            job["steps"][-1]["status"] = "completed"
            job["progress"] = 30

            # Step 3: Apply stream settings
            if "stream" in settings:
                job["steps"].append({"name": "Apply stream settings", "status": "in_progress"})

                stream_settings = self._translate_stream_settings(settings["stream"])

                await self.onvif_client.set_video_encoder_config(
                    camera,
                    config_token,
                    stream_settings
                )

                job["steps"][-1]["status"] = "completed"
                job["progress"] = 60

            # Step 4: Apply imaging settings (exposure, WDR, brightness, etc.)
            if "exposure" in settings or "lowLight" in settings or "image" in settings:
                job["steps"].append({"name": "Apply imaging settings", "status": "in_progress"})

                try:
                    # Get video source token
                    video_source_token = settings.get("video_source_token")

                    if not video_source_token:
                        # Try to get from media profiles
                        media_profiles = await self.onvif_client.get_media_profiles(camera)
                        if media_profiles:
                            video_source_token = media_profiles[0].get("video_source_token")

                    if not video_source_token:
                        # Try to get from video sources directly
                        video_sources = await self.onvif_client.get_video_sources(camera)
                        if video_sources:
                            video_source_token = video_sources[0].get("token")

                    if video_source_token:
                        # Translate and apply imaging settings
                        imaging_settings = self._translate_imaging_settings(settings)

                        if imaging_settings:
                            await self.onvif_client.set_imaging_settings(
                                camera,
                                video_source_token,
                                imaging_settings
                            )
                            job["steps"][-1]["status"] = "completed"
                            job["steps"][-1]["message"] = f"Applied imaging settings to video source: {video_source_token}"
                        else:
                            job["steps"][-1]["status"] = "skipped"
                            job["steps"][-1]["message"] = "No imaging settings to apply"
                    else:
                        job["steps"][-1]["status"] = "skipped"
                        job["steps"][-1]["message"] = "Could not find video source token - imaging settings skipped"

                except Exception as e:
                    logger.warning(f"Failed to apply imaging settings: {e}")
                    job["steps"][-1]["status"] = "warning"
                    job["steps"][-1]["message"] = f"Imaging settings partially applied or failed: {str(e)}"

                job["progress"] = 80

            # Step 5: Verify settings (if requested)
            if verify:
                job["steps"].append({"name": "Verify applied settings", "status": "in_progress"})

                # Re-query encoder config
                updated_configs = await self.onvif_client.get_video_encoder_configs(camera)
                updated_config = updated_configs[0] if updated_configs else None

                verification_result = self._verify_settings(
                    settings.get("stream", {}),
                    updated_config
                )

                job["steps"][-1]["status"] = "completed"
                job["steps"][-1]["verification"] = verification_result
                job["progress"] = 100

            # Job completed successfully
            job["status"] = ApplyStatus.COMPLETED
            job["completed_at"] = datetime.utcnow().isoformat() + "Z"
            job["result"] = {
                "applied_settings": settings,
                "verification_status": "success" if verify else "skipped"
            }

            # Update database
            verification_result = job.get("steps", [{}])[-1].get("verification") if verify else None
            self._update_job_status(job_id, "success", verification_result=verification_result)

            # Clean up cache
            if job_id in self._job_cache:
                del self._job_cache[job_id]

            logger.info(f"Apply job {job_id} completed successfully")

            return job

        except Exception as e:
            logger.error(f"Apply job {job_id} failed: {e}")

            # Mark job as failed
            job["status"] = ApplyStatus.FAILED
            job["completed_at"] = datetime.utcnow().isoformat() + "Z"
            job["error"] = {
                "code": "APPLY_FAILED",
                "message": str(e),
                "failed_step": job["steps"][-1]["name"] if job["steps"] else "Unknown"
            }

            # Mark current step as failed
            if job["steps"]:
                job["steps"][-1]["status"] = "failed"

            # Update database
            self._update_job_status(job_id, "failed", error_message=str(e))

            # Clean up cache
            if job_id in self._job_cache:
                del self._job_cache[job_id]

            return job


    def get_job_status(self, job_id: int) -> Optional[Dict]:
        """
        Get status of an apply job from database.

        Args:
            job_id: Job ID (database primary key)

        Returns:
            Job status dictionary or None if not found
        """
        # Check in-memory cache first for active jobs
        if job_id in self._job_cache:
            return self._job_cache[job_id]

        # Query from database
        try:
            with get_db_session() as session:
                job = session.query(AppliedConfig).filter(AppliedConfig.id == job_id).first()
                if job:
                    return job.to_dict()
                return None
        except Exception as e:
            logger.error(f"Failed to get job status for {job_id}: {e}")
            return None

    def get_job_status_by_legacy_id(self, legacy_job_id: str) -> Optional[Dict]:
        """
        Get job status by legacy string job ID format.

        Args:
            legacy_job_id: Legacy job ID string (e.g., "apply-camera1-1234567890")

        Returns:
            Job status dictionary or None if not found
        """
        # For backward compatibility with old job ID format
        # Try to extract camera_id and find recent job for that camera
        try:
            parts = legacy_job_id.split("-")
            if len(parts) >= 2 and parts[0] == "apply":
                camera_id = parts[1]
                with get_db_session() as session:
                    job = session.query(AppliedConfig).filter(
                        AppliedConfig.camera_id == camera_id
                    ).order_by(AppliedConfig.created_at.desc()).first()
                    if job:
                        return job.to_dict()
        except Exception as e:
            logger.warning(f"Failed to lookup legacy job {legacy_job_id}: {e}")
        return None

    def list_jobs(
        self,
        camera_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """
        List apply jobs with optional filters.

        Args:
            camera_id: Filter by camera ID
            status: Filter by status
            limit: Max results
            offset: Pagination offset

        Returns:
            List of job records as dicts
        """
        try:
            with get_db_session() as session:
                query = session.query(AppliedConfig)

                if camera_id:
                    query = query.filter(AppliedConfig.camera_id == camera_id)
                if status:
                    query = query.filter(AppliedConfig.status == status)

                query = query.order_by(AppliedConfig.created_at.desc())
                query = query.offset(offset).limit(limit)

                jobs = query.all()
                return [job.to_dict() for job in jobs]

        except Exception as e:
            logger.error(f"Failed to list jobs: {e}")
            return []


    def _translate_stream_settings(self, stream_settings: Dict) -> Dict:
        """
        Translate CamOpt stream settings to ONVIF format

        Args:
            stream_settings: CamOpt format stream settings
            {
                "resolution": "1920x1080",
                "codec": "H.265",
                "fps": 20,
                "bitrateMbps": 3.5,
                "keyframeInterval": 40
            }

        Returns:
            ONVIF-compatible settings dictionary
        """
        onvif_settings = {}

        if "resolution" in stream_settings:
            onvif_settings["resolution"] = stream_settings["resolution"]

        if "fps" in stream_settings:
            onvif_settings["fps"] = stream_settings["fps"]

        if "bitrateMbps" in stream_settings:
            onvif_settings["bitrate"] = stream_settings["bitrateMbps"]

        if "codec" in stream_settings:
            onvif_settings["codec"] = stream_settings["codec"]

        if "keyframeInterval" in stream_settings:
            onvif_settings["keyframe_interval"] = stream_settings["keyframeInterval"]

        return onvif_settings


    def _translate_imaging_settings(self, settings: Dict) -> Dict:
        """
        Translate CamOpt imaging settings to ONVIF imaging format

        Args:
            settings: CamOpt format settings containing exposure, lowLight, image

        Returns:
            ONVIF-compatible imaging settings dictionary
        """
        onvif_imaging = {}

        # Extract image settings (brightness, contrast, saturation, sharpness)
        image_settings = settings.get("image", {})
        if image_settings:
            if image_settings.get("brightness") is not None:
                onvif_imaging["brightness"] = image_settings["brightness"]
            if image_settings.get("contrast") is not None:
                onvif_imaging["contrast"] = image_settings["contrast"]
            if image_settings.get("saturation") is not None:
                onvif_imaging["saturation"] = image_settings["saturation"]
            if image_settings.get("sharpness") is not None:
                onvif_imaging["sharpness"] = image_settings["sharpness"]
            # Handle alias
            if image_settings.get("sharpening") is not None and "sharpness" not in onvif_imaging:
                onvif_imaging["sharpness"] = image_settings["sharpening"]

        # Note: Exposure and WDR settings require more complex handling
        # as they involve nested structures in ONVIF. The set_imaging_settings
        # method in onvif_client handles basic image quality settings.
        # Full exposure control would need additional implementation.

        return onvif_imaging


    def _verify_settings(self, expected: Dict, actual: Optional[Dict]) -> Dict:
        """
        Verify that applied settings match expected values

        Args:
            expected: Expected settings (CamOpt format)
            actual: Actual settings from camera (ONVIF format)

        Returns:
            Verification result
        """
        if not actual:
            return {
                "status": "failed",
                "message": "Could not query applied settings"
            }

        mismatches = []

        # Check resolution
        if "resolution" in expected:
            expected_res = expected["resolution"]
            actual_res = f"{actual['resolution']['width']}x{actual['resolution']['height']}"

            if expected_res != actual_res:
                mismatches.append({
                    "setting": "resolution",
                    "expected": expected_res,
                    "actual": actual_res
                })

        # Check FPS
        if "fps" in expected:
            if expected["fps"] != actual.get("fps"):
                mismatches.append({
                    "setting": "fps",
                    "expected": expected["fps"],
                    "actual": actual.get("fps")
                })

        # Check bitrate (with tolerance of 5%)
        if "bitrateMbps" in expected:
            expected_mbps = expected["bitrateMbps"]
            actual_mbps = actual.get("bitrate_limit", 0) / 1000.0
            tolerance = expected_mbps * 0.05

            if abs(expected_mbps - actual_mbps) > tolerance:
                mismatches.append({
                    "setting": "bitrate",
                    "expected": f"{expected_mbps} Mbps",
                    "actual": f"{actual_mbps:.1f} Mbps"
                })

        if mismatches:
            return {
                "status": "partial",
                "message": f"Some settings did not apply correctly ({len(mismatches)} mismatches)",
                "mismatches": mismatches
            }

        return {
            "status": "success",
            "message": "All settings applied correctly"
        }


    async def apply_settings_vms(
        self,
        camera_id: str,
        vms_system: str,
        vms_camera_id: str,
        settings: Dict,
        server_ip: str = "",
        port: int = 7001,
        username: str = "admin",
        password: str = "",
        verify: bool = True
    ) -> Dict:
        """
        Apply settings via VMS API

        Supported VMS platforms:
        - hanwha-wave (Hanwha WAVE VMS)
        - genetec (future)
        - milestone (future)

        Args:
            camera_id: CamOpt camera ID
            vms_system: VMS platform (hanwha-wave, genetec, milestone, etc.)
            vms_camera_id: Camera ID in VMS
            settings: Settings to apply (CamOpt format)
            server_ip: VMS server IP address
            port: VMS API port
            username: VMS username
            password: VMS password
            verify: Whether to verify settings after apply

        Returns:
            Apply result with job tracking
        """
        logger.info(f"Applying settings via {vms_system} VMS for camera {camera_id}...")

        # Route to appropriate VMS handler
        if vms_system.lower() in ["hanwha-wave", "wave", "wisenet-wave"]:
            return await self._apply_settings_wave(
                camera_id=camera_id,
                vms_camera_id=vms_camera_id,
                settings=settings,
                server_ip=server_ip,
                port=port,
                username=username,
                password=password,
                verify=verify
            )
        elif vms_system.lower() == "verkada":
            return await self._apply_settings_verkada(
                camera_id=camera_id,
                vms_camera_id=vms_camera_id,
                settings=settings,
                api_key=password,  # API key passed via password field
                org_id=username if username else None,  # Org ID via username
                region=server_ip if server_ip in ("us", "eu") else "us",
                verify=verify
            )
        elif vms_system.lower() == "rhombus":
            return await self._apply_settings_rhombus(
                camera_id=camera_id,
                vms_camera_id=vms_camera_id,
                settings=settings,
                api_key=password,  # API key passed via password field
                verify=verify
            )
        elif vms_system.lower() == "genetec":
            # Genetec requires DAP membership
            return {
                "job_id": f"vms-{camera_id}",
                "status": ApplyStatus.FAILED,
                "error": {
                    "code": "NOT_IMPLEMENTED",
                    "message": "Genetec VMS integration requires DAP membership. See https://www.genetec.com/partners/sdk-dap"
                },
                "setupUrl": "https://www.genetec.com/partners/sdk-dap",
                "developerPortal": "https://developer.genetec.com/"
            }
        elif vms_system.lower() == "milestone":
            # Future: Milestone integration
            return {
                "job_id": f"vms-{camera_id}",
                "status": ApplyStatus.FAILED,
                "error": {
                    "code": "NOT_IMPLEMENTED",
                    "message": "Milestone VMS integration not yet implemented"
                }
            }
        else:
            return {
                "job_id": f"vms-{camera_id}",
                "status": ApplyStatus.FAILED,
                "error": {
                    "code": "UNSUPPORTED_VMS",
                    "message": f"VMS platform '{vms_system}' is not supported. Supported: hanwha-wave, verkada, rhombus"
                }
            }


    async def _apply_settings_wave(
        self,
        camera_id: str,
        vms_camera_id: str,
        settings: Dict,
        server_ip: str,
        port: int,
        username: str,
        password: str,
        verify: bool,
        optimization_id: Optional[int] = None,
    ) -> Dict:
        """
        Apply settings via Hanwha WAVE VMS

        Args:
            camera_id: CamOpt camera ID
            vms_camera_id: Camera ID in WAVE
            settings: Settings to apply
            server_ip: WAVE server IP
            port: WAVE API port
            username: WAVE username
            password: WAVE password
            verify: Whether to verify after apply
            optimization_id: Optional optimization ID this job relates to

        Returns:
            Apply result
        """
        # Create job in database
        job_id = self._create_job(
            camera_id=camera_id,
            settings=settings,
            apply_method="wave",
            optimization_id=optimization_id,
        )

        logger.info(f"Starting WAVE settings apply job {job_id} for camera {camera_id}")

        # Update status to applying
        self._update_job_status(job_id, "applying")

        # Create in-memory job tracking for step details
        job = {
            "id": job_id,
            "job_id": job_id,  # For backward compatibility
            "camera_id": camera_id,
            "vms_camera_id": vms_camera_id,
            "status": ApplyStatus.IN_PROGRESS,
            "progress": 0,
            "steps": [],
            "started_at": datetime.utcnow().isoformat() + "Z",
            "completed_at": None,
            "error": None,
            "vms_system": "hanwha-wave"
        }

        self._job_cache[job_id] = job

        try:
            # Step 1: Connect to WAVE server
            job["steps"].append({"name": "Connect to WAVE server", "status": "in_progress"})
            job["progress"] = 10

            wave_client = HanwhaWAVEClient(
                server_ip=server_ip,
                port=port,
                username=username,
                password=password
            )

            # Test connection
            connected = await wave_client.test_connection()
            if not connected:
                raise Exception("Cannot connect to WAVE server")

            job["steps"][-1]["status"] = "completed"
            job["progress"] = 20

            # Step 2: Get current settings (for backup/verification)
            if verify:
                job["steps"].append({"name": "Query current settings", "status": "in_progress"})
                job["progress"] = 30

                current_settings = await wave_client.get_camera_settings(vms_camera_id)
                job["current_settings"] = current_settings

                job["steps"][-1]["status"] = "completed"
                job["progress"] = 40

            # Step 3: Apply settings
            job["steps"].append({"name": "Apply settings to camera", "status": "in_progress"})
            job["progress"] = 50

            success = await wave_client.apply_camera_settings(vms_camera_id, settings)

            if not success:
                raise Exception("Failed to apply settings via WAVE API")

            job["steps"][-1]["status"] = "completed"
            job["progress"] = 70

            # Step 4: Verify settings (if requested)
            if verify:
                job["steps"].append({"name": "Verify applied settings", "status": "in_progress"})
                job["progress"] = 80

                # Wait a moment for settings to take effect
                await asyncio.sleep(2)

                # Get updated settings
                new_settings = await wave_client.get_camera_settings(vms_camera_id)

                # Compare key settings
                verification_passed = self._verify_wave_settings(settings, new_settings)

                if not verification_passed:
                    job["steps"][-1]["status"] = "warning"
                    job["warnings"] = ["Some settings may not have been applied correctly"]
                else:
                    job["steps"][-1]["status"] = "completed"

                job["progress"] = 90

            # Complete job
            wave_client.close()

            job["status"] = ApplyStatus.COMPLETED
            job["progress"] = 100
            job["completed_at"] = datetime.utcnow().isoformat() + "Z"
            job["steps"].append({"name": "Apply complete", "status": "completed"})

            # Update database
            self._update_job_status(job_id, "success")

            # Clean up cache
            if job_id in self._job_cache:
                del self._job_cache[job_id]

            logger.info(f"WAVE apply job {job_id} completed successfully")

            return {
                "id": job_id,
                "job_id": job_id,
                "status": ApplyStatus.COMPLETED,
                "message": "Settings applied successfully via WAVE VMS",
                "camera_id": camera_id,
                "vms_camera_id": vms_camera_id
            }

        except Exception as e:
            logger.error(f"WAVE apply job {job_id} failed: {e}")

            job["status"] = ApplyStatus.FAILED
            job["error"] = {
                "code": "WAVE_APPLY_FAILED",
                "message": str(e)
            }
            job["completed_at"] = datetime.utcnow().isoformat() + "Z"

            if job["steps"] and job["steps"][-1]["status"] == "in_progress":
                job["steps"][-1]["status"] = "failed"

            # Update database
            self._update_job_status(job_id, "failed", error_message=str(e))

            # Clean up cache
            if job_id in self._job_cache:
                del self._job_cache[job_id]

            return {
                "id": job_id,
                "job_id": job_id,
                "status": ApplyStatus.FAILED,
                "error": {
                    "code": "WAVE_APPLY_FAILED",
                    "message": str(e)
                }
            }


    def _verify_wave_settings(self, applied: Dict, current: Dict) -> bool:
        """
        Verify that WAVE settings were applied correctly

        Args:
            applied: Settings that were applied
            current: Current settings from camera

        Returns:
            True if settings match, False otherwise
        """
        try:
            # Check stream settings
            applied_stream = applied.get("stream", {})
            current_stream = current.get("stream", {})

            # Resolution
            if applied_stream.get("resolution") and \
               applied_stream["resolution"] != current_stream.get("resolution"):
                logger.warning(f"Resolution mismatch: {applied_stream['resolution']} != {current_stream.get('resolution')}")
                return False

            # Codec
            if applied_stream.get("codec") and \
               applied_stream["codec"] != current_stream.get("codec"):
                logger.warning(f"Codec mismatch: {applied_stream['codec']} != {current_stream.get('codec')}")
                return False

            # FPS (allow ±1 frame tolerance)
            if applied_stream.get("fps"):
                fps_diff = abs(applied_stream["fps"] - current_stream.get("fps", 0))
                if fps_diff > 1:
                    logger.warning(f"FPS mismatch: {applied_stream['fps']} != {current_stream.get('fps')}")
                    return False

            # Bitrate (allow 10% tolerance due to encoding)
            if applied_stream.get("bitrateMbps"):
                applied_bitrate = applied_stream["bitrateMbps"]
                current_bitrate = current_stream.get("bitrateMbps", 0)
                bitrate_diff_pct = abs(applied_bitrate - current_bitrate) / applied_bitrate * 100
                if bitrate_diff_pct > 10:
                    logger.warning(f"Bitrate mismatch: {applied_bitrate} != {current_bitrate} (>{bitrate_diff_pct:.1f}%)")
                    return False

            logger.info("WAVE settings verification passed")
            return True

        except Exception as e:
            logger.error(f"Settings verification failed: {e}")
            return False


    async def _apply_settings_verkada(
        self,
        camera_id: str,
        vms_camera_id: str,
        settings: Dict,
        api_key: str,
        org_id: Optional[str] = None,
        region: str = "us",
        verify: bool = True,
        optimization_id: Optional[int] = None,
    ) -> Dict:
        """
        Apply settings via Verkada Cloud VMS

        Note: Verkada cameras are cloud-managed. Most settings are configured
        through the Command dashboard. This method returns information about
        what can/cannot be applied via API.

        Args:
            camera_id: PlatoniCam camera ID
            vms_camera_id: Camera ID in Verkada
            settings: Settings to apply
            api_key: Verkada API key
            org_id: Organization ID (optional)
            region: API region
            verify: Whether to verify after apply
            optimization_id: Optional optimization ID

        Returns:
            Apply result
        """
        logger.info(f"Applying settings via Verkada for camera {camera_id}")

        # Verkada is cloud-managed - settings are primarily controlled via Command dashboard
        # The API is read-heavy with limited write capabilities

        return {
            "id": None,
            "job_id": f"verkada-{camera_id}",
            "camera_id": camera_id,
            "vms_camera_id": vms_camera_id,
            "status": ApplyStatus.PARTIAL,
            "message": "Verkada cameras are cloud-managed. Settings should be applied via Verkada Command dashboard.",
            "vms_system": "verkada",
            "cloudManaged": True,
            "recommendations": {
                "action": "Apply settings in Verkada Command",
                "url": "https://command.verkada.com",
                "settings": settings
            },
            "note": (
                "Verkada API is primarily read-only for camera settings. "
                "Please apply the recommended settings through the Verkada Command dashboard: "
                "https://command.verkada.com"
            )
        }


    async def _apply_settings_rhombus(
        self,
        camera_id: str,
        vms_camera_id: str,
        settings: Dict,
        api_key: str,
        verify: bool = True,
        optimization_id: Optional[int] = None,
    ) -> Dict:
        """
        Apply settings via Rhombus Cloud VMS

        Args:
            camera_id: PlatoniCam camera ID
            vms_camera_id: Camera UUID in Rhombus
            settings: Settings to apply
            api_key: Rhombus API key
            verify: Whether to verify after apply
            optimization_id: Optional optimization ID

        Returns:
            Apply result
        """
        # Create job in database
        job_id = self._create_job(
            camera_id=camera_id,
            settings=settings,
            apply_method="rhombus",
            optimization_id=optimization_id,
        )

        logger.info(f"Starting Rhombus settings apply job {job_id} for camera {camera_id}")

        # Update status to applying
        self._update_job_status(job_id, "applying")

        # Create in-memory job tracking
        job = {
            "id": job_id,
            "job_id": job_id,
            "camera_id": camera_id,
            "vms_camera_id": vms_camera_id,
            "status": ApplyStatus.IN_PROGRESS,
            "progress": 0,
            "steps": [],
            "started_at": datetime.utcnow().isoformat() + "Z",
            "completed_at": None,
            "error": None,
            "vms_system": "rhombus"
        }

        self._job_cache[job_id] = job

        try:
            # Step 1: Connect to Rhombus
            job["steps"].append({"name": "Connect to Rhombus API", "status": "in_progress"})
            job["progress"] = 10

            rhombus_client = RhombusClient(api_key=api_key)

            # Test connection
            connected = await rhombus_client.test_connection()
            if not connected:
                raise Exception("Cannot connect to Rhombus API")

            job["steps"][-1]["status"] = "completed"
            job["progress"] = 20

            # Step 2: Get current settings (for backup/verification)
            if verify:
                job["steps"].append({"name": "Query current settings", "status": "in_progress"})
                job["progress"] = 30

                current_settings = await rhombus_client.get_camera_settings(vms_camera_id)
                job["current_settings"] = current_settings

                job["steps"][-1]["status"] = "completed"
                job["progress"] = 40

            # Step 3: Apply settings
            job["steps"].append({"name": "Apply settings to camera", "status": "in_progress"})
            job["progress"] = 50

            success = await rhombus_client.update_camera_config(vms_camera_id, settings)

            if not success:
                raise Exception("Failed to apply settings via Rhombus API")

            job["steps"][-1]["status"] = "completed"
            job["progress"] = 70

            # Step 4: Verify settings (if requested)
            if verify:
                job["steps"].append({"name": "Verify applied settings", "status": "in_progress"})
                job["progress"] = 80

                # Wait a moment for settings to take effect
                await asyncio.sleep(2)

                # Get updated settings
                new_settings = await rhombus_client.get_camera_settings(vms_camera_id)

                # Compare key settings (basic verification)
                verification_passed = True
                if settings.get("stream", {}).get("resolution"):
                    if settings["stream"]["resolution"] != new_settings.get("stream", {}).get("resolution"):
                        verification_passed = False

                if not verification_passed:
                    job["steps"][-1]["status"] = "warning"
                    job["warnings"] = ["Some settings may not have been applied correctly"]
                else:
                    job["steps"][-1]["status"] = "completed"

                job["progress"] = 90

            # Complete job
            rhombus_client.close()

            job["status"] = ApplyStatus.COMPLETED
            job["progress"] = 100
            job["completed_at"] = datetime.utcnow().isoformat() + "Z"
            job["steps"].append({"name": "Apply complete", "status": "completed"})

            # Update database
            self._update_job_status(job_id, "success")

            # Clean up cache
            if job_id in self._job_cache:
                del self._job_cache[job_id]

            logger.info(f"Rhombus apply job {job_id} completed successfully")

            return {
                "id": job_id,
                "job_id": job_id,
                "status": ApplyStatus.COMPLETED,
                "message": "Settings applied successfully via Rhombus",
                "camera_id": camera_id,
                "vms_camera_id": vms_camera_id,
                "vms_system": "rhombus"
            }

        except Exception as e:
            logger.error(f"Rhombus apply job {job_id} failed: {e}")

            job["status"] = ApplyStatus.FAILED
            job["error"] = {
                "code": "RHOMBUS_APPLY_FAILED",
                "message": str(e)
            }
            job["completed_at"] = datetime.utcnow().isoformat() + "Z"

            if job["steps"] and job["steps"][-1]["status"] == "in_progress":
                job["steps"][-1]["status"] = "failed"

            # Update database
            self._update_job_status(job_id, "failed", error_message=str(e))

            # Clean up cache
            if job_id in self._job_cache:
                del self._job_cache[job_id]

            return {
                "id": job_id,
                "job_id": job_id,
                "status": ApplyStatus.FAILED,
                "error": {
                    "code": "RHOMBUS_APPLY_FAILED",
                    "message": str(e)
                },
                "vms_system": "rhombus"
            }


    async def rollback_settings(
        self,
        camera_id: str,
        ip: str,
        port: int,
        username: str,
        password: str,
        previous_settings: Dict
    ) -> Dict:
        """
        Rollback to previous settings (future implementation)

        Args:
            camera_id: Camera identifier
            ip: Camera IP
            port: ONVIF port
            username: Username
            password: Password
            previous_settings: Settings to restore

        Returns:
            Rollback result
        """
        logger.info(f"Rolling back settings for camera {camera_id}...")

        # This would use the same apply logic but with previous settings
        return await self.apply_settings_onvif(
            camera_id,
            ip,
            port,
            username,
            password,
            previous_settings,
            verify=True
        )
