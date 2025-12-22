"""
Unit tests for Rhombus Cloud VMS Client

Tests the RhombusClient class with mocked HTTP responses.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import asyncio

# Import the client and exceptions
import sys
sys.path.insert(0, 'backend')

from integrations.rhombus_client import (
    RhombusClient,
    RhombusConnectionError,
    RhombusAuthenticationError,
    RhombusAPIError
)


class TestRhombusClientInit:
    """Tests for RhombusClient initialization"""

    def test_init_with_api_key(self):
        """Test client initializes with API key"""
        client = RhombusClient(api_key="test-api-key")
        assert client.api_key == "test-api-key"
        assert "x-auth-apikey" in client.session.headers
        assert client.session.headers["x-auth-apikey"] == "test-api-key"
        assert client.session.headers["x-auth-scheme"] == "api-token"
        client.close()

    def test_init_with_custom_timeout(self):
        """Test client initializes with custom timeout"""
        client = RhombusClient(api_key="test-key", timeout=60)
        assert client.timeout == 60
        client.close()


class TestRhombusAPIRequests:
    """Tests for API request handling"""

    @patch('integrations.rhombus_client.requests.Session')
    def test_make_request_success(self, mock_session_class):
        """Test successful API request"""
        mock_session = MagicMock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b'{"cameraStates": []}'
        mock_response.json.return_value = {"cameraStates": []}
        mock_session.post.return_value = mock_response
        mock_session_class.return_value = mock_session

        client = RhombusClient(api_key="test-key")
        result = client._make_request("camera/getMinimalCameraStateList", {})

        assert result == {"cameraStates": []}
        mock_session.post.assert_called_once()
        client.close()

    @patch('integrations.rhombus_client.requests.Session')
    def test_make_request_auth_error(self, mock_session_class):
        """Test API request with authentication error"""
        mock_session = MagicMock()
        mock_response = Mock()
        mock_response.status_code = 401
        mock_session.post.return_value = mock_response
        mock_session_class.return_value = mock_session

        client = RhombusClient(api_key="invalid-key")

        with pytest.raises(RhombusAuthenticationError) as exc_info:
            client._make_request("camera/getMinimalCameraStateList", {})

        assert "Invalid API key" in str(exc_info.value)
        client.close()

    @patch('integrations.rhombus_client.requests.Session')
    def test_make_request_not_found(self, mock_session_class):
        """Test API request with 404 error"""
        mock_session = MagicMock()
        mock_response = Mock()
        mock_response.status_code = 404
        mock_session.post.return_value = mock_response
        mock_session_class.return_value = mock_session

        client = RhombusClient(api_key="test-key")

        with pytest.raises(RhombusAPIError) as exc_info:
            client._make_request("invalid/endpoint", {})

        assert "not found" in str(exc_info.value).lower()
        client.close()


class TestRhombusCameraOperations:
    """Tests for camera operations"""

    @pytest.fixture
    def mock_client(self):
        """Create a mocked client"""
        with patch('integrations.rhombus_client.requests.Session') as mock_session_class:
            mock_session = MagicMock()
            mock_session_class.return_value = mock_session

            # Default camera list response
            camera_response = Mock()
            camera_response.status_code = 200
            camera_response.content = b'{"cameraStates": [{"uuid": "cam-1", "name": "Lobby", "model": "R100"}]}'
            camera_response.json.return_value = {
                "cameraStates": [
                    {
                        "uuid": "cam-1",
                        "name": "Lobby",
                        "model": "R100",
                        "online": True,
                        "lanIpAddress": "192.168.1.50"
                    }
                ]
            }

            mock_session.post.return_value = camera_response

            client = RhombusClient(api_key="test-key")
            yield client, mock_session
            client.close()

    @pytest.mark.asyncio
    async def test_test_connection_success(self, mock_client):
        """Test successful connection test"""
        client, _ = mock_client
        result = await client.test_connection()
        assert result is True

    @pytest.mark.asyncio
    async def test_get_cameras(self, mock_client):
        """Test camera discovery"""
        client, _ = mock_client
        cameras = await client.get_cameras()

        assert len(cameras) == 1
        assert cameras[0]["id"] == "cam-1"
        assert cameras[0]["name"] == "Lobby"
        assert cameras[0]["vendor"] == "Rhombus"
        assert cameras[0]["vmsSystem"] == "rhombus"

    @pytest.mark.asyncio
    async def test_normalize_camera_data(self, mock_client):
        """Test camera data normalization"""
        client, _ = mock_client

        raw_camera = {
            "uuid": "cam-456",
            "name": "Entrance",
            "model": "R200",
            "online": True,
            "lanIpAddress": "10.0.0.100",
            "serialNumber": "XYZ789",
            "firmwareVersion": "3.0.1"
        }

        normalized = client._normalize_camera_data(raw_camera)

        assert normalized["id"] == "cam-456"
        assert normalized["name"] == "Entrance"
        assert normalized["vendor"] == "Rhombus"
        assert normalized["model"] == "R200"
        assert normalized["status"] == "online"
        assert normalized["ip"] == "10.0.0.100"
        assert normalized["cloudManaged"] is True
        assert normalized["vmsSystem"] == "rhombus"


class TestRhombusCameraConfig:
    """Tests for camera configuration operations"""

    @pytest.fixture
    def mock_config_client(self):
        """Create a mocked client for config tests"""
        with patch('integrations.rhombus_client.requests.Session') as mock_session_class:
            mock_session = MagicMock()
            mock_session_class.return_value = mock_session

            # Config response
            config_response = Mock()
            config_response.status_code = 200
            config_response.content = b'{"config": {"resolution": "1920x1080", "frameRate": 30}}'
            config_response.json.return_value = {
                "config": {
                    "resolution": "1920x1080",
                    "frameRate": 30,
                    "videoCodec": "H.264",
                    "brightness": 50,
                    "contrast": 50
                }
            }

            mock_session.post.return_value = config_response

            client = RhombusClient(api_key="test-key")
            yield client, mock_session
            client.close()

    @pytest.mark.asyncio
    async def test_get_camera_config(self, mock_config_client):
        """Test getting camera configuration"""
        client, _ = mock_config_client
        config = await client.get_camera_config("cam-123")

        assert "stream" in config
        assert "image" in config
        assert config["stream"]["resolution"] == "1920x1080"
        assert config["stream"]["fps"] == 30
        assert config["vmsSystem"] == "rhombus"

    @pytest.mark.asyncio
    async def test_update_camera_config(self, mock_config_client):
        """Test updating camera configuration"""
        client, mock_session = mock_config_client

        # Mock successful update
        update_response = Mock()
        update_response.status_code = 200
        update_response.content = b'{"success": true}'
        update_response.json.return_value = {"success": True}
        mock_session.post.return_value = update_response

        settings = {
            "stream": {"resolution": "2560x1440", "fps": 25},
            "image": {"brightness": 60}
        }

        result = await client.update_camera_config("cam-123", settings)
        assert result is True

    def test_build_rhombus_config(self, mock_config_client):
        """Test building Rhombus config from PlatoniCam format"""
        client, _ = mock_config_client

        settings = {
            "stream": {
                "resolution": "1920x1080",
                "fps": 30,
                "codec": "H.265"
            },
            "image": {
                "brightness": 55,
                "contrast": 45
            },
            "lowLight": {
                "irMode": "Auto"
            }
        }

        rhombus_config = client._build_rhombus_config(settings)

        assert rhombus_config["resolution"] == "1920x1080"
        assert rhombus_config["frameRate"] == 30
        assert rhombus_config["videoCodec"] == "H.265"
        assert rhombus_config["brightness"] == 55
        assert rhombus_config["contrast"] == 45
        assert rhombus_config["infraredMode"] == "Auto"


class TestRhombusErrorHandling:
    """Tests for error handling"""

    @patch('integrations.rhombus_client.requests.Session')
    def test_connection_timeout(self, mock_session_class):
        """Test handling of connection timeout"""
        import requests

        mock_session = MagicMock()
        mock_session.post.side_effect = requests.exceptions.ConnectTimeout()
        mock_session_class.return_value = mock_session

        client = RhombusClient(api_key="test-key")

        with pytest.raises(RhombusConnectionError) as exc_info:
            client._make_request("camera/getMinimalCameraStateList", {})

        assert "timeout" in str(exc_info.value).lower()
        client.close()

    @patch('integrations.rhombus_client.requests.Session')
    def test_connection_error(self, mock_session_class):
        """Test handling of connection error"""
        import requests

        mock_session = MagicMock()
        mock_session.post.side_effect = requests.exceptions.ConnectionError()
        mock_session_class.return_value = mock_session

        client = RhombusClient(api_key="test-key")

        with pytest.raises(RhombusConnectionError) as exc_info:
            client._make_request("camera/getMinimalCameraStateList", {})

        assert "connect" in str(exc_info.value).lower()
        client.close()

    @patch('integrations.rhombus_client.requests.Session')
    def test_api_error_response(self, mock_session_class):
        """Test handling of API error response"""
        mock_session = MagicMock()
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal server error"
        mock_session.post.return_value = mock_response
        mock_session_class.return_value = mock_session

        client = RhombusClient(api_key="test-key")

        with pytest.raises(RhombusAPIError) as exc_info:
            client._make_request("camera/getMinimalCameraStateList", {})

        assert "500" in str(exc_info.value)
        client.close()


class TestRhombusCleanup:
    """Tests for resource cleanup"""

    @patch('integrations.rhombus_client.requests.Session')
    def test_close_cleanup(self, mock_session_class):
        """Test that close properly cleans up resources"""
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session

        client = RhombusClient(api_key="test-key")
        client.close()

        mock_session.close.assert_called_once()


class TestRhombusCameraState:
    """Tests for camera state operations"""

    @patch('integrations.rhombus_client.requests.Session')
    @pytest.mark.asyncio
    async def test_get_camera_state(self, mock_session_class):
        """Test getting camera state"""
        mock_session = MagicMock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b'{"cameraState": {"online": true, "recording": true}}'
        mock_response.json.return_value = {
            "cameraState": {
                "online": True,
                "recording": True,
                "streaming": False
            }
        }
        mock_session.post.return_value = mock_response
        mock_session_class.return_value = mock_session

        client = RhombusClient(api_key="test-key")
        state = await client.get_camera_state("cam-123")

        assert state["online"] is True
        assert state["recording"] is True
        client.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
