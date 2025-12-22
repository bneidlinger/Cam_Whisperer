"""
Rhombus Cloud VMS Integration Client

Provides integration with Rhombus Systems cloud platform for:
- Camera discovery via Rhombus API
- Camera settings query and update
- Snapshot retrieval
- Configuration management

Rhombus API Information:
- Base URL: https://api2.rhombussystems.com
- Authentication: API Key header (x-auth-apikey)
- All requests are POST with JSON body
- OpenAPI spec: https://api2.rhombussystems.com/api/openapi/public.json
- API Docs: https://api-docs.rhombus.community/

Rhombus uses PKI infrastructure with signed certificates for enhanced security.
"""

import logging
import asyncio
from typing import Dict, List, Optional, Any
from concurrent.futures import ThreadPoolExecutor
import requests

logger = logging.getLogger(__name__)


class RhombusConnectionError(Exception):
    """Raised when connection to Rhombus API fails"""
    pass


class RhombusAuthenticationError(Exception):
    """Raised when authentication to Rhombus API fails"""
    pass


class RhombusAPIError(Exception):
    """Raised when Rhombus API returns an error"""
    pass


class RhombusClient:
    """
    Client for interacting with Rhombus Cloud VMS API

    Rhombus is a cloud-native security platform with cameras, access control,
    and sensors. Their API uses POST requests with JSON payloads for all operations.

    Features:
    - Camera discovery (list all cameras in organization)
    - Camera configuration query and update
    - Snapshot/media retrieval
    - Camera state monitoring
    """

    BASE_URL = "https://api2.rhombussystems.com"

    def __init__(
        self,
        api_key: str,
        timeout: int = 30
    ):
        """
        Initialize Rhombus client

        Args:
            api_key: Rhombus API key from Console
            timeout: Request timeout in seconds
        """
        self.api_key = api_key
        self.timeout = timeout

        # Session for connection pooling
        self.session = requests.Session()
        self.session.headers.update({
            "x-auth-apikey": api_key,
            "x-auth-scheme": "api-token",
            "Content-Type": "application/json"
        })

        # Thread pool for blocking HTTP calls
        self.executor = ThreadPoolExecutor(max_workers=5)

        logger.info("Initialized Rhombus client")

    def _make_request(
        self,
        method: str,
        payload: Optional[Dict] = None
    ) -> Any:
        """
        Make POST request to Rhombus API (blocking)

        Rhombus API uses POST for all operations with the method
        specified in the endpoint path.

        Args:
            method: API method name (e.g., 'camera/getMinimalCameraStateList')
            payload: JSON request body (optional)

        Returns:
            Response JSON or raises exception
        """
        url = f"{self.BASE_URL}/api/{method}"

        try:
            logger.debug(f"Rhombus API POST {url} payload={payload}")

            response = self.session.post(
                url=url,
                json=payload or {},
                timeout=self.timeout
            )

            # Check for errors
            if response.status_code == 401:
                raise RhombusAuthenticationError("Invalid API key")
            elif response.status_code == 403:
                raise RhombusAuthenticationError("Access forbidden - insufficient permissions")
            elif response.status_code == 404:
                raise RhombusAPIError(f"API method not found: {method}")
            elif response.status_code >= 400:
                raise RhombusAPIError(f"API error: {response.status_code} - {response.text}")

            # Parse response
            if response.content:
                try:
                    return response.json()
                except Exception:
                    return response.text
            else:
                return None

        except requests.exceptions.ConnectTimeout:
            raise RhombusConnectionError(f"Connection timeout to Rhombus API")
        except requests.exceptions.ConnectionError:
            raise RhombusConnectionError("Cannot connect to Rhombus API")
        except Exception as e:
            if isinstance(e, (RhombusConnectionError, RhombusAuthenticationError, RhombusAPIError)):
                raise
            logger.error(f"Rhombus API request failed: {e}")
            raise RhombusAPIError(f"Request failed: {e}")

    async def test_connection(self) -> bool:
        """
        Test connection to Rhombus API

        Returns:
            True if connection successful, False otherwise
        """
        try:
            loop = asyncio.get_event_loop()

            # Try to get camera list
            result = await loop.run_in_executor(
                self.executor,
                lambda: self._make_request("camera/getMinimalCameraStateList", {})
            )

            logger.info("Rhombus connection test successful")
            return True

        except Exception as e:
            logger.warning(f"Rhombus connection test failed: {e}")
            return False

    async def get_cameras(self) -> List[Dict]:
        """
        Get list of all cameras in the organization

        Returns:
            List of camera dictionaries with details
        """
        logger.info("Fetching cameras from Rhombus...")

        try:
            loop = asyncio.get_event_loop()

            result = await loop.run_in_executor(
                self.executor,
                lambda: self._make_request("camera/getMinimalCameraStateList", {})
            )

            cameras = []
            if isinstance(result, dict):
                # Response typically has a 'cameraStates' or similar field
                camera_list = result.get("cameraStates", result.get("cameras", []))
                if isinstance(camera_list, list):
                    cameras = camera_list
                elif isinstance(result, list):
                    cameras = result

            # Normalize camera data
            normalized_cameras = []
            for cam in cameras:
                normalized = self._normalize_camera_data(cam)
                normalized_cameras.append(normalized)

            logger.info(f"Found {len(normalized_cameras)} cameras in Rhombus")
            return normalized_cameras

        except Exception as e:
            logger.error(f"Failed to get cameras from Rhombus: {e}")
            raise

    def _normalize_camera_data(self, cam: Dict) -> Dict:
        """
        Normalize Rhombus camera data to PlatoniCam format

        Args:
            cam: Raw camera data from Rhombus API

        Returns:
            Normalized camera dictionary
        """
        # Extract camera ID - Rhombus uses 'uuid' or 'deviceUuid'
        camera_id = cam.get("uuid", cam.get("deviceUuid", cam.get("cameraUuid", "")))

        # Extract name
        name = cam.get("name", cam.get("deviceName", "Unknown Camera"))

        # Extract status
        is_online = cam.get("online", cam.get("isOnline", True))
        status = "online" if is_online else "offline"

        return {
            "id": camera_id,
            "name": name,
            "ip": cam.get("lanIpAddress", cam.get("ipAddress", "")),
            "vendor": "Rhombus",
            "model": cam.get("model", cam.get("deviceModel", "Unknown")),
            "firmware": cam.get("firmwareVersion", ""),
            "status": status,
            "enabled": cam.get("enabled", True),
            "location": cam.get("location", cam.get("locationName", "")),
            "serial": cam.get("serialNumber", ""),
            "mac": cam.get("macAddress", ""),
            "cloudManaged": True,
            "vmsId": camera_id,
            "vmsSystem": "rhombus",
            "rawData": cam
        }

    async def get_camera_details(self, camera_uuid: str) -> Dict:
        """
        Get detailed information for a specific camera

        Args:
            camera_uuid: Rhombus camera UUID

        Returns:
            Camera details dictionary
        """
        logger.info(f"Fetching details for Rhombus camera {camera_uuid}...")

        try:
            loop = asyncio.get_event_loop()

            result = await loop.run_in_executor(
                self.executor,
                lambda: self._make_request("camera/getCameraDetails", {"cameraUuid": camera_uuid})
            )

            if isinstance(result, dict):
                # Get camera from response
                camera = result.get("camera", result)
                return self._normalize_camera_data(camera)

            raise RhombusAPIError(f"Camera {camera_uuid} not found")

        except Exception as e:
            logger.error(f"Failed to get camera details: {e}")
            raise

    async def get_camera_config(self, camera_uuid: str) -> Dict:
        """
        Get current camera configuration

        Args:
            camera_uuid: Rhombus camera UUID

        Returns:
            Camera configuration dictionary
        """
        logger.info(f"Fetching config for Rhombus camera {camera_uuid}...")

        try:
            loop = asyncio.get_event_loop()

            result = await loop.run_in_executor(
                self.executor,
                lambda: self._make_request("camera/getCameraConfig", {"cameraUuid": camera_uuid})
            )

            if isinstance(result, dict):
                return self._normalize_config(result, camera_uuid)

            raise RhombusAPIError(f"Could not get config for camera {camera_uuid}")

        except Exception as e:
            logger.error(f"Failed to get camera config: {e}")
            raise

    def _normalize_config(self, config: Dict, camera_uuid: str) -> Dict:
        """
        Normalize Rhombus camera config to PlatoniCam format

        Args:
            config: Raw config from Rhombus API
            camera_uuid: Camera UUID

        Returns:
            Normalized config dictionary
        """
        # Extract config from response
        cam_config = config.get("config", config.get("cameraConfig", config))

        return {
            "stream": {
                "resolution": cam_config.get("resolution", "Unknown"),
                "codec": cam_config.get("videoCodec", "H.264"),
                "fps": cam_config.get("frameRate", cam_config.get("fps", 30)),
                "bitrateMbps": cam_config.get("bitrate", None),
                "quality": cam_config.get("quality", cam_config.get("videoQuality", None))
            },
            "exposure": {
                "mode": cam_config.get("exposureMode", "Auto"),
                "wdr": cam_config.get("wdrEnabled", cam_config.get("wdr", "Auto"))
            },
            "lowLight": {
                "irMode": cam_config.get("irMode", cam_config.get("infraredMode", "Auto")),
                "sensitivity": cam_config.get("lowLightSensitivity", "Medium")
            },
            "image": {
                "brightness": cam_config.get("brightness", 50),
                "contrast": cam_config.get("contrast", 50),
                "saturation": cam_config.get("saturation", 50),
                "sharpness": cam_config.get("sharpness", 50),
                "rotation": cam_config.get("rotation", 0),
                "mirror": cam_config.get("mirror", False),
                "flip": cam_config.get("flip", False)
            },
            "recording": {
                "enabled": cam_config.get("recordingEnabled", True),
                "retentionDays": cam_config.get("retentionDays", 30),
                "mode": cam_config.get("recordingMode", "continuous")
            },
            "cloudManaged": True,
            "vmsSystem": "rhombus",
            "cameraUuid": camera_uuid,
            "rawConfig": cam_config
        }

    async def update_camera_config(
        self,
        camera_uuid: str,
        config: Dict
    ) -> bool:
        """
        Update camera configuration

        Args:
            camera_uuid: Rhombus camera UUID
            config: Configuration updates to apply

        Returns:
            True if successful, False otherwise
        """
        logger.info(f"Updating config for Rhombus camera {camera_uuid}...")

        try:
            loop = asyncio.get_event_loop()

            # Build update payload
            payload = {
                "cameraUuid": camera_uuid,
                "config": self._build_rhombus_config(config)
            }

            result = await loop.run_in_executor(
                self.executor,
                lambda: self._make_request("camera/updateCameraConfig", payload)
            )

            logger.info(f"Successfully updated config for camera {camera_uuid}")
            return True

        except Exception as e:
            logger.error(f"Failed to update camera config: {e}")
            return False

    def _build_rhombus_config(self, config: Dict) -> Dict:
        """
        Convert PlatoniCam config format to Rhombus API format

        Args:
            config: PlatoniCam format configuration

        Returns:
            Rhombus API format configuration
        """
        rhombus_config = {}

        # Stream settings
        stream = config.get("stream", {})
        if stream.get("resolution"):
            rhombus_config["resolution"] = stream["resolution"]
        if stream.get("fps"):
            rhombus_config["frameRate"] = stream["fps"]
        if stream.get("codec"):
            rhombus_config["videoCodec"] = stream["codec"]
        if stream.get("quality"):
            rhombus_config["videoQuality"] = stream["quality"]

        # Image settings
        image = config.get("image", {})
        if image.get("brightness") is not None:
            rhombus_config["brightness"] = image["brightness"]
        if image.get("contrast") is not None:
            rhombus_config["contrast"] = image["contrast"]
        if image.get("saturation") is not None:
            rhombus_config["saturation"] = image["saturation"]
        if image.get("sharpness") is not None:
            rhombus_config["sharpness"] = image["sharpness"]
        if image.get("rotation") is not None:
            rhombus_config["rotation"] = image["rotation"]
        if image.get("mirror") is not None:
            rhombus_config["mirror"] = image["mirror"]

        # Low light settings
        low_light = config.get("lowLight", {})
        if low_light.get("irMode"):
            rhombus_config["infraredMode"] = low_light["irMode"]

        # Exposure settings
        exposure = config.get("exposure", {})
        if exposure.get("wdr"):
            rhombus_config["wdrEnabled"] = exposure["wdr"] not in ("Off", "off", False)

        return rhombus_config

    async def get_camera_state(self, camera_uuid: str) -> Dict:
        """
        Get current camera state (online/offline, recording, etc.)

        Args:
            camera_uuid: Rhombus camera UUID

        Returns:
            Camera state dictionary
        """
        logger.info(f"Fetching state for Rhombus camera {camera_uuid}...")

        try:
            loop = asyncio.get_event_loop()

            result = await loop.run_in_executor(
                self.executor,
                lambda: self._make_request("camera/getCurrentCameraState", {"cameraUuid": camera_uuid})
            )

            if isinstance(result, dict):
                state = result.get("cameraState", result)
                return {
                    "online": state.get("online", False),
                    "recording": state.get("recording", False),
                    "streaming": state.get("streaming", False),
                    "lastSeen": state.get("lastSeen", state.get("lastSeenTimestamp")),
                    "uptime": state.get("uptime"),
                    "alerts": state.get("alerts", [])
                }

            return {"online": False, "error": "Could not get state"}

        except Exception as e:
            logger.error(f"Failed to get camera state: {e}")
            return {"online": False, "error": str(e)}

    async def get_snapshot(self, camera_uuid: str) -> Optional[bytes]:
        """
        Get current snapshot from camera

        Args:
            camera_uuid: Rhombus camera UUID

        Returns:
            JPEG image bytes or None if failed
        """
        logger.info(f"Requesting snapshot for Rhombus camera {camera_uuid}...")

        try:
            loop = asyncio.get_event_loop()

            # Get media URIs
            result = await loop.run_in_executor(
                self.executor,
                lambda: self._make_request("camera/getCameraMediaUris", {"cameraUuid": camera_uuid})
            )

            if isinstance(result, dict):
                # Get thumbnail or snapshot URL
                thumbnail_url = result.get("thumbnailUri", result.get("snapshotUri"))

                if thumbnail_url:
                    # Fetch the actual image
                    response = await loop.run_in_executor(
                        self.executor,
                        lambda: self.session.get(thumbnail_url, timeout=10)
                    )

                    if response.status_code == 200:
                        logger.info(f"Got snapshot for camera {camera_uuid} ({len(response.content)} bytes)")
                        return response.content

            logger.warning(f"Could not get snapshot for camera {camera_uuid}")
            return None

        except Exception as e:
            logger.error(f"Failed to get snapshot: {e}")
            return None

    async def get_camera_settings(self, camera_uuid: str) -> Dict:
        """
        Get current camera settings (alias for get_camera_config)

        Args:
            camera_uuid: Rhombus camera UUID

        Returns:
            Camera settings dictionary in PlatoniCam format
        """
        return await self.get_camera_config(camera_uuid)

    def close(self):
        """Close connection and cleanup resources"""
        self.session.close()
        self.executor.shutdown(wait=False)
        logger.info("Rhombus client closed")


# Example usage
if __name__ == "__main__":
    import asyncio

    async def test_rhombus_client():
        """Test Rhombus client"""

        # Initialize client
        client = RhombusClient(
            api_key="your-api-key-here"  # Replace with actual API key
        )

        try:
            # Test connection
            print("Testing connection...")
            connected = await client.test_connection()
            print(f"Connected: {connected}")

            if not connected:
                print("Cannot connect to Rhombus API")
                return

            # Get cameras
            print("\nGetting cameras...")
            cameras = await client.get_cameras()
            print(f"Found {len(cameras)} cameras")

            for cam in cameras[:5]:  # Print first 5
                print(f"  - {cam['name']} ({cam['model']}) at {cam['ip']}")

            # Get config for first camera
            if cameras:
                camera_uuid = cameras[0]["id"]
                print(f"\nGetting config for camera {camera_uuid}...")
                config = await client.get_camera_config(camera_uuid)
                print(f"Config: {config}")

        finally:
            client.close()

    # Run test
    asyncio.run(test_rhombus_client())
