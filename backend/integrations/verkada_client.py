"""
Verkada Cloud VMS Integration Client

Provides integration with Verkada Command platform for:
- Camera discovery via Verkada API
- Camera settings query
- Snapshot retrieval
- Footage streaming links

Verkada API Information:
- Base URL: https://api.verkada.com (US) or https://api.eu.verkada.com (EU)
- Authentication: API Key + short-lived Token (30 min validity)
- API Docs: https://apidocs.verkada.com/reference/introduction

Note: Verkada cameras are cloud-managed. Most settings are configured through
the Verkada Command dashboard. This client focuses on read operations and
metadata retrieval for optimization analysis.
"""

import logging
import asyncio
import time
from typing import Dict, List, Optional, Any
from concurrent.futures import ThreadPoolExecutor
import requests

logger = logging.getLogger(__name__)


class VerkadaConnectionError(Exception):
    """Raised when connection to Verkada API fails"""
    pass


class VerkadaAuthenticationError(Exception):
    """Raised when authentication to Verkada API fails"""
    pass


class VerkadaAPIError(Exception):
    """Raised when Verkada API returns an error"""
    pass


class VerkadaClient:
    """
    Client for interacting with Verkada Command API

    Verkada is a cloud-native VMS with cameras that stream directly to
    Verkada's cloud infrastructure. Settings are primarily managed through
    their Command dashboard.

    Features:
    - Camera discovery (list all cameras in organization)
    - Camera info query (get camera details and status)
    - Snapshot retrieval (get current camera thumbnail)
    - Footage link generation (get HLS streaming URLs)
    """

    # Verkada API regions
    REGIONS = {
        "us": "https://api.verkada.com",
        "eu": "https://api.eu.verkada.com"
    }

    def __init__(
        self,
        api_key: str,
        org_id: Optional[str] = None,
        region: str = "us",
        token_refresh_margin: int = 300  # Refresh 5 min before expiry
    ):
        """
        Initialize Verkada client

        Args:
            api_key: Verkada API key from Command dashboard
            org_id: Organization ID (optional, for multi-org accounts)
            region: API region ("us" or "eu")
            token_refresh_margin: Seconds before token expiry to refresh
        """
        self.api_key = api_key
        self.org_id = org_id
        self.region = region
        self.token_refresh_margin = token_refresh_margin

        # Validate region
        if region not in self.REGIONS:
            raise ValueError(f"Invalid region '{region}'. Must be one of: {list(self.REGIONS.keys())}")

        self.base_url = self.REGIONS[region]

        # Token management
        self._token: Optional[str] = None
        self._token_expires_at: float = 0

        # Session for connection pooling
        self.session = requests.Session()

        # Thread pool for blocking HTTP calls
        self.executor = ThreadPoolExecutor(max_workers=5)

        logger.info(f"Initialized Verkada client for region: {region}")

    def _get_token(self) -> str:
        """
        Get a valid API token, refreshing if necessary

        Verkada uses a two-step auth:
        1. API Key (persistent) -> Token endpoint
        2. Token (30 min) -> All other endpoints

        Returns:
            Valid API token
        """
        current_time = time.time()

        # Check if we have a valid token
        if self._token and current_time < (self._token_expires_at - self.token_refresh_margin):
            return self._token

        logger.info("Fetching new Verkada API token...")

        try:
            response = self.session.post(
                f"{self.base_url}/token",
                headers={"x-api-key": self.api_key},
                timeout=10
            )

            if response.status_code == 401:
                raise VerkadaAuthenticationError("Invalid API key")
            elif response.status_code == 403:
                raise VerkadaAuthenticationError("API key does not have required permissions")
            elif response.status_code != 200:
                raise VerkadaAPIError(f"Token request failed: {response.status_code} - {response.text}")

            data = response.json()
            self._token = data.get("token")

            if not self._token:
                raise VerkadaAPIError("No token in response")

            # Token is valid for 30 minutes
            self._token_expires_at = current_time + (30 * 60)

            logger.info("Successfully obtained Verkada API token")
            return self._token

        except requests.exceptions.RequestException as e:
            raise VerkadaConnectionError(f"Failed to connect to Verkada API: {e}")

    def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict] = None,
        json_data: Optional[Dict] = None,
        timeout: int = 30
    ) -> Any:
        """
        Make authenticated HTTP request to Verkada API (blocking)

        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint (e.g., '/cameras/v1/devices')
            params: URL query parameters
            json_data: JSON request body
            timeout: Request timeout in seconds

        Returns:
            Response JSON or raises exception
        """
        token = self._get_token()
        url = f"{self.base_url}{endpoint}"

        try:
            logger.debug(f"Verkada API {method} {url} params={params}")

            response = self.session.request(
                method=method,
                url=url,
                params=params,
                json=json_data,
                headers={"x-verkada-auth": token},
                timeout=timeout
            )

            # Check for errors
            if response.status_code == 401:
                # Token might have expired, clear and retry once
                self._token = None
                token = self._get_token()
                response = self.session.request(
                    method=method,
                    url=url,
                    params=params,
                    json=json_data,
                    headers={"x-verkada-auth": token},
                    timeout=timeout
                )
                if response.status_code == 401:
                    raise VerkadaAuthenticationError("Authentication failed after token refresh")

            if response.status_code == 403:
                raise VerkadaAuthenticationError("Access forbidden - insufficient permissions")
            elif response.status_code == 404:
                raise VerkadaAPIError(f"Resource not found: {endpoint}")
            elif response.status_code >= 400:
                raise VerkadaAPIError(f"API error: {response.status_code} - {response.text}")

            # Parse response
            if response.content:
                try:
                    return response.json()
                except Exception:
                    return response.content
            else:
                return None

        except requests.exceptions.ConnectTimeout:
            raise VerkadaConnectionError(f"Connection timeout to {url}")
        except requests.exceptions.ConnectionError:
            raise VerkadaConnectionError(f"Cannot connect to Verkada API at {url}")
        except Exception as e:
            if isinstance(e, (VerkadaConnectionError, VerkadaAuthenticationError, VerkadaAPIError)):
                raise
            logger.error(f"Verkada API request failed: {e}")
            raise VerkadaAPIError(f"Request failed: {e}")

    async def test_connection(self) -> bool:
        """
        Test connection to Verkada API

        Returns:
            True if connection successful, False otherwise
        """
        try:
            loop = asyncio.get_event_loop()

            # Try to get cameras with limit 1
            result = await loop.run_in_executor(
                self.executor,
                lambda: self._make_request("GET", "/cameras/v1/devices", {"page_size": 1})
            )

            logger.info(f"Verkada connection test successful")
            return True

        except Exception as e:
            logger.warning(f"Verkada connection test failed: {e}")
            return False

    async def get_cameras(self, page_size: int = 100) -> List[Dict]:
        """
        Get list of all cameras in the organization

        Args:
            page_size: Number of cameras per page (max 100)

        Returns:
            List of camera dictionaries with details
        """
        logger.info("Fetching cameras from Verkada...")

        try:
            loop = asyncio.get_event_loop()
            all_cameras = []
            next_page_token = None

            while True:
                params = {"page_size": min(page_size, 100)}
                if next_page_token:
                    params["page_token"] = next_page_token

                result = await loop.run_in_executor(
                    self.executor,
                    lambda p=params: self._make_request("GET", "/cameras/v1/devices", p)
                )

                if isinstance(result, dict):
                    cameras = result.get("cameras", [])
                    all_cameras.extend(cameras)

                    # Check for pagination
                    next_page_token = result.get("next_page_token")
                    if not next_page_token:
                        break
                else:
                    break

            # Normalize camera data
            normalized_cameras = []
            for cam in all_cameras:
                normalized = self._normalize_camera_data(cam)
                normalized_cameras.append(normalized)

            logger.info(f"Found {len(normalized_cameras)} cameras in Verkada")
            return normalized_cameras

        except Exception as e:
            logger.error(f"Failed to get cameras from Verkada: {e}")
            raise

    def _normalize_camera_data(self, cam: Dict) -> Dict:
        """
        Normalize Verkada camera data to PlatoniCam format

        Args:
            cam: Raw camera data from Verkada API

        Returns:
            Normalized camera dictionary
        """
        # Verkada camera fields
        return {
            "id": cam.get("camera_id", ""),
            "name": cam.get("name", "Unknown Camera"),
            "ip": cam.get("local_ip", ""),
            "vendor": "Verkada",
            "model": cam.get("model", "Unknown"),
            "firmware": cam.get("firmware", ""),
            "status": "online" if cam.get("is_online") else "offline",
            "enabled": cam.get("is_enabled", True),
            "location": cam.get("location", ""),
            "site": cam.get("site", ""),
            "serial": cam.get("serial", ""),
            "mac": cam.get("mac", ""),
            "cloudManaged": True,
            "vmsId": cam.get("camera_id", ""),
            "vmsSystem": "verkada",
            "rawData": cam
        }

    async def get_camera_info(self, camera_id: str) -> Dict:
        """
        Get detailed information for a specific camera

        Args:
            camera_id: Verkada camera ID

        Returns:
            Camera info dictionary
        """
        logger.info(f"Fetching info for Verkada camera {camera_id}...")

        try:
            loop = asyncio.get_event_loop()

            result = await loop.run_in_executor(
                self.executor,
                lambda: self._make_request(
                    "GET",
                    "/cameras/v1/devices",
                    {"camera_id": camera_id}
                )
            )

            if isinstance(result, dict):
                cameras = result.get("cameras", [])
                if cameras:
                    return self._normalize_camera_data(cameras[0])

            raise VerkadaAPIError(f"Camera {camera_id} not found")

        except Exception as e:
            logger.error(f"Failed to get camera info: {e}")
            raise

    async def get_snapshot(self, camera_id: str) -> Optional[bytes]:
        """
        Get current snapshot/thumbnail from camera

        Args:
            camera_id: Verkada camera ID

        Returns:
            JPEG image bytes or None if failed
        """
        logger.info(f"Requesting snapshot for Verkada camera {camera_id}...")

        try:
            loop = asyncio.get_event_loop()

            # Get thumbnail URL
            result = await loop.run_in_executor(
                self.executor,
                lambda: self._make_request(
                    "GET",
                    "/cameras/v1/thumbnail",
                    {"camera_id": camera_id}
                )
            )

            if isinstance(result, dict) and result.get("url"):
                # Fetch the actual image
                response = await loop.run_in_executor(
                    self.executor,
                    lambda: self.session.get(result["url"], timeout=10)
                )

                if response.status_code == 200:
                    logger.info(f"Got snapshot for camera {camera_id} ({len(response.content)} bytes)")
                    return response.content

            logger.warning(f"Could not get snapshot for camera {camera_id}")
            return None

        except Exception as e:
            logger.error(f"Failed to get snapshot: {e}")
            return None

    async def get_footage_stream_url(
        self,
        camera_id: str,
        start_time: Optional[int] = None,
        end_time: Optional[int] = None
    ) -> Optional[str]:
        """
        Get HLS streaming URL for live or historical footage

        Args:
            camera_id: Verkada camera ID
            start_time: Unix timestamp for historical start (None for live)
            end_time: Unix timestamp for historical end

        Returns:
            HLS stream URL or None if failed
        """
        logger.info(f"Requesting footage stream URL for camera {camera_id}...")

        try:
            loop = asyncio.get_event_loop()

            params = {"camera_id": camera_id}
            if start_time:
                params["start_time"] = start_time
            if end_time:
                params["end_time"] = end_time

            result = await loop.run_in_executor(
                self.executor,
                lambda: self._make_request("GET", "/cameras/v1/footage/stream", params)
            )

            if isinstance(result, dict) and result.get("url"):
                return result["url"]

            return None

        except Exception as e:
            logger.error(f"Failed to get footage stream URL: {e}")
            return None

    async def get_camera_settings(self, camera_id: str) -> Dict:
        """
        Get current camera configuration/settings

        Note: Verkada settings are primarily cloud-managed.
        This returns available configuration data.

        Args:
            camera_id: Verkada camera ID

        Returns:
            Camera settings dictionary in PlatoniCam format
        """
        logger.info(f"Fetching settings for Verkada camera {camera_id}...")

        try:
            # Get camera info (includes some settings)
            camera_info = await self.get_camera_info(camera_id)
            raw_data = camera_info.get("rawData", {})

            # Build settings response
            # Note: Verkada API doesn't expose granular settings like bitrate/fps
            # These would need to be inferred or set via Command dashboard
            settings = {
                "stream": {
                    "resolution": raw_data.get("resolution", "Unknown"),
                    "codec": raw_data.get("codec", "H.264"),  # Verkada uses H.264/H.265
                    "fps": raw_data.get("fps", 30),
                    "bitrateMbps": None,  # Not exposed via API
                    "cloudStorage": raw_data.get("cloud_retention_days")
                },
                "exposure": {
                    "mode": "Auto",  # Verkada cameras use auto exposure
                    "wdr": raw_data.get("wdr_enabled", "Auto")
                },
                "lowLight": {
                    "irMode": raw_data.get("ir_mode", "Auto"),
                    "nightVision": raw_data.get("night_vision_enabled", True)
                },
                "image": {
                    "rotation": raw_data.get("rotation", 0),
                    "mirror": raw_data.get("mirror", False)
                },
                "cloudManaged": True,
                "vmsSystem": "verkada",
                "note": "Verkada cameras are cloud-managed. Advanced settings are configured via Command dashboard."
            }

            return settings

        except Exception as e:
            logger.error(f"Failed to get camera settings: {e}")
            raise

    async def get_organization_info(self) -> Dict:
        """
        Get organization information

        Returns:
            Organization info dictionary
        """
        logger.info("Fetching Verkada organization info...")

        try:
            loop = asyncio.get_event_loop()

            # The /cameras/v1/devices endpoint doesn't return org info directly
            # We can infer some info from camera data
            cameras = await self.get_cameras(page_size=1)

            return {
                "region": self.region,
                "cameraCount": len(cameras) if cameras else 0,
                "connected": True
            }

        except Exception as e:
            logger.error(f"Failed to get organization info: {e}")
            return {
                "region": self.region,
                "connected": False,
                "error": str(e)
            }

    def close(self):
        """Close connection and cleanup resources"""
        self.session.close()
        self.executor.shutdown(wait=False)
        self._token = None
        logger.info("Verkada client closed")


# Example usage
if __name__ == "__main__":
    import asyncio

    async def test_verkada_client():
        """Test Verkada client"""

        # Initialize client
        client = VerkadaClient(
            api_key="your-api-key-here",  # Replace with actual API key
            region="us"
        )

        try:
            # Test connection
            print("Testing connection...")
            connected = await client.test_connection()
            print(f"Connected: {connected}")

            if not connected:
                print("Cannot connect to Verkada API")
                return

            # Get cameras
            print("\nGetting cameras...")
            cameras = await client.get_cameras()
            print(f"Found {len(cameras)} cameras")

            for cam in cameras[:5]:  # Print first 5
                print(f"  - {cam['name']} ({cam['model']}) at {cam['ip']}")

            # Get settings for first camera
            if cameras:
                camera_id = cameras[0]["id"]
                print(f"\nGetting settings for camera {camera_id}...")
                settings = await client.get_camera_settings(camera_id)
                print(f"Settings: {settings}")

        finally:
            client.close()

    # Run test
    asyncio.run(test_verkada_client())
