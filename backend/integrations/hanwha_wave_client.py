"""
Hanwha WAVE VMS Integration Client

Provides integration with Hanwha WAVE (formerly Wisenet WAVE) VMS for:
- Camera discovery via WAVE API
- Camera settings query
- Camera settings application
- Health monitoring

WAVE API Information:
- Default Port: 7001 (HTTPS)
- Authentication: Digest authentication or session tokens
- API Endpoint: https://<server-ip>:7001/api/...
- Documentation: http://<server-ip>:7001/#/api-tool (when WAVE Server is running)

References:
- https://support.hanwhavisionamerica.com/hc/en-us/articles/1260806781909-WAVE-Server-HTTP-REST-API
- https://support.hanwhavisionamerica.com/hc/en-us/articles/115013501208-WAVE-SDK-API
"""

import logging
import asyncio
from typing import Dict, List, Optional, Any
from concurrent.futures import ThreadPoolExecutor
import requests
from requests.auth import HTTPDigestAuth
import urllib3

# Disable SSL warnings for self-signed certificates (WAVE uses self-signed by default)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger(__name__)


class WAVEConnectionError(Exception):
    """Raised when connection to WAVE server fails"""
    pass


class WAVEAuthenticationError(Exception):
    """Raised when authentication to WAVE server fails"""
    pass


class WAVEAPIError(Exception):
    """Raised when WAVE API returns an error"""
    pass


