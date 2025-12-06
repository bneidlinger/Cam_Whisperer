"""
ONVIF Client for Camera Discovery and Configuration

This module provides ONVIF protocol integration for:
- Camera discovery via WS-Discovery
- Querying camera capabilities and current settings
- Applying optimized settings to cameras
- Verifying configuration changes

Supports ONVIF Profile S (streaming) and Profile T (advanced features)
"""

import logging
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import asyncio
from concurrent.futures import ThreadPoolExecutor

from onvif import ONVIFCamera
from zeep.exceptions import Fault as ZeepFault

try:
    from wsdiscovery.discovery import ThreadedWSDiscovery as WSDiscovery
    from wsdiscovery.scope import Scope
    WSDISCOVERY_AVAILABLE = True
except ImportError:
    logger.warning("WSDiscovery not available. Install with: pip install WSDiscovery")
    WSDISCOVERY_AVAILABLE = False
    WSDiscovery = None
    Scope = None

logger = logging.getLogger(__name__)


class ONVIFClient:
    """
    ONVIF protocol client for IP camera integration

    Handles camera discovery, settings query, and configuration apply.
    Uses onvif-zeep library for SOAP/WSDL communication.
    """

    def __init__(self, timeout: int = 10):
        """
        Initialize ONVIF client

        Args:
            timeout: Connection timeout in seconds (default: 10)
        """
        self.timeout = timeout
        self.executor = ThreadPoolExecutor(max_workers=10)


    async def discover_cameras(
        self,
        timeout: int = 5,
        max_cameras: Optional[int] = None
    ) -> List[Dict]:
        """
        Discover ONVIF cameras on the network using WS-Discovery

        Args:
            timeout: Discovery timeout in seconds (default: 5)
            max_cameras: Maximum number of cameras to return (default: all)

        Returns:
            List of discovered camera info dictionaries:
            [
                {
                    "id": "onvif-192.168.1.104",
                    "ip": "192.168.1.104",
                    "port": 80,
                    "name": "Camera Name",
                    "manufacturer": "Hanwha",
                    "model": "QNV-7080R",
                    "firmware": "2.40",
                    "mac": "00:09:18:ab:cd:ef",
                    "scopes": [...],
                    "discovered_at": "2025-12-06T..."
                },
                ...
            ]
        """
        logger.info(f"Starting ONVIF camera discovery (timeout={timeout}s)...")

        if not WSDISCOVERY_AVAILABLE:
            logger.error("WSDiscovery not available - cannot perform camera discovery")
            return []

        discovered = []

        try:
            # Run WS-Discovery in thread pool (blocking operation)
            loop = asyncio.get_event_loop()
            services = await loop.run_in_executor(
                self.executor,
                self._discover_services,
                timeout
            )

            logger.info(f"WS-Discovery found {len(services)} ONVIF services")

            # Process each discovered service
            for service in services:
                try:
                    camera_info = await self._process_discovered_service(service)
                    if camera_info:
                        discovered.append(camera_info)

                        if max_cameras and len(discovered) >= max_cameras:
                            break

                except Exception as e:
                    logger.warning(f"Failed to process discovered service: {e}")
                    continue

            logger.info(f"Successfully discovered {len(discovered)} cameras")
            return discovered

        except Exception as e:
            logger.error(f"Camera discovery failed: {e}")
            return []


    def _discover_services(self, timeout: int) -> List:
        """
        Run WS-Discovery scan (blocking operation)

        Args:
            timeout: Discovery timeout in seconds

        Returns:
            List of discovered services
        """
        wsd = WSDiscovery()
        wsd.start()

        try:
            # Probe for ONVIF devices
            services = wsd.searchServices(timeout=timeout)
            return services
        finally:
            wsd.stop()


    async def _process_discovered_service(self, service) -> Optional[Dict]:
        """
        Process a discovered WS-Discovery service and extract camera info

        Args:
            service: WS-Discovery service object

        Returns:
            Camera info dictionary or None if not a valid camera
        """
        # Extract IP and port from XAddrs
        xaddrs = service.getXAddrs()
        if not xaddrs:
            return None

        # Parse first XAddr (usually the HTTP endpoint)
        xaddr = xaddrs[0]
        ip, port = self._parse_xaddr(xaddr)

        if not ip:
            return None

        # Extract scopes (contains manufacturer, model, etc.)
        scopes = service.getScopes()
        scope_info = self._parse_scopes(scopes)

        camera_info = {
            "id": f"onvif-{ip}",
            "ip": ip,
            "port": port,
            "name": scope_info.get("name", f"Camera-{ip}"),
            "manufacturer": scope_info.get("manufacturer", "Unknown"),
            "model": scope_info.get("model", "Unknown"),
            "scopes": [str(s) for s in scopes],
            "xaddrs": xaddrs,
            "discovered_at": datetime.utcnow().isoformat() + "Z"
        }

        logger.debug(f"Discovered camera: {camera_info['manufacturer']} {camera_info['model']} at {ip}:{port}")

        return camera_info


    def _parse_xaddr(self, xaddr: str) -> Tuple[Optional[str], int]:
        """
        Parse IP and port from ONVIF XAddr URL

        Args:
            xaddr: XAddr URL (e.g., "http://192.168.1.104:80/onvif/device_service")

        Returns:
            Tuple of (ip, port) or (None, 80)
        """
        try:
            # Simple parsing: extract IP and port from URL
            # Format: http://IP:PORT/path
            if "://" in xaddr:
                url_part = xaddr.split("://")[1]
                if "/" in url_part:
                    host_port = url_part.split("/")[0]
                else:
                    host_port = url_part

                if ":" in host_port:
                    ip, port_str = host_port.split(":")
                    return ip, int(port_str)
                else:
                    return host_port, 80
        except Exception as e:
            logger.warning(f"Failed to parse XAddr '{xaddr}': {e}")

        return None, 80


    def _parse_scopes(self, scopes: List[Scope]) -> Dict[str, str]:
        """
        Parse ONVIF scopes to extract camera metadata

        Args:
            scopes: List of Scope objects from WS-Discovery

        Returns:
            Dictionary with manufacturer, model, name, etc.
        """
        info = {}

        for scope in scopes:
            scope_str = str(scope).lower()

            # Extract manufacturer
            if "/hardware/" in scope_str:
                parts = scope_str.split("/hardware/")
                if len(parts) > 1:
                    info["manufacturer"] = parts[1].split("/")[0].title()

            # Extract model
            if "/model/" in scope_str:
                parts = scope_str.split("/model/")
                if len(parts) > 1:
                    info["model"] = parts[1].split("/")[0].upper()

            # Extract name
            if "/name/" in scope_str:
                parts = scope_str.split("/name/")
                if len(parts) > 1:
                    info["name"] = parts[1].split("/")[0].replace("_", " ")

        return info


    async def connect_camera(
        self,
        ip: str,
        port: int,
        username: str,
        password: str
    ) -> ONVIFCamera:
        """
        Connect to an ONVIF camera

        Args:
            ip: Camera IP address
            port: ONVIF port (usually 80)
            username: Camera username
            password: Camera password

        Returns:
            ONVIFCamera instance

        Raises:
            Exception: If connection fails
        """
        logger.info(f"Connecting to ONVIF camera at {ip}:{port}...")

        try:
            # Create ONVIF camera instance (blocking operation)
            # Note: wsdl_dir will use package default if not specified
            loop = asyncio.get_event_loop()
            camera = await loop.run_in_executor(
                self.executor,
                lambda: ONVIFCamera(ip, port, username, password)
            )

            logger.info(f"Successfully connected to camera at {ip}:{port}")
            return camera

        except Exception as e:
            logger.error(f"Failed to connect to camera at {ip}:{port}: {e}")
            raise


    async def get_camera_info(self, camera: ONVIFCamera) -> Dict:
        """
        Get detailed camera information

        Args:
            camera: ONVIFCamera instance

        Returns:
            Dictionary with device info, capabilities, etc.
        """
        logger.info("Querying camera device information...")

        try:
            # Get device management service
            device_mgmt = camera.create_devicemgmt_service()

            # Run blocking calls in executor
            loop = asyncio.get_event_loop()

            device_info = await loop.run_in_executor(
                self.executor,
                device_mgmt.GetDeviceInformation
            )

            capabilities = await loop.run_in_executor(
                self.executor,
                device_mgmt.GetCapabilities
            )

            return {
                "manufacturer": device_info.Manufacturer,
                "model": device_info.Model,
                "firmware": device_info.FirmwareVersion,
                "serial": device_info.SerialNumber,
                "hardware_id": device_info.HardwareId,
                "capabilities": {
                    "analytics": capabilities.Analytics is not None,
                    "device": capabilities.Device is not None,
                    "events": capabilities.Events is not None,
                    "imaging": capabilities.Imaging is not None,
                    "media": capabilities.Media is not None,
                    "ptz": capabilities.PTZ is not None,
                }
            }

        except Exception as e:
            logger.error(f"Failed to get camera info: {e}")
            raise


    async def get_video_encoder_configs(self, camera: ONVIFCamera) -> List[Dict]:
        """
        Get video encoder configurations from camera

        Args:
            camera: ONVIFCamera instance

        Returns:
            List of encoder configuration dictionaries
        """
        logger.info("Querying video encoder configurations...")

        try:
            media = camera.create_media_service()

            loop = asyncio.get_event_loop()
            configs = await loop.run_in_executor(
                self.executor,
                media.GetVideoEncoderConfigurations
            )

            result = []
            for config in configs:
                result.append({
                    "name": config.Name,
                    "token": config.token,
                    "resolution": {
                        "width": config.Resolution.Width,
                        "height": config.Resolution.Height
                    },
                    "quality": config.Quality,
                    "fps": config.RateControl.FrameRateLimit,
                    "encoding": config.Encoding,
                    "bitrate_limit": config.RateControl.BitrateLimit,
                    "encoding_interval": config.RateControl.EncodingInterval
                })

            logger.info(f"Found {len(result)} video encoder configurations")
            return result

        except Exception as e:
            logger.error(f"Failed to get encoder configs: {e}")
            raise


    async def get_imaging_settings(self, camera: ONVIFCamera, video_source_token: str) -> Dict:
        """
        Get imaging settings (exposure, white balance, etc.)

        Args:
            camera: ONVIFCamera instance
            video_source_token: Video source token

        Returns:
            Dictionary with imaging settings
        """
        logger.info("Querying imaging settings...")

        try:
            imaging = camera.create_imaging_service()

            loop = asyncio.get_event_loop()
            settings = await loop.run_in_executor(
                self.executor,
                imaging.GetImagingSettings,
                {"VideoSourceToken": video_source_token}
            )

            result = {
                "brightness": settings.Brightness if hasattr(settings, 'Brightness') else None,
                "contrast": settings.Contrast if hasattr(settings, 'Contrast') else None,
                "saturation": settings.Saturation if hasattr(settings, 'Saturation') else None,
                "sharpness": settings.Sharpness if hasattr(settings, 'Sharpness') else None,
            }

            # Exposure settings
            if hasattr(settings, 'Exposure'):
                result["exposure"] = {
                    "mode": settings.Exposure.Mode,
                    "min_exposure_time": settings.Exposure.MinExposureTime if hasattr(settings.Exposure, 'MinExposureTime') else None,
                    "max_exposure_time": settings.Exposure.MaxExposureTime if hasattr(settings.Exposure, 'MaxExposureTime') else None,
                    "min_gain": settings.Exposure.MinGain if hasattr(settings.Exposure, 'MinGain') else None,
                    "max_gain": settings.Exposure.MaxGain if hasattr(settings.Exposure, 'MaxGain') else None,
                }

            # WDR settings
            if hasattr(settings, 'WideDynamicRange'):
                result["wdr"] = {
                    "mode": settings.WideDynamicRange.Mode,
                    "level": settings.WideDynamicRange.Level if hasattr(settings.WideDynamicRange, 'Level') else None,
                }

            return result

        except Exception as e:
            logger.error(f"Failed to get imaging settings: {e}")
            raise


    async def set_video_encoder_config(
        self,
        camera: ONVIFCamera,
        config_token: str,
        settings: Dict
    ) -> bool:
        """
        Apply video encoder configuration to camera

        Args:
            camera: ONVIFCamera instance
            config_token: Configuration token to modify
            settings: Settings to apply (resolution, fps, bitrate, codec, etc.)

        Returns:
            True if successful

        Raises:
            Exception: If apply fails
        """
        logger.info(f"Applying video encoder configuration (token={config_token})...")

        try:
            media = camera.create_media_service()

            # Get current config
            loop = asyncio.get_event_loop()
            current_config = await loop.run_in_executor(
                self.executor,
                media.GetVideoEncoderConfiguration,
                {"ConfigurationToken": config_token}
            )

            # Modify settings
            if "resolution" in settings:
                res = settings["resolution"]
                if isinstance(res, str) and "x" in res:
                    width, height = map(int, res.split("x"))
                    current_config.Resolution.Width = width
                    current_config.Resolution.Height = height

            if "fps" in settings:
                current_config.RateControl.FrameRateLimit = settings["fps"]

            if "bitrate" in settings:
                # Convert Mbps to Kbps
                bitrate_kbps = int(settings["bitrate"] * 1000)
                current_config.RateControl.BitrateLimit = bitrate_kbps

            if "codec" in settings:
                # Map codec names to ONVIF encoding types
                codec_map = {
                    "H.264": "H264",
                    "H.265": "H265",
                    "MJPEG": "JPEG"
                }
                current_config.Encoding = codec_map.get(settings["codec"], "H264")

            if "keyframe_interval" in settings:
                current_config.RateControl.EncodingInterval = settings["keyframe_interval"]

            # Apply configuration
            await loop.run_in_executor(
                self.executor,
                media.SetVideoEncoderConfiguration,
                {
                    "Configuration": current_config,
                    "ForcePersistence": True
                }
            )

            logger.info(f"Successfully applied video encoder configuration")
            return True

        except Exception as e:
            logger.error(f"Failed to apply encoder config: {e}")
            raise


    async def set_imaging_settings(
        self,
        camera: ONVIFCamera,
        video_source_token: str,
        settings: Dict
    ) -> bool:
        """
        Apply imaging settings to camera

        Args:
            camera: ONVIFCamera instance
            video_source_token: Video source token
            settings: Settings to apply (exposure, WDR, etc.)

        Returns:
            True if successful
        """
        logger.info("Applying imaging settings...")

        try:
            imaging = camera.create_imaging_service()

            # Get current settings
            loop = asyncio.get_event_loop()
            current_settings = await loop.run_in_executor(
                self.executor,
                imaging.GetImagingSettings,
                {"VideoSourceToken": video_source_token}
            )

            # Modify settings
            if "brightness" in settings:
                current_settings.Brightness = settings["brightness"]

            if "contrast" in settings:
                current_settings.Contrast = settings["contrast"]

            if "saturation" in settings:
                current_settings.Saturation = settings["saturation"]

            if "sharpness" in settings:
                current_settings.Sharpness = settings["sharpness"]

            # Apply settings
            await loop.run_in_executor(
                self.executor,
                imaging.SetImagingSettings,
                {
                    "VideoSourceToken": video_source_token,
                    "ImagingSettings": current_settings,
                    "ForcePersistence": True
                }
            )

            logger.info("Successfully applied imaging settings")
            return True

        except Exception as e:
            logger.error(f"Failed to apply imaging settings: {e}")
            raise


    async def get_snapshot_uri(self, camera: ONVIFCamera, profile_token: str) -> str:
        """
        Get snapshot URI from camera

        Args:
            camera: ONVIFCamera instance
            profile_token: Media profile token

        Returns:
            Snapshot URI (HTTP URL)
        """
        logger.info("Getting snapshot URI...")

        try:
            media = camera.create_media_service()

            loop = asyncio.get_event_loop()
            snapshot_uri = await loop.run_in_executor(
                self.executor,
                media.GetSnapshotUri,
                {"ProfileToken": profile_token}
            )

            uri = snapshot_uri.Uri
            logger.info(f"Snapshot URI: {uri}")
            return uri

        except Exception as e:
            logger.error(f"Failed to get snapshot URI: {e}")
            raise


# Utility function for testing
async def test_discovery():
    """Test camera discovery"""
    client = ONVIFClient()
    cameras = await client.discover_cameras(timeout=10)

    print(f"\nDiscovered {len(cameras)} cameras:")
    for cam in cameras:
        print(f"  - {cam['manufacturer']} {cam['model']} at {cam['ip']}:{cam['port']}")

    return cameras


if __name__ == "__main__":
    # Run discovery test
    asyncio.run(test_discovery())
