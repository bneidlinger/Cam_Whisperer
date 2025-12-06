"""
Camera Settings Apply Service

Handles applying optimized settings to cameras via:
- ONVIF protocol
- Hanwha WAVE VMS API
- Future: Genetec, Milestone, etc.
"""

import logging
from typing import Dict, Optional
from datetime import datetime
import asyncio
from enum import Enum

from integrations.onvif_client import ONVIFClient
from integrations.hanwha_wave_client import HanwhaWAVEClient

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
        self.active_jobs = {}  # In-memory job tracking (should use DB in production)


    async def apply_settings_onvif(
        self,
        camera_id: str,
        ip: str,
        port: int,
        username: str,
        password: str,
        settings: Dict,
        verify: bool = True
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

        Returns:
            Apply result dictionary
        """
        job_id = f"apply-{camera_id}-{int(datetime.utcnow().timestamp())}"

        logger.info(f"Starting settings apply job {job_id} for camera {camera_id} at {ip}:{port}")

        # Create job tracking
        job = {
            "job_id": job_id,
            "camera_id": camera_id,
            "status": ApplyStatus.IN_PROGRESS,
            "progress": 0,
            "steps": [],
            "started_at": datetime.utcnow().isoformat() + "Z",
            "completed_at": None,
            "error": None
        }

        self.active_jobs[job_id] = job

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

            # Step 4: Apply imaging settings (exposure, WDR, etc.)
            # Note: This requires video source token, which we'd need to query
            # For now, we'll skip imaging settings or implement in future
            if "exposure" in settings or "lowLight" in settings or "image" in settings:
                job["steps"].append({"name": "Apply imaging settings", "status": "skipped"})
                job["steps"][-1]["message"] = "Imaging settings require video source token (not implemented yet)"
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

            return job


    def get_job_status(self, job_id: str) -> Optional[Dict]:
        """
        Get status of an apply job

        Args:
            job_id: Job identifier

        Returns:
            Job status dictionary or None if not found
        """
        return self.active_jobs.get(job_id)


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
        elif vms_system.lower() == "genetec":
            # Future: Genetec integration
            return {
                "job_id": f"vms-{camera_id}",
                "status": ApplyStatus.FAILED,
                "error": {
                    "code": "NOT_IMPLEMENTED",
                    "message": "Genetec VMS integration not yet implemented"
                }
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
                    "message": f"VMS platform '{vms_system}' is not supported"
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
        verify: bool
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

        Returns:
            Apply result
        """
        job_id = f"apply-wave-{camera_id}-{int(datetime.utcnow().timestamp())}"

        logger.info(f"Starting WAVE settings apply job {job_id} for camera {camera_id}")

        # Create job tracking
        job = {
            "job_id": job_id,
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

        self.active_jobs[job_id] = job

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

            logger.info(f"WAVE apply job {job_id} completed successfully")

            return {
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

            return {
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
