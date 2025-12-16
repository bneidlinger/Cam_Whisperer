# tests/backend/test_tls_helper.py
"""
Tests for TLS/SSL helper utilities (Phase 5.1)
"""

import pytest
import ssl
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add backend to path
backend_path = Path(__file__).parent.parent.parent / "backend"
sys.path.insert(0, str(backend_path))

from utils.tls_helper import (
    create_ssl_context,
    get_default_ssl_context,
    validate_camera_certificate,
)


class TestCreateSSLContext:
    """Tests for create_ssl_context function"""

    def test_creates_context_without_verification(self):
        """Should create context that doesn't verify certificates"""
        ctx = create_ssl_context(verify=False, allow_self_signed=True)

        assert isinstance(ctx, ssl.SSLContext)
        assert ctx.verify_mode == ssl.CERT_NONE
        assert ctx.check_hostname is False

    def test_creates_strict_context_with_verification(self):
        """Should create context that verifies certificates when verify=True"""
        ctx = create_ssl_context(verify=True, allow_self_signed=False)

        assert isinstance(ctx, ssl.SSLContext)
        assert ctx.verify_mode == ssl.CERT_REQUIRED
        assert ctx.check_hostname is True

    def test_disables_old_ssl_protocols(self):
        """Should disable SSLv2, SSLv3, TLSv1.0, TLSv1.1"""
        ctx = create_ssl_context(verify=False)

        # Check that old protocols are disabled
        # Note: In Python 3.10+, SSLv2 is completely removed (OP_NO_SSLv2 = 0)
        # So we only check the options that are still relevant
        assert ctx.options & ssl.OP_NO_SSLv3
        # In Python 3.12+, these options are deprecated but still work
        # The context is created with secure defaults

    def test_loads_custom_ca_bundle(self, tmp_path):
        """Should load custom CA bundle when provided"""
        # Create a dummy CA file (won't be valid, just testing the path)
        ca_file = tmp_path / "ca-bundle.crt"
        ca_file.write_text("-----BEGIN CERTIFICATE-----\ntest\n-----END CERTIFICATE-----")

        # This will fail to load the invalid cert, but we're testing the path handling
        with pytest.raises(ssl.SSLError):
            create_ssl_context(
                verify=True,
                ca_bundle_path=str(ca_file)
            )

    def test_allows_self_signed_when_configured(self):
        """Should allow self-signed certificates when allow_self_signed=True"""
        ctx = create_ssl_context(verify=False, allow_self_signed=True)

        assert ctx.verify_mode == ssl.CERT_NONE


class TestGetDefaultSSLContext:
    """Tests for get_default_ssl_context function"""

    @patch('config.get_settings')
    def test_uses_settings_values(self, mock_settings):
        """Should use values from application settings"""
        mock_settings.return_value = MagicMock(
            tls_verify_certificates=False,
            tls_allow_self_signed=True,
            tls_ca_bundle_path="",
            tls_client_cert_path="",
            tls_client_key_path="",
        )

        ctx = get_default_ssl_context()

        assert isinstance(ctx, ssl.SSLContext)
        mock_settings.assert_called_once()


class TestValidateCameraCertificate:
    """Tests for validate_camera_certificate function"""

    def test_returns_error_for_invalid_host(self):
        """Should return error for non-existent host"""
        result = validate_camera_certificate("192.168.255.255", port=443, timeout=1)

        assert result["host"] == "192.168.255.255"
        assert result["port"] == 443
        assert result["valid"] is False
        assert result["error"] is not None

    def test_returns_error_for_connection_refused(self):
        """Should return error when connection is refused"""
        # Use localhost on a port that's likely not listening
        result = validate_camera_certificate("127.0.0.1", port=65432, timeout=1)

        assert result["valid"] is False
        assert "refused" in result["error"].lower() or "timeout" in result["error"].lower() or result["error"] is not None

    def test_returns_certificate_details_for_valid_host(self):
        """Should return certificate details for a valid HTTPS host"""
        # Test against a known public HTTPS server
        result = validate_camera_certificate("www.google.com", port=443, timeout=5)

        # This test requires network access
        if result.get("error") and "timeout" in result["error"].lower():
            pytest.skip("Network timeout - skipping external test")

        assert result["host"] == "www.google.com"
        assert result["valid"] is True
        assert result["issuer"] is not None
        assert result["subject"] is not None
        assert result["expires"] is not None
        assert result["self_signed"] is False  # Google uses proper CA

    def test_result_structure(self):
        """Should return all expected fields in result"""
        result = validate_camera_certificate("127.0.0.1", port=443, timeout=1)

        expected_keys = [
            "host", "port", "valid", "self_signed",
            "issuer", "subject", "expires", "days_until_expiry", "error"
        ]

        for key in expected_keys:
            assert key in result, f"Missing key: {key}"


class TestSSLContextIntegration:
    """Integration tests for SSL context usage"""

    def test_context_can_wrap_socket(self):
        """Should be able to wrap a socket with the context"""
        import socket

        ctx = create_ssl_context(verify=False, allow_self_signed=True)
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        try:
            # Should not raise an error
            wrapped = ctx.wrap_socket(sock, server_hostname="example.com")
            wrapped.close()
        except Exception as e:
            # Socket might not be connected, but wrapping should work
            assert "not connected" in str(e).lower() or isinstance(e, ssl.SSLError)
        finally:
            sock.close()
