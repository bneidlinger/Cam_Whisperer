"""
Unit tests for Verkada Cloud VMS Client

Tests the VerkadaClient class with mocked HTTP responses.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import asyncio

# Import the client and exceptions
import sys
sys.path.insert(0, 'backend')

from integrations.verkada_client import (
    VerkadaClient,
    VerkadaConnectionError,
    VerkadaAuthenticationError,
    VerkadaAPIError
)


class TestVerkadaClientInit:
    """Tests for VerkadaClient initialization"""

    def test_init_default_region(self):
        """Test client initializes with default US region"""
        client = VerkadaClient(api_key="test-key")
        assert client.region == "us"
        assert client.base_url == "https://api.verkada.com"
        client.close()

    def test_init_eu_region(self):
        """Test client initializes with EU region"""
        client = VerkadaClient(api_key="test-key", region="eu")
        assert client.region == "eu"
        assert client.base_url == "https://api.eu.verkada.com"
        client.close()

    def test_init_invalid_region(self):
        """Test client raises error for invalid region"""
        with pytest.raises(ValueError) as exc_info:
            VerkadaClient(api_key="test-key", region="invalid")
        assert "Invalid region" in str(exc_info.value)

    def test_init_with_org_id(self):
        """Test client initializes with org ID"""
        client = VerkadaClient(api_key="test-key", org_id="org-123")
        assert client.org_id == "org-123"
        client.close()


class TestVerkadaTokenManagement:
    """Tests for token management"""

    @patch('integrations.verkada_client.requests.Session')
    def test_get_token_success(self, mock_session_class):
        """Test successful token retrieval"""
        mock_session = MagicMock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"token": "test-token-123"}
        mock_session.post.return_value = mock_response
        mock_session_class.return_value = mock_session

        client = VerkadaClient(api_key="test-key")
        token = client._get_token()

        assert token == "test-token-123"
        mock_session.post.assert_called_once()
        client.close()

    @patch('integrations.verkada_client.requests.Session')
    def test_get_token_invalid_api_key(self, mock_session_class):
        """Test token retrieval with invalid API key"""
        mock_session = MagicMock()
        mock_response = Mock()
        mock_response.status_code = 401
        mock_session.post.return_value = mock_response
        mock_session_class.return_value = mock_session

        client = VerkadaClient(api_key="invalid-key")

        with pytest.raises(VerkadaAuthenticationError) as exc_info:
            client._get_token()

        assert "Invalid API key" in str(exc_info.value)
        client.close()

    @patch('integrations.verkada_client.requests.Session')
    def test_token_caching(self, mock_session_class):
        """Test that tokens are cached"""
        mock_session = MagicMock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"token": "cached-token"}
        mock_session.post.return_value = mock_response
        mock_session_class.return_value = mock_session

        client = VerkadaClient(api_key="test-key")

        # First call should make HTTP request
        token1 = client._get_token()

        # Second call should use cached token
        token2 = client._get_token()

        assert token1 == token2
        assert mock_session.post.call_count == 1  # Only one HTTP call
        client.close()


class TestVerkadaCameraOperations:
    """Tests for camera operations"""

    @pytest.fixture
    def mock_client(self):
        """Create a mocked client"""
        with patch('integrations.verkada_client.requests.Session') as mock_session_class:
            mock_session = MagicMock()
            mock_session_class.return_value = mock_session

            # Token response
            token_response = Mock()
            token_response.status_code = 200
            token_response.json.return_value = {"token": "test-token"}

            # Camera response
            camera_response = Mock()
            camera_response.status_code = 200
            camera_response.content = b'{"cameras": [{"camera_id": "cam-1", "name": "Front Door", "model": "CD52"}]}'
            camera_response.json.return_value = {
                "cameras": [
                    {
                        "camera_id": "cam-1",
                        "name": "Front Door",
                        "model": "CD52",
                        "is_online": True,
                        "local_ip": "192.168.1.100"
                    }
                ]
            }

            mock_session.post.return_value = token_response
            mock_session.request.return_value = camera_response

            client = VerkadaClient(api_key="test-key")
            yield client, mock_session
            client.close()

    @pytest.mark.asyncio
    async def test_test_connection_success(self, mock_client):
        """Test successful connection test"""
        client, mock_session = mock_client
        result = await client.test_connection()
        assert result is True

    @pytest.mark.asyncio
    async def test_get_cameras(self, mock_client):
        """Test camera discovery"""
        client, mock_session = mock_client
        cameras = await client.get_cameras()

        assert len(cameras) == 1
        assert cameras[0]["id"] == "cam-1"
        assert cameras[0]["name"] == "Front Door"
        assert cameras[0]["vendor"] == "Verkada"
        assert cameras[0]["vmsSystem"] == "verkada"

    @pytest.mark.asyncio
    async def test_normalize_camera_data(self, mock_client):
        """Test camera data normalization"""
        client, _ = mock_client

        raw_camera = {
            "camera_id": "cam-123",
            "name": "Test Camera",
            "model": "CD62",
            "is_online": True,
            "local_ip": "10.0.0.50",
            "serial": "ABC123",
            "firmware": "2.1.0"
        }

        normalized = client._normalize_camera_data(raw_camera)

        assert normalized["id"] == "cam-123"
        assert normalized["name"] == "Test Camera"
        assert normalized["vendor"] == "Verkada"
        assert normalized["model"] == "CD62"
        assert normalized["status"] == "online"
        assert normalized["ip"] == "10.0.0.50"
        assert normalized["cloudManaged"] is True
        assert normalized["vmsSystem"] == "verkada"


class TestVerkadaErrorHandling:
    """Tests for error handling"""

    @patch('integrations.verkada_client.requests.Session')
    def test_connection_timeout(self, mock_session_class):
        """Test handling of connection timeout"""
        import requests

        mock_session = MagicMock()
        mock_session.post.side_effect = requests.exceptions.ConnectTimeout()
        mock_session_class.return_value = mock_session

        client = VerkadaClient(api_key="test-key")

        with pytest.raises(VerkadaConnectionError) as exc_info:
            client._get_token()

        assert "Failed to connect" in str(exc_info.value)
        client.close()

    @patch('integrations.verkada_client.requests.Session')
    def test_forbidden_access(self, mock_session_class):
        """Test handling of forbidden access"""
        mock_session = MagicMock()
        mock_response = Mock()
        mock_response.status_code = 403
        mock_session.post.return_value = mock_response
        mock_session_class.return_value = mock_session

        client = VerkadaClient(api_key="test-key")

        with pytest.raises(VerkadaAuthenticationError) as exc_info:
            client._get_token()

        assert "permissions" in str(exc_info.value).lower()
        client.close()


class TestVerkadaCleanup:
    """Tests for resource cleanup"""

    @patch('integrations.verkada_client.requests.Session')
    def test_close_cleanup(self, mock_session_class):
        """Test that close properly cleans up resources"""
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session

        client = VerkadaClient(api_key="test-key")
        client._token = "some-token"

        client.close()

        mock_session.close.assert_called_once()
        assert client._token is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