class HanwhaWAVEClient:
    """
    Client for interacting with Hanwha WAVE VMS

    WAVE VMS provides a REST API for managing cameras, users, servers,
    and other system resources.

    Features:
    - Camera discovery (list all cameras in WAVE system)
    - Camera settings query (get current configuration)
    - Camera settings apply (update configuration)
    - Health monitoring (get camera status, snapshots)
    """

    def __init__(
        self,
        server_ip: str,
        port: int = 7001,
        username: str = "admin",
        password: str = "",
        use_https: bool = True,
        verify_ssl: bool = False
    ):
        """
        Initialize WAVE client

        Args:
            server_ip: WAVE server IP address
            port: WAVE API port (default: 7001)
            username: WAVE username
            password: WAVE password
            use_https: Use HTTPS (default: True, recommended)
            verify_ssl: Verify SSL certificates (default: False, WAVE uses self-signed)
        """
        self.server_ip = server_ip
        self.port = port
        self.username = username
        self.password = password
        self.use_https = use_https
        self.verify_ssl = verify_ssl

        # Build base URL
        protocol = "https" if use_https else "http"
        self.base_url = f"{protocol}://{server_ip}:{port}"

        # Session for connection pooling
        self.session = requests.Session()
        self.session.auth = HTTPDigestAuth(username, password)
        self.session.verify = verify_ssl

        # Thread pool for blocking HTTP calls
        self.executor = ThreadPoolExecutor(max_workers=5)

        logger.info(f"Initialized WAVE client for {self.base_url}")


    def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict] = None,
        json_data: Optional[Dict] = None,
        timeout: int = 10
    ) -> Any:
        """
        Make HTTP request to WAVE API (blocking)

        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint (e.g., '/api/v1/devices')
            params: URL query parameters
            json_data: JSON request body
            timeout: Request timeout in seconds

        Returns:
            Response JSON or raises exception
        """
        url = f"{self.base_url}{endpoint}"

        try:
            logger.debug(f"WAVE API {method} {url} params={params}")

            response = self.session.request(
                method=method,
                url=url,
                params=params,
                json=json_data,
                timeout=timeout
            )

            # Check for errors
            if response.status_code == 401:
                raise WAVEAuthenticationError("Authentication failed - invalid credentials")
            elif response.status_code == 403:
                raise WAVEAuthenticationError("Access forbidden - insufficient permissions")
            elif response.status_code >= 400:
                raise WAVEAPIError(f"API error: {response.status_code} - {response.text}")

            # Parse response
            if response.content:
                try:
                    return response.json()
                except Exception:
                    return response.text
            else:
                return None

        except requests.exceptions.ConnectTimeout:
            raise WAVEConnectionError(f"Connection timeout to {url}")
        except requests.exceptions.ConnectionError:
            raise WAVEConnectionError(f"Cannot connect to WAVE server at {url}")
        except Exception as e:
            if isinstance(e, (WAVEConnectionError, WAVEAuthenticationError, WAVEAPIError)):
                raise
            logger.error(f"WAVE API request failed: {e}")
            raise WAVEAPIError(f"Request failed: {e}")


    async def test_connection(self) -> bool:
        """
        Test connection to WAVE server

        Returns:
            True if connection successful, False otherwise
        """
        try:
            loop = asyncio.get_event_loop()

            # Try to get server info
            result = await loop.run_in_executor(
                self.executor,
                self._make_request,
                "GET",
                "/api/v1/servers"
            )

            logger.info(f"WAVE connection test successful to {self.base_url}")
            return True

        except Exception as e:
            logger.warning(f"WAVE connection test failed: {e}")
            return False


    async def get_cameras(self) -> List[Dict]:
        """
        Get list of all cameras in WAVE system

        Returns:
            List of camera dictionaries with details
        """
        logger.info(f"Fetching cameras from WAVE at {self.base_url}")

        try:
            loop = asyncio.get_event_loop()

            # WAVE API endpoint for cameras (may vary by version)
            # Try multiple possible endpoints
            cameras = []

            # Try v1 API first
            try:
                result = await loop.run_in_executor(
                    self.executor,
                    self._make_request,
                    "GET",
                    "/api/v1/devices",
                    {"type": "camera"}
                )

                if isinstance(result, list):
                    cameras = result
                elif isinstance(result, dict) and "devices" in result:
                    cameras = result["devices"]

            except Exception as e:
                logger.debug(f"v1 API failed, trying legacy endpoint: {e}")

                # Try legacy EC2 endpoint
                result = await loop.run_in_executor(
                    self.executor,
                    self._make_request,
                    "GET",
                    "/ec2/getCamerasEx"
                )

                if isinstance(result, list):
                    cameras = result
                elif isinstance(result, dict) and "cameras" in result:
                    cameras = result["cameras"]

            # Normalize camera data
            normalized_cameras = []
            for cam in cameras:
                normalized = self._normalize_camera_data(cam)
                normalized_cameras.append(normalized)

            logger.info(f"Found {len(normalized_cameras)} cameras in WAVE")
            return normalized_cameras

        except Exception as e:
            logger.error(f"Failed to get cameras from WAVE: {e}")
            raise


    def _normalize_camera_data(self, cam: Dict) -> Dict:
        """
        Normalize WAVE camera data to PlatoniCam format

        Args:
            cam: Raw camera data from WAVE API

        Returns:
            Normalized camera dictionary
        """
        # WAVE camera objects have various fields depending on version
        # Common fields: id, name, url, vendor, model, status, etc.

        return {
            "id": cam.get("id") or cam.get("physicalId", ""),
            "name": cam.get("name", "Unknown Camera"),
            "ip": self._extract_ip_from_url(cam.get("url", "")),
            "vendor": cam.get("vendor", "Unknown"),
            "model": cam.get("model", "Unknown"),
            "status": cam.get("status", "unknown"),
            "enabled": cam.get("enabled", True),
            "recording": cam.get("isRecording", False),
            "url": cam.get("url", ""),
            "vmsId": cam.get("id", ""),
            "vmsSystem": "hanwha-wave",
            "rawData": cam  # Keep original data for reference
        }


    def _extract_ip_from_url(self, url: str) -> str:
        """Extract IP address from RTSP/HTTP URL"""
        if not url:
            return ""

        try:
            # URL format: rtsp://admin:pass@192.168.1.100:554/...
            # or http://192.168.1.100/...
            if "@" in url:
                # Has credentials
                parts = url.split("@")
                host_part = parts[1].split("/")[0]
            else:
                # No credentials
                parts = url.replace("://", "|").split("|")
                if len(parts) > 1:
                    host_part = parts[1].split("/")[0]
                else:
                    return ""

            # Extract IP (remove port if present)
            ip = host_part.split(":")[0]
            return ip

        except Exception:
            return ""


    async def get_camera_settings(self, camera_id: str) -> Dict:
        """
        Get current settings for a specific camera

        Args:
            camera_id: WAVE camera ID

        Returns:
            Camera settings dictionary
        """
        logger.info(f"Fetching settings for camera {camera_id} from WAVE")

        try:
            loop = asyncio.get_event_loop()

            # Get camera details
            result = await loop.run_in_executor(
                self.executor,
                self._make_request,
                "GET",
                f"/api/v1/devices/{camera_id}"
            )

            if not result:
                raise WAVEAPIError(f"Camera {camera_id} not found")

            # Extract settings from camera object
            settings = self._extract_camera_settings(result)

            logger.info(f"Retrieved settings for camera {camera_id}")
            return settings

        except Exception as e:
            logger.error(f"Failed to get camera settings: {e}")
            raise


    def _extract_camera_settings(self, camera: Dict) -> Dict:
        """
        Extract camera settings from WAVE camera object

        Args:
            camera: Raw camera object from WAVE

        Returns:
            Settings in PlatoniCam format
        """
        # WAVE stores settings differently than ONVIF
        # Settings may be in: streamSettings, advanced, recording, etc.

        stream_settings = camera.get("streamSettings", {})
        recording_settings = camera.get("recordingSettings", {})

        # Build PlatoniCam format settings
        return {
            "stream": {
                "resolution": stream_settings.get("resolution", "1920x1080"),
                "codec": stream_settings.get("codec", "H.264"),
                "fps": stream_settings.get("fps", 30),
                "bitrateMbps": stream_settings.get("bitrate", 6000) / 1000,  # Convert kbps to Mbps
                "keyframeInterval": stream_settings.get("keyFrameInterval", 60),
                "cbr": stream_settings.get("bitrateMode") == "CBR"
            },
            "recording": {
                "mode": recording_settings.get("mode", "always"),
                "quality": recording_settings.get("quality", "high"),
                "preRecordSeconds": recording_settings.get("preRecording", 5)
            },
            "exposure": {
                # WAVE may not expose these directly (handled by camera)
                "shutter": "auto",
                "iris": "auto",
                "gainLimit": "medium",
                "wdr": "auto"
            },
            "lowLight": {
                "irMode": "auto",
                "irIntensity": "auto",
                "noiseReduction": "medium"
            }
        }


    async def apply_camera_settings(
        self,
        camera_id: str,
        settings: Dict
    ) -> bool:
        """
        Apply settings to a camera via WAVE API

        Args:
            camera_id: WAVE camera ID
            settings: Settings to apply (PlatoniCam format)

        Returns:
            True if successful, False otherwise
        """
        logger.info(f"Applying settings to camera {camera_id} via WAVE")

        try:
            loop = asyncio.get_event_loop()

            # Convert PlatoniCam format to WAVE format
            wave_settings = self._convert_to_wave_format(settings)

            # Apply settings via WAVE API
            result = await loop.run_in_executor(
                self.executor,
                self._make_request,
                "PATCH",
                f"/api/v1/devices/{camera_id}",
                None,
                wave_settings
            )

            logger.info(f"Successfully applied settings to camera {camera_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to apply settings: {e}")
            return False


    def _convert_to_wave_format(self, settings: Dict) -> Dict:
        """
        Convert PlatoniCam settings format to WAVE API format

        Args:
            settings: PlatoniCam format settings

        Returns:
            WAVE API format settings
        """
        stream = settings.get("stream", {})
        recording = settings.get("recording", {})

        wave_settings = {
            "streamSettings": {
                "resolution": stream.get("resolution", "1920x1080"),
                "codec": stream.get("codec", "H.264"),
                "fps": stream.get("fps", 30),
                "bitrate": int(stream.get("bitrateMbps", 6) * 1000),  # Convert Mbps to kbps
                "keyFrameInterval": stream.get("keyframeInterval", 60),
                "bitrateMode": "CBR" if stream.get("cbr", True) else "VBR"
            },
            "recordingSettings": {
                "mode": recording.get("mode", "always"),
                "quality": recording.get("quality", "high"),
                "preRecording": recording.get("preRecordSeconds", 5)
            }
        }

        return wave_settings


    async def get_snapshot(self, camera_id: str) -> Optional[bytes]:
        """
        Get snapshot image from camera via WAVE

        Args:
            camera_id: WAVE camera ID

        Returns:
            JPEG image bytes or None if failed
        """
        logger.info(f"Requesting snapshot for camera {camera_id} from WAVE")

        try:
            loop = asyncio.get_event_loop()

            # WAVE snapshot endpoint
            endpoint = f"/api/v1/devices/{camera_id}/image"

            # Make request
            response = await loop.run_in_executor(
                self.executor,
                lambda: self.session.get(
                    f"{self.base_url}{endpoint}",
                    timeout=10
                )
            )

            if response.status_code == 200:
                logger.info(f"Got snapshot for camera {camera_id} ({len(response.content)} bytes)")
                return response.content
            else:
                logger.warning(f"Snapshot request failed: {response.status_code}")
                return None

        except Exception as e:
            logger.error(f"Failed to get snapshot: {e}")
            return None


    async def get_server_info(self) -> Dict:
        """
        Get WAVE server information

        Returns:
            Server info dictionary
        """
        logger.info(f"Fetching WAVE server info from {self.base_url}")

        try:
            loop = asyncio.get_event_loop()

            result = await loop.run_in_executor(
                self.executor,
                self._make_request,
                "GET",
                "/api/v1/servers"
            )

            if isinstance(result, list) and len(result) > 0:
                server = result[0]
            elif isinstance(result, dict):
                server = result
            else:
                server = {}

            return {
                "name": server.get("name", "Unknown"),
                "version": server.get("version", "Unknown"),
                "id": server.get("id", ""),
                "status": server.get("status", "unknown")
            }

        except Exception as e:
            logger.error(f"Failed to get server info: {e}")
            return {
                "name": "Unknown",
                "version": "Unknown",
                "error": str(e)
            }


    def close(self):
        """Close connection and cleanup resources"""
        self.session.close()
        self.executor.shutdown(wait=False)
        logger.info("WAVE client closed")

    @staticmethod
    def integration_profile() -> Dict[str, Any]:
        """
        Describe the Hanwha WAVE integration surface for the app.

        Returns:
            Dict defining available tooling and optimization touch points so
            the UI can light up the right controls for WAVE deployments.
        """
        return {
            "id": "hanwha-wave",
            "name": "Hanwha Vision WAVE",
            "deployment": "on-prem",
            "auth": "Digest auth or session token",
            "defaultEndpoints": ["https://<server-ip>:7001/api"],
            "tools": {
                "discovery": True,
                "snapshots": True,
                "settingsRead": True,
                "settingsWrite": True,
                "eventBridge": True,
            },
            "optimizations": {
                "streamTuning": True,
                "recordingPolicies": True,
                "analytics": False,
                "cloudExports": False,
                "notes": "Full config read/write enables bitrate/fps tuning and recording policy automation.",
            },
            "status": {"available": True, "reason": None},
        }


# Example usage
if __name__ == "__main__":
    import asyncio

    async def test_wave_client():
        """Test WAVE client"""

        # Initialize client
        client = HanwhaWAVEClient(
            server_ip="192.168.1.100",  # Replace with your WAVE server IP
            username="admin",
            password="admin"
        )

        try:
            # Test connection
            print("Testing connection...")
            connected = await client.test_connection()
            print(f"Connected: {connected}")

            if not connected:
                print("Cannot connect to WAVE server")
                return

            # Get server info
            print("\nGetting server info...")
            server_info = await client.get_server_info()
            print(f"Server: {server_info}")

            # Get cameras
            print("\nGetting cameras...")
            cameras = await client.get_cameras()
            print(f"Found {len(cameras)} cameras")

            for cam in cameras:
                print(f"  - {cam['name']} ({cam['vendor']} {cam['model']}) at {cam['ip']}")

            # Get settings for first camera
            if cameras:
                camera_id = cameras[0]["id"]
                print(f"\nGetting settings for camera {camera_id}...")
                settings = await client.get_camera_settings(camera_id)
                print(f"Settings: {settings}")

        finally:
            client.close()

    # Run test
    asyncio.run(test_wave_client())
