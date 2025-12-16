# backend/utils/tls_helper.py
"""
TLS/SSL Configuration Utilities for Camera Connections

Provides secure SSL context creation with configurable certificate validation.
Supports both strict validation (production) and self-signed certificates
(common in camera deployments).

Phase 5 Security Enhancement.
"""

import ssl
import logging
from typing import Optional
from pathlib import Path

logger = logging.getLogger(__name__)


def create_ssl_context(
    verify: bool = False,
    allow_self_signed: bool = True,
    ca_bundle_path: Optional[str] = None,
    client_cert_path: Optional[str] = None,
    client_key_path: Optional[str] = None,
) -> ssl.SSLContext:
    """
    Create an SSL context for camera connections.

    Args:
        verify: Whether to verify server certificates (default: False for dev)
        allow_self_signed: Allow self-signed certificates (default: True)
        ca_bundle_path: Path to custom CA certificate bundle (optional)
        client_cert_path: Path to client certificate for mutual TLS (optional)
        client_key_path: Path to client private key for mutual TLS (optional)

    Returns:
        Configured ssl.SSLContext

    Security Notes:
        - For production deployments with proper CA infrastructure, set verify=True
        - Most IP cameras use self-signed certificates, requiring allow_self_signed=True
        - Mutual TLS (client certs) provides strongest authentication but requires
          certificate deployment to cameras
    """
    if verify:
        # Strict verification mode
        ctx = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
        ctx.check_hostname = True
        ctx.verify_mode = ssl.CERT_REQUIRED

        # Load custom CA bundle if provided
        if ca_bundle_path and Path(ca_bundle_path).exists():
            ctx.load_verify_locations(cafile=ca_bundle_path)
            logger.info(f"Loaded custom CA bundle from {ca_bundle_path}")
        else:
            # Use system default CA certificates
            ctx.load_default_certs()

        logger.info("Created SSL context with certificate verification ENABLED")

    elif allow_self_signed:
        # Allow self-signed certificates (common for cameras)
        ctx = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        logger.info("Created SSL context allowing self-signed certificates")

    else:
        # No verification (insecure - development only)
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        logger.warning("Created SSL context with NO certificate verification (insecure)")

    # Load client certificate for mutual TLS if provided
    if client_cert_path and client_key_path:
        if Path(client_cert_path).exists() and Path(client_key_path).exists():
            ctx.load_cert_chain(certfile=client_cert_path, keyfile=client_key_path)
            logger.info("Loaded client certificate for mutual TLS authentication")
        else:
            logger.warning(
                f"Client cert/key not found: {client_cert_path}, {client_key_path}"
            )

    # Set secure protocol options
    ctx.options |= ssl.OP_NO_SSLv2
    ctx.options |= ssl.OP_NO_SSLv3
    ctx.options |= ssl.OP_NO_TLSv1
    ctx.options |= ssl.OP_NO_TLSv1_1

    return ctx


def get_default_ssl_context() -> ssl.SSLContext:
    """
    Get default SSL context using application settings.

    Returns:
        SSL context configured according to application settings
    """
    from config import get_settings

    settings = get_settings()

    return create_ssl_context(
        verify=settings.tls_verify_certificates,
        allow_self_signed=settings.tls_allow_self_signed,
        ca_bundle_path=settings.tls_ca_bundle_path or None,
        client_cert_path=settings.tls_client_cert_path or None,
        client_key_path=settings.tls_client_key_path or None,
    )


def create_https_adapter_session():
    """
    Create a requests Session with custom SSL handling.

    Returns:
        requests.Session configured with appropriate SSL settings

    Note:
        Used for HTTPS connections to cameras (snapshots, ONVIF over HTTPS).
    """
    import requests
    from requests.adapters import HTTPAdapter
    from urllib3.util.ssl_ import create_urllib3_context

    from config import get_settings

    settings = get_settings()

    class SSLAdapter(HTTPAdapter):
        """Custom adapter to use our SSL context"""

        def init_poolmanager(self, *args, **kwargs):
            ctx = create_urllib3_context()

            if not settings.tls_verify_certificates:
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE

            kwargs["ssl_context"] = ctx
            return super().init_poolmanager(*args, **kwargs)

    session = requests.Session()
    session.mount("https://", SSLAdapter())

    # Disable SSL warnings if not verifying (to reduce log noise)
    if not settings.tls_verify_certificates:
        import urllib3

        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    return session


def validate_camera_certificate(
    host: str, port: int = 443, timeout: int = 10
) -> dict:
    """
    Validate a camera's SSL certificate and return details.

    Args:
        host: Camera hostname or IP
        port: HTTPS port (default: 443)
        timeout: Connection timeout in seconds

    Returns:
        Dictionary with certificate information:
        {
            "valid": True/False,
            "self_signed": True/False,
            "issuer": "...",
            "subject": "...",
            "expires": "...",
            "error": "..." (if any)
        }
    """
    import socket
    from datetime import datetime

    result = {
        "host": host,
        "port": port,
        "valid": False,
        "self_signed": False,
        "issuer": None,
        "subject": None,
        "expires": None,
        "days_until_expiry": None,
        "error": None,
    }

    try:
        # First try with CERT_OPTIONAL to get parsed certificate
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_OPTIONAL

        with socket.create_connection((host, port), timeout=timeout) as sock:
            with ctx.wrap_socket(sock, server_hostname=host) as ssock:
                cert = ssock.getpeercert(binary_form=False)
                binary_cert = ssock.getpeercert(binary_form=True)

                if cert:
                    result["valid"] = True

                    # Parse certificate details
                    issuer = dict(x[0] for x in cert.get("issuer", []))
                    subject = dict(x[0] for x in cert.get("subject", []))

                    result["issuer"] = issuer.get(
                        "organizationName", issuer.get("commonName", "Unknown")
                    )
                    result["subject"] = subject.get(
                        "commonName", subject.get("organizationName", "Unknown")
                    )

                    # Check if self-signed
                    result["self_signed"] = result["issuer"] == result["subject"]

                    # Parse expiry
                    not_after = cert.get("notAfter")
                    if not_after:
                        expiry = datetime.strptime(not_after, "%b %d %H:%M:%S %Y %Z")
                        result["expires"] = expiry.isoformat()
                        result["days_until_expiry"] = (expiry - datetime.utcnow()).days

                elif binary_cert:
                    # Binary cert available - basic validation
                    result["valid"] = True
                    result["self_signed"] = True  # Assume self-signed if can't verify

                else:
                    result["valid"] = False
                    result["error"] = "No certificate received"

    except ssl.SSLCertVerificationError as e:
        result["error"] = f"Certificate verification failed: {e}"
    except socket.timeout:
        result["error"] = "Connection timeout"
    except ConnectionRefusedError:
        result["error"] = "Connection refused"
    except Exception as e:
        result["error"] = str(e)

    return result
