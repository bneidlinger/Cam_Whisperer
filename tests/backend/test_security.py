# tests/backend/test_security.py
"""
Tests for Security Features (Phase 5)
- Discovery mode control
- TLS integration in ONVIF client
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock

# Add backend to path
backend_path = Path(__file__).parent.parent.parent / "backend"
sys.path.insert(0, str(backend_path))


class TestONVIFClientTLSIntegration:
    """Tests for TLS integration in ONVIFClient"""

    def test_client_has_ssl_context_attribute(self):
        """Should have class-level SSL context"""
        from integrations.onvif_client import ONVIFClient

        # SSL context should be accessible
        assert hasattr(ONVIFClient, '_ssl_context')

    def test_client_has_get_ssl_context_method(self):
        """Should have method to get SSL context"""
        from integrations.onvif_client import ONVIFClient

        assert hasattr(ONVIFClient, 'get_ssl_context')
        assert callable(ONVIFClient.get_ssl_context)

    def test_client_accepts_use_tls_parameter(self):
        """Should accept use_tls parameter in constructor"""
        from integrations.onvif_client import ONVIFClient

        client = ONVIFClient(use_tls=True)
        assert client.use_tls is True

        client2 = ONVIFClient(use_tls=False)
        assert client2.use_tls is False

    def test_client_has_validate_camera_tls_method(self):
        """Should have method to validate camera TLS certificate"""
        from integrations.onvif_client import ONVIFClient

        client = ONVIFClient()
        assert hasattr(client, 'validate_camera_tls')


class TestDiscoveryModeControl:
    """Tests for WS-Discovery mode control"""

    def test_client_has_get_discovery_mode_method(self):
        """Should have method to get discovery mode"""
        from integrations.onvif_client import ONVIFClient

        client = ONVIFClient()
        assert hasattr(client, 'get_discovery_mode')

    def test_client_has_set_discovery_mode_method(self):
        """Should have method to set discovery mode"""
        from integrations.onvif_client import ONVIFClient

        client = ONVIFClient()
        assert hasattr(client, 'set_discovery_mode')

    def test_client_has_disable_discovery_method(self):
        """Should have convenience method to disable discovery"""
        from integrations.onvif_client import ONVIFClient

        client = ONVIFClient()
        assert hasattr(client, 'disable_discovery')

    def test_client_has_enable_discovery_method(self):
        """Should have convenience method to enable discovery"""
        from integrations.onvif_client import ONVIFClient

        client = ONVIFClient()
        assert hasattr(client, 'enable_discovery')

    @pytest.mark.asyncio
    async def test_get_discovery_mode_returns_dict(self):
        """Should return dictionary with discovery mode info"""
        from integrations.onvif_client import ONVIFClient

        client = ONVIFClient()

        # Mock the camera object
        mock_camera = MagicMock()
        mock_device_mgmt = MagicMock()
        mock_device_mgmt.GetDiscoveryMode = MagicMock(return_value="Discoverable")
        mock_camera.create_devicemgmt_service = MagicMock(return_value=mock_device_mgmt)

        with patch.object(client, 'executor'):
            with patch('asyncio.get_event_loop') as mock_loop:
                mock_loop.return_value.run_in_executor = AsyncMock(return_value="Discoverable")

                result = await client.get_discovery_mode(mock_camera)

        assert isinstance(result, dict)
        assert "mode" in result
        assert "discoverable" in result

    @pytest.mark.asyncio
    async def test_set_discovery_mode_returns_result(self):
        """Should return result dictionary from set operation"""
        from integrations.onvif_client import ONVIFClient

        client = ONVIFClient()

        # Mock the camera object
        mock_camera = MagicMock()
        mock_device_mgmt = MagicMock()
        mock_device_mgmt.GetDiscoveryMode = MagicMock(return_value="Discoverable")
        mock_device_mgmt.SetDiscoveryMode = MagicMock(return_value=None)
        mock_camera.create_devicemgmt_service = MagicMock(return_value=mock_device_mgmt)

        with patch.object(client, 'executor'):
            with patch('asyncio.get_event_loop') as mock_loop:
                # First call gets current mode, second sets new mode
                mock_loop.return_value.run_in_executor = AsyncMock(side_effect=["Discoverable", None])

                result = await client.set_discovery_mode(mock_camera, discoverable=False)

        assert isinstance(result, dict)
        assert "success" in result
        assert "mode" in result

    @pytest.mark.asyncio
    async def test_disable_discovery_calls_set_discovery_mode(self):
        """Should call set_discovery_mode with discoverable=False"""
        from integrations.onvif_client import ONVIFClient

        client = ONVIFClient()
        mock_camera = MagicMock()

        with patch.object(client, 'set_discovery_mode', new_callable=AsyncMock) as mock_set:
            mock_set.return_value = {"success": True, "mode": "NonDiscoverable"}

            result = await client.disable_discovery(mock_camera)

            mock_set.assert_called_once_with(mock_camera, discoverable=False)

    @pytest.mark.asyncio
    async def test_enable_discovery_calls_set_discovery_mode(self):
        """Should call set_discovery_mode with discoverable=True"""
        from integrations.onvif_client import ONVIFClient

        client = ONVIFClient()
        mock_camera = MagicMock()

        with patch.object(client, 'set_discovery_mode', new_callable=AsyncMock) as mock_set:
            mock_set.return_value = {"success": True, "mode": "Discoverable"}

            result = await client.enable_discovery(mock_camera)

            mock_set.assert_called_once_with(mock_camera, discoverable=True)


class TestSecurityAPIEndpoints:
    """Tests for security-related API endpoints"""

    @pytest.fixture
    def client(self):
        """Create test client"""
        from fastapi.testclient import TestClient
        from main import app
        return TestClient(app)

    def test_discovery_mode_get_endpoint_exists(self, client):
        """Should have GET endpoint for discovery mode"""
        # Without credentials, should return 400
        response = client.get("/api/camera/192.168.1.100/discovery-mode")
        assert response.status_code in [400, 422, 500]  # Missing credentials or connection error

    def test_discovery_mode_post_endpoint_exists(self, client):
        """Should have POST endpoint for setting discovery mode"""
        response = client.post(
            "/api/camera/discovery-mode",
            json={
                "ip": "192.168.1.100",
                "port": 80,
                "username": "admin",
                "password": "password",
                "discoverable": False
            }
        )
        # Endpoint should exist - returns 200 with error in body, or 500/503 on connection failure
        assert response.status_code in [200, 500, 503]
        if response.status_code == 200:
            data = response.json()
            # Should have result structure with success=false or error message
            assert "success" in data or "error" in data or "mode" in data

    def test_tls_certificate_endpoint_exists(self, client):
        """Should have GET endpoint for TLS certificate validation"""
        response = client.get("/api/camera/192.168.1.100/tls-certificate")
        # Should return result (with error since host won't exist)
        assert response.status_code == 200
        data = response.json()
        assert "valid" in data


class TestTLSHelperIntegration:
    """Tests for TLS helper integration"""

    def test_tls_available_flag(self):
        """Should have TLS_AVAILABLE flag in onvif_client"""
        from integrations.onvif_client import TLS_AVAILABLE

        assert isinstance(TLS_AVAILABLE, bool)
        # Should be True since we created the module
        assert TLS_AVAILABLE is True

    def test_ssl_context_initialization(self):
        """Should initialize SSL context on client creation"""
        from integrations.onvif_client import ONVIFClient

        # Reset class-level context
        ONVIFClient._ssl_context = None

        client = ONVIFClient(use_tls=True)

        # Context should be initialized
        ctx = ONVIFClient.get_ssl_context()
        assert ctx is not None


class TestConfigSecuritySettings:
    """Tests for security configuration settings"""

    def test_config_has_tls_settings(self):
        """Should have TLS configuration settings"""
        from config import Settings

        settings = Settings()

        assert hasattr(settings, 'tls_verify_certificates')
        assert hasattr(settings, 'tls_allow_self_signed')
        assert hasattr(settings, 'tls_ca_bundle_path')
        assert hasattr(settings, 'tls_client_cert_path')
        assert hasattr(settings, 'tls_client_key_path')

    def test_tls_defaults_allow_self_signed(self):
        """Should default to allowing self-signed certificates"""
        from config import Settings

        settings = Settings()

        assert settings.tls_allow_self_signed is True
        assert settings.tls_verify_certificates is False
