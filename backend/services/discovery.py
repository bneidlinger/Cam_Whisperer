"""
Camera Discovery Service

Handles camera discovery via:
- ONVIF WS-Discovery
- Hanwha WAVE VMS API
- Manual registration
"""

import logging
from typing import List, Dict, Optional
from datetime import datetime

from integrations.onvif_client import ONVIFClient
from integrations.hanwha_wave_client import HanwhaWAVEClient

logger = logging.getLogger(__name__)


class DiscoveryService:
    """
    Camera discovery and registration service

    Supports discovery via:
    - ONVIF protocol (direct camera discovery)
    - Hanwha WAVE VMS (VMS-managed cameras)
    """

    def __init__(self):
        self.onvif_client = ONVIFClient()
        # WAVE client will be created on-demand with server credentials


    async def discover_onvif_cameras(
        self,
        timeout: int = 5,
        max_cameras: Optional[int] = None
    ) -> List[Dict]:
        """
        Discover cameras via ONVIF WS-Discovery

        Args:
            timeout: Discovery timeout in seconds
            max_cameras: Maximum cameras to return

        Returns:
            List of discovered camera records
        """
        logger.info("Starting ONVIF camera discovery...")

        try:
            cameras = await self.onvif_client.discover_cameras(
                timeout=timeout,
                max_cameras=max_cameras
            )

            # Enrich with additional metadata
            for camera in cameras:
                camera["discovery_method"] = "onvif"
                camera["registered"] = False  # Not yet added to DB

            return cameras

        except Exception as e:
            logger.error(f"ONVIF discovery failed: {e}")
            return []


    async def get_camera_capabilities(
        self,
        ip: str,
        port: int,
        username: str,
        password: str
    ) -> Dict:
        """
        Query camera capabilities via ONVIF

        Args:
            ip: Camera IP address
            port: ONVIF port
            username: Camera username
            password: Camera password

        Returns:
            Dictionary with capabilities
        """
        logger.info(f"Querying capabilities for camera at {ip}:{port}...")

        try:
            # Connect to camera
            camera = await self.onvif_client.connect_camera(ip, port, username, password)

            # Get device info
            device_info = await self.onvif_client.get_camera_info(camera)

            # Get encoder configs
            encoder_configs = await self.onvif_client.get_video_encoder_configs(camera)

            # Build capabilities response
            capabilities = {
                "device": device_info,
                "video_encoders": encoder_configs,
                "max_resolution": self._get_max_resolution(encoder_configs),
                "supported_codecs": self._get_supported_codecs(encoder_configs),
                "max_fps": self._get_max_fps(encoder_configs),
                "queried_at": datetime.utcnow().isoformat() + "Z"
            }

            return capabilities

        except Exception as e:
            logger.error(f"Failed to query camera capabilities: {e}")
            raise


    async def get_current_settings(
        self,
        ip: str,
        port: int,
        username: str,
        password: str
    ) -> Dict:
        """
        Query current camera settings via ONVIF

        Args:
            ip: Camera IP address
            port: ONVIF port
            username: Camera username
            password: Camera password

        Returns:
            Dictionary with current settings
        """
        logger.info(f"Querying current settings for camera at {ip}:{port}...")

        try:
            # Connect to camera
            camera = await self.onvif_client.connect_camera(ip, port, username, password)

            # Get encoder configs
            encoder_configs = await self.onvif_client.get_video_encoder_configs(camera)

            if not encoder_configs:
                raise ValueError("No video encoder configurations found")

            # Use first config (usually the main stream)
            main_config = encoder_configs[0]

            # Get imaging settings (need video source token)
            # For now, use a default or skip if we don't have it
            # imaging_settings = await self.onvif_client.get_imaging_settings(camera, video_source_token)

            current_settings = {
                "stream": {
                    "resolution": f"{main_config['resolution']['width']}x{main_config['resolution']['height']}",
                    "codec": main_config['encoding'],
                    "fps": main_config['fps'],
                    "bitrateMbps": main_config['bitrate_limit'] / 1000.0,  # Convert Kbps to Mbps
                },
                "exposure": {
                    # These would come from imaging settings
                    "shutter": "Auto",  # Placeholder
                    "iris": "Auto",
                    "wdr": "Unknown"
                },
                "lowLight": {
                    "irMode": "Auto",
                    "noiseReduction": "Unknown"
                },
                "queried_at": datetime.utcnow().isoformat() + "Z"
            }

            return current_settings

        except Exception as e:
            logger.error(f"Failed to query current settings: {e}")
            raise


    def _get_max_resolution(self, encoder_configs: List[Dict]) -> str:
        """Extract maximum resolution from encoder configs"""
        if not encoder_configs:
            return "Unknown"

        max_width = 0
        max_height = 0

        for config in encoder_configs:
            res = config.get("resolution", {})
            width = res.get("width", 0)
            height = res.get("height", 0)

            if width * height > max_width * max_height:
                max_width = width
                max_height = height

        return f"{max_width}x{max_height}" if max_width > 0 else "Unknown"


    def _get_supported_codecs(self, encoder_configs: List[Dict]) -> List[str]:
        """Extract supported codecs from encoder configs"""
        codecs = set()

        for config in encoder_configs:
            encoding = config.get("encoding")
            if encoding:
                # Map ONVIF encoding names to standard names
                codec_map = {
                    "H264": "H.264",
                    "H265": "H.265",
                    "JPEG": "MJPEG"
                }
                codec = codec_map.get(encoding, encoding)
                codecs.add(codec)

        return sorted(list(codecs))


    def _get_max_fps(self, encoder_configs: List[Dict]) -> int:
        """Extract maximum FPS from encoder configs"""
        if not encoder_configs:
            return 30  # Default assumption

        max_fps = 0

        for config in encoder_configs:
            fps = config.get("fps", 0)
            if fps > max_fps:
                max_fps = fps

        return max_fps if max_fps > 0 else 30


    # ============================================================================
    # Hanwha WAVE VMS Discovery Methods
    # ============================================================================

    async def discover_wave_cameras(
        self,
        server_ip: str,
        port: int = 7001,
        username: str = "admin",
        password: str = "",
        use_https: bool = True
    ) -> List[Dict]:
        """
        Discover cameras via Hanwha WAVE VMS

        Args:
            server_ip: WAVE server IP address
            port: WAVE API port (default: 7001)
            username: WAVE username
            password: WAVE password
            use_https: Use HTTPS (default: True)

        Returns:
            List of discovered camera records
        """
        logger.info(f"Starting WAVE camera discovery from {server_ip}:{port}...")

        try:
            # Create WAVE client
            wave_client = HanwhaWAVEClient(
                server_ip=server_ip,
                port=port,
                username=username,
                password=password,
                use_https=use_https
            )

            # Test connection first
            connected = await wave_client.test_connection()
            if not connected:
                logger.error("Cannot connect to WAVE server")
                wave_client.close()
                return []

            # Get cameras from WAVE
            cameras = await wave_client.get_cameras()

            # Enrich with additional metadata
            for camera in cameras:
                camera["discovery_method"] = "wave"
                camera["registered"] = False  # Not yet added to DB
                camera["wave_server"] = server_ip

            wave_client.close()

            logger.info(f"Discovered {len(cameras)} cameras from WAVE VMS")
            return cameras

        except Exception as e:
            logger.error(f"WAVE discovery failed: {e}")
            return []


    async def get_wave_camera_capabilities(
        self,
        server_ip: str,
        camera_id: str,
        port: int = 7001,
        username: str = "admin",
        password: str = ""
    ) -> Dict:
        """
        Query camera capabilities via WAVE VMS

        Args:
            server_ip: WAVE server IP address
            camera_id: Camera ID in WAVE system
            port: WAVE API port
            username: WAVE username
            password: WAVE password

        Returns:
            Dictionary with capabilities
        """
        logger.info(f"Querying WAVE camera {camera_id} capabilities...")

        try:
            # Create WAVE client
            wave_client = HanwhaWAVEClient(
                server_ip=server_ip,
                port=port,
                username=username,
                password=password
            )

            # Get camera settings (which includes capabilities)
            settings = await wave_client.get_camera_settings(camera_id)

            # Get all cameras to find camera details
            cameras = await wave_client.get_cameras()
            camera_info = next((c for c in cameras if c["id"] == camera_id), {})

            wave_client.close()

            # Build capabilities response
            capabilities = {
                "device": {
                    "manufacturer": camera_info.get("vendor", "Unknown"),
                    "model": camera_info.get("model", "Unknown"),
                    "name": camera_info.get("name", "Unknown")
                },
                "current_settings": settings,
                "max_resolution": settings["stream"]["resolution"],
                "supported_codecs": [settings["stream"]["codec"]],  # WAVE doesn't expose full list
                "max_fps": settings["stream"]["fps"],
                "vms_managed": True,
                "vms_system": "hanwha-wave",
                "queried_at": datetime.utcnow().isoformat() + "Z"
            }

            return capabilities

        except Exception as e:
            logger.error(f"Failed to query WAVE camera capabilities: {e}")
            raise


    async def get_wave_current_settings(
        self,
        server_ip: str,
        camera_id: str,
        port: int = 7001,
        username: str = "admin",
        password: str = ""
    ) -> Dict:
        """
        Query current camera settings via WAVE VMS

        Args:
            server_ip: WAVE server IP address
            camera_id: Camera ID in WAVE system
            port: WAVE API port
            username: WAVE username
            password: WAVE password

        Returns:
            Dictionary with current settings
        """
        logger.info(f"Querying WAVE camera {camera_id} current settings...")

        try:
            # Create WAVE client
            wave_client = HanwhaWAVEClient(
                server_ip=server_ip,
                port=port,
                username=username,
                password=password
            )

            # Get camera settings
            settings = await wave_client.get_camera_settings(camera_id)

            wave_client.close()

            # Add metadata
            settings["queried_at"] = datetime.utcnow().isoformat() + "Z"
            settings["vms_managed"] = True
            settings["vms_system"] = "hanwha-wave"

            return settings

        except Exception as e:
            logger.error(f"Failed to query WAVE current settings: {e}")
            raise
