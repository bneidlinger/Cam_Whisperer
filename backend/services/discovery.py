"""
Camera Discovery Service

Handles camera discovery via:
- ONVIF WS-Discovery
- Hanwha WAVE VMS API
- Manual registration

Also triggers background datasheet fetching for discovered cameras.
"""

import logging
from typing import List, Dict, Optional
from datetime import datetime

from integrations.onvif_client import ONVIFClient
from integrations.hanwha_wave_client import HanwhaWAVEClient

logger = logging.getLogger(__name__)

# Lazy imports to avoid circular dependencies
_datasheet_service = None
_camera_service = None
_network_filter = None

def _get_datasheet_service():
    """Lazy getter for datasheet service."""
    global _datasheet_service
    if _datasheet_service is None:
        try:
            from services.datasheet_service import get_datasheet_service
            _datasheet_service = get_datasheet_service()
        except ImportError as e:
            logger.warning(f"Datasheet service not available: {e}")
    return _datasheet_service


def _get_camera_service():
    """Lazy getter for camera service."""
    global _camera_service
    if _camera_service is None:
        try:
            from services.camera_service import get_camera_service
            _camera_service = get_camera_service()
        except ImportError as e:
            logger.warning(f"Camera service not available: {e}")
    return _camera_service


def _get_network_filter():
    """Lazy getter for network filter."""
    global _network_filter
    if _network_filter is None:
        try:
            from utils.network_filter import get_network_filter
            _network_filter = get_network_filter()
        except ImportError as e:
            logger.warning(f"Network filter not available: {e}")
    return _network_filter


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
            max_cameras: Maximum cameras to return (default: 100 for safety)

        Returns:
            List of discovered camera records
        """
        logger.info("Starting ONVIF camera discovery...")

        # Apply safe default for max_cameras to prevent resource exhaustion
        if max_cameras is None:
            max_cameras = 100

        try:
            cameras = await self.onvif_client.discover_cameras(
                timeout=timeout,
                max_cameras=max_cameras
            )

            # Enrich with additional metadata
            for camera in cameras:
                camera["discovery_method"] = "onvif"
                camera["registered"] = False  # Will be updated by auto-register

            # Apply network filtering (MAC/OUI/subnet)
            network_filter = _get_network_filter()
            if network_filter:
                # Enrich with vendor info from MAC OUI lookup
                cameras = network_filter.enrich_with_vendor(cameras)
                # Apply filters
                original_count = len(cameras)
                cameras = network_filter.filter_cameras(cameras)
                if len(cameras) < original_count:
                    logger.info(
                        f"Network filter: {original_count - len(cameras)} cameras "
                        f"removed, {len(cameras)} remaining"
                    )

            # Trigger background datasheet fetch for discovered cameras
            self._trigger_datasheet_fetch(cameras)

            # Auto-register discovered cameras in database
            self._auto_register_cameras(cameras, discovery_method="onvif")

            return cameras

        except Exception as e:
            logger.error(f"ONVIF discovery failed: {e}")
            return []

    def _trigger_datasheet_fetch(self, cameras: List[Dict]) -> None:
        """
        Trigger background datasheet fetch for discovered cameras.
        Non-blocking - returns immediately.
        """
        datasheet_service = _get_datasheet_service()
        if not datasheet_service:
            return

        for camera in cameras:
            manufacturer = camera.get("vendor") or camera.get("manufacturer")
            model = camera.get("model")

            if manufacturer and model:
                try:
                    datasheet_service.start_background_fetch(manufacturer, model)
                except Exception as e:
                    logger.warning(
                        f"Failed to start datasheet fetch for {manufacturer} {model}: {e}"
                    )

    def _auto_register_cameras(
        self,
        cameras: List[Dict],
        discovery_method: str,
        vms_system: Optional[str] = None,
    ) -> None:
        """
        Auto-register discovered cameras in the database.

        Creates or updates camera records for each discovered camera.
        Non-blocking - failures are logged but don't stop discovery.

        Args:
            cameras: List of discovered camera dicts
            discovery_method: How cameras were discovered ('onvif', 'wave')
            vms_system: VMS system name if applicable
        """
        camera_service = _get_camera_service()
        if not camera_service:
            logger.warning("Camera service not available - skipping auto-registration")
            return

        registered_count = 0
        for camera in cameras:
            try:
                ip = camera.get("ip")
                if not ip:
                    continue

                # Register or update camera
                camera_service.register_camera(
                    ip=ip,
                    port=camera.get("port", 80),
                    vendor=camera.get("vendor") or camera.get("manufacturer"),
                    model=camera.get("model"),
                    location=camera.get("name"),  # Use camera name as initial location
                    discovery_method=discovery_method,
                    vms_system=vms_system,
                    vms_camera_id=camera.get("id") if vms_system else None,
                )
                camera["registered"] = True
                registered_count += 1

            except Exception as e:
                logger.warning(
                    f"Failed to auto-register camera {camera.get('ip')}: {e}"
                )

        logger.info(f"Auto-registered {registered_count}/{len(cameras)} discovered cameras")


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

            # Get video sources (for imaging capabilities)
            video_sources = []
            try:
                video_sources = await self.onvif_client.get_video_sources(camera)
            except Exception as e:
                logger.warning(f"Could not query video sources: {e}")

            # Get media profiles
            media_profiles = []
            try:
                media_profiles = await self.onvif_client.get_media_profiles(camera)
            except Exception as e:
                logger.warning(f"Could not query media profiles: {e}")

            # Build capabilities response
            capabilities = {
                "device": device_info,
                "video_encoders": encoder_configs,
                "video_sources": video_sources,
                "media_profiles": media_profiles,
                "max_resolution": self._get_max_resolution(encoder_configs),
                "supported_codecs": self._get_supported_codecs(encoder_configs),
                "max_fps": self._get_max_fps(encoder_configs),
                "has_imaging_service": device_info.get("capabilities", {}).get("imaging", False),
                "queried_at": datetime.utcnow().isoformat() + "Z"
            }

            # Trigger background datasheet fetch
            manufacturer = device_info.get("manufacturer")
            model = device_info.get("model")
            if manufacturer and model:
                self._trigger_datasheet_fetch([{"vendor": manufacturer, "model": model}])

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

            # Get video source token for imaging settings
            video_source_token = None
            imaging_settings = None

            try:
                # First try to get from media profiles
                media_profiles = await self.onvif_client.get_media_profiles(camera)
                if media_profiles:
                    video_source_token = media_profiles[0].get("video_source_token")

                # Fallback to video sources directly
                if not video_source_token:
                    video_sources = await self.onvif_client.get_video_sources(camera)
                    if video_sources:
                        video_source_token = video_sources[0].get("token")

                # Get imaging settings if we have a token
                if video_source_token:
                    imaging_settings = await self.onvif_client.get_imaging_settings(
                        camera, video_source_token
                    )
                    logger.info(f"Successfully retrieved imaging settings for video source: {video_source_token}")
            except Exception as e:
                logger.warning(f"Could not retrieve imaging settings: {e}")

            # Build current settings response
            current_settings = {
                "stream": {
                    "resolution": f"{main_config['resolution']['width']}x{main_config['resolution']['height']}",
                    "codec": main_config['encoding'],
                    "fps": main_config['fps'],
                    "bitrateMbps": main_config['bitrate_limit'] / 1000.0,  # Convert Kbps to Mbps
                },
                "exposure": self._build_exposure_settings(imaging_settings),
                "lowLight": self._build_low_light_settings(imaging_settings),
                "image": self._build_image_settings(imaging_settings),
                "video_source_token": video_source_token,  # Include for apply operations
                "queried_at": datetime.utcnow().isoformat() + "Z"
            }

            return current_settings

        except Exception as e:
            logger.error(f"Failed to query current settings: {e}")
            raise

    def _build_exposure_settings(self, imaging_settings: Optional[Dict]) -> Dict:
        """Build exposure settings from imaging data"""
        if not imaging_settings:
            return {
                "mode": "Unknown",
                "shutter": "Unknown",
                "iris": "Unknown",
                "wdr": "Unknown"
            }

        exposure = imaging_settings.get("exposure", {})
        wdr = imaging_settings.get("wdr", {})

        return {
            "mode": exposure.get("mode", "Auto"),
            "shutter": f"{exposure.get('min_exposure_time', 'Auto')}-{exposure.get('max_exposure_time', 'Auto')}" if exposure.get('min_exposure_time') else "Auto",
            "iris": "Auto",  # ONVIF doesn't always expose this separately
            "gainLimit": f"{exposure.get('max_gain', 'Auto')}" if exposure.get('max_gain') else "Auto",
            "wdr": wdr.get("mode", "Unknown"),
            "wdrLevel": wdr.get("level") if wdr.get("level") is not None else None
        }

    def _build_low_light_settings(self, imaging_settings: Optional[Dict]) -> Dict:
        """Build low light settings from imaging data"""
        if not imaging_settings:
            return {
                "irMode": "Unknown",
                "noiseReduction": "Unknown"
            }

        # Note: IR mode is often controlled via PTZ or separate service
        # ONVIF Imaging service typically doesn't expose IR directly
        return {
            "irMode": "Auto",  # Usually controlled elsewhere
            "dayNightMode": "Auto",
            "noiseReduction": "Unknown"  # Would need to check for DNR extension
        }

    def _build_image_settings(self, imaging_settings: Optional[Dict]) -> Optional[Dict]:
        """Build image quality settings from imaging data"""
        if not imaging_settings:
            return None

        return {
            "brightness": imaging_settings.get("brightness"),
            "contrast": imaging_settings.get("contrast"),
            "saturation": imaging_settings.get("saturation"),
            "sharpness": imaging_settings.get("sharpness")
        }


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
                camera["registered"] = False  # Will be updated by auto-register
                camera["wave_server"] = server_ip

            wave_client.close()

            # Apply network filtering (MAC/OUI/subnet)
            network_filter = _get_network_filter()
            if network_filter:
                # Enrich with vendor info from MAC OUI lookup
                cameras = network_filter.enrich_with_vendor(cameras)
                # Apply filters
                original_count = len(cameras)
                cameras = network_filter.filter_cameras(cameras)
                if len(cameras) < original_count:
                    logger.info(
                        f"Network filter: {original_count - len(cameras)} cameras "
                        f"removed, {len(cameras)} remaining"
                    )

            # Trigger background datasheet fetch for discovered cameras
            self._trigger_datasheet_fetch(cameras)

            # Auto-register discovered cameras in database
            self._auto_register_cameras(
                cameras,
                discovery_method="wave",
                vms_system="hanwha-wave",
            )

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
