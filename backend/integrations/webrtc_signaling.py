# backend/integrations/webrtc_signaling.py
"""
WebRTC Signaling Gateway for ONVIF Cameras

Implements ONVIF WebRTC signaling specification (Version 24.06) to enable
low-latency live streaming from cameras to browsers.

Architecture:
    Browser <--WebSocket--> Backend Gateway <--WS/JSON-RPC--> Camera
                                  |
                            SDP Offer/Answer
                            ICE Candidates
                                  |
    Browser <====== SRTP (Direct P2P or TURN relay) ======> Camera

The gateway proxies JSON-RPC 2.0 signaling messages between browsers and cameras,
handling authentication and session management.
"""

import asyncio
import json
import logging
import ssl
import hashlib
import secrets
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set
from uuid import uuid4

import websockets
from websockets.exceptions import ConnectionClosed, WebSocketException

from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class SignalingState(str, Enum):
    """WebRTC signaling connection state"""
    CONNECTING = "connecting"
    CONNECTED = "connected"
    REGISTERING = "registering"
    REGISTERED = "registered"
    NEGOTIATING = "negotiating"
    STREAMING = "streaming"
    FAILED = "failed"
    CLOSED = "closed"


class JsonRpcMethod(str, Enum):
    """ONVIF WebRTC JSON-RPC 2.0 methods"""
    # Client -> Camera
    REGISTER = "register"
    GET_CONFIGURATIONS = "getConfigurations"
    SET_CONFIGURATION = "setConfiguration"
    OPEN = "open"
    CLOSE = "close"
    ADD_ICE_CANDIDATE = "addIceCandidate"

    # Camera -> Client (notifications)
    ON_OPEN = "onOpen"
    ON_CLOSE = "onClose"
    ON_ERROR = "onError"
    ON_ICE_CANDIDATE = "onIceCandidate"


@dataclass
class WebRTCSession:
    """Represents an active WebRTC streaming session"""
    session_id: str
    camera_ip: str
    camera_port: int
    profile_token: str
    browser_ws: Any  # WebSocket connection to browser
    camera_ws: Optional[Any] = None  # WebSocket connection to camera
    state: SignalingState = SignalingState.CONNECTING
    created_at: datetime = field(default_factory=datetime.utcnow)
    sdp_offer: Optional[str] = None
    sdp_answer: Optional[str] = None
    ice_candidates_local: List[Dict] = field(default_factory=list)
    ice_candidates_remote: List[Dict] = field(default_factory=list)
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sessionId": self.session_id,
            "cameraIp": self.camera_ip,
            "cameraPort": self.camera_port,
            "profileToken": self.profile_token,
            "state": self.state.value,
            "createdAt": self.created_at.isoformat() + "Z",
            "hasOffer": self.sdp_offer is not None,
            "hasAnswer": self.sdp_answer is not None,
            "localCandidates": len(self.ice_candidates_local),
            "remoteCandidates": len(self.ice_candidates_remote),
            "error": self.error,
        }


@dataclass
class ICEServer:
    """ICE server configuration for WebRTC"""
    urls: List[str]
    username: Optional[str] = None
    credential: Optional[str] = None
    credential_type: str = "password"

    def to_dict(self) -> Dict[str, Any]:
        result = {"urls": self.urls}
        if self.username:
            result["username"] = self.username
        if self.credential:
            result["credential"] = self.credential
            result["credentialType"] = self.credential_type
        return result


class ONVIFWebRTCGateway:
    """
    WebRTC signaling gateway per ONVIF spec (Version 24.06).

    Proxies JSON-RPC 2.0 messages between browser and camera to establish
    WebRTC peer connections for low-latency video streaming.

    Usage:
        gateway = ONVIFWebRTCGateway()

        # In FastAPI WebSocket endpoint:
        @app.websocket("/api/webrtc/{camera_id}")
        async def webrtc_endpoint(websocket: WebSocket, camera_id: str):
            await websocket.accept()
            await gateway.handle_browser_connection(
                websocket, camera_ip, camera_port, username, password
            )
    """

    def __init__(self):
        self.active_sessions: Dict[str, WebRTCSession] = {}
        self.ssl_context = self._create_ssl_context()
        self._cleanup_task: Optional[asyncio.Task] = None

    def _create_ssl_context(self) -> ssl.SSLContext:
        """Create SSL context for camera WebSocket connections"""
        ctx = ssl.create_default_context()
        # Many cameras use self-signed certificates
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        return ctx

    def get_ice_servers(self) -> List[ICEServer]:
        """Get configured ICE servers (STUN/TURN) for WebRTC"""
        servers = []

        # Add STUN servers (free, for direct P2P)
        if settings.stun_server_urls:
            stun_urls = [u.strip() for u in settings.stun_server_urls.split(",") if u.strip()]
            if stun_urls:
                servers.append(ICEServer(urls=stun_urls))

        # Add TURN server (for NAT traversal)
        if settings.turn_server_url:
            servers.append(ICEServer(
                urls=[settings.turn_server_url],
                username=settings.turn_username or None,
                credential=settings.turn_credential or None,
                credential_type=settings.turn_credential_type,
            ))

        # Add multiple TURN servers if configured
        if settings.turn_server_urls:
            turn_urls = [u.strip() for u in settings.turn_server_urls.split(",") if u.strip()]
            if turn_urls and settings.turn_username:
                servers.append(ICEServer(
                    urls=turn_urls,
                    username=settings.turn_username,
                    credential=settings.turn_credential or None,
                    credential_type=settings.turn_credential_type,
                ))

        return servers

    def get_ice_servers_config(self) -> List[Dict[str, Any]]:
        """Get ICE servers as dicts for frontend configuration"""
        return [s.to_dict() for s in self.get_ice_servers()]

    async def handle_browser_connection(
        self,
        browser_ws: Any,
        camera_ip: str,
        camera_port: int,
        username: str,
        password: str,
        profile_token: str = "MainStream",
    ) -> None:
        """
        Handle WebSocket connection from browser for WebRTC signaling.

        This is the main entry point for WebRTC streaming. It:
        1. Creates a session
        2. Connects to the camera's WebRTC endpoint
        3. Proxies signaling messages bidirectionally
        4. Manages session lifecycle

        Args:
            browser_ws: WebSocket connection from browser
            camera_ip: Camera IP address
            camera_port: Camera ONVIF port
            username: Camera username
            password: Camera password
            profile_token: Media profile token to stream
        """
        session_id = str(uuid4())
        session = WebRTCSession(
            session_id=session_id,
            camera_ip=camera_ip,
            camera_port=camera_port,
            profile_token=profile_token,
            browser_ws=browser_ws,
        )
        self.active_sessions[session_id] = session

        logger.info(f"[{session_id}] WebRTC session started for camera {camera_ip}:{camera_port}")

        try:
            # Send session info to browser
            await self._send_to_browser(session, {
                "type": "session",
                "sessionId": session_id,
                "iceServers": self.get_ice_servers_config(),
            })

            # Try to connect to camera's WebRTC endpoint
            camera_ws_url = self._get_camera_webrtc_url(camera_ip, camera_port)

            try:
                session.state = SignalingState.CONNECTING
                async with websockets.connect(
                    camera_ws_url,
                    ssl=self.ssl_context,
                    close_timeout=5,
                    ping_interval=20,
                    ping_timeout=10,
                ) as camera_ws:
                    session.camera_ws = camera_ws
                    session.state = SignalingState.CONNECTED

                    logger.info(f"[{session_id}] Connected to camera WebRTC endpoint")

                    # Register with camera
                    await self._register_with_camera(session, username, password)

                    # Proxy messages bidirectionally
                    await asyncio.gather(
                        self._proxy_browser_to_camera(session),
                        self._proxy_camera_to_browser(session),
                    )

            except (ConnectionRefusedError, OSError) as e:
                logger.warning(f"[{session_id}] Camera doesn't support WebRTC endpoint: {e}")
                # Fall back to browser-side WebRTC with RTSP
                await self._handle_rtsp_fallback(session, username, password)

            except WebSocketException as e:
                logger.error(f"[{session_id}] Camera WebSocket error: {e}")
                session.state = SignalingState.FAILED
                session.error = str(e)
                await self._send_to_browser(session, {
                    "type": "error",
                    "code": "CAMERA_CONNECTION_FAILED",
                    "message": f"Failed to connect to camera: {e}",
                })

        except ConnectionClosed:
            logger.info(f"[{session_id}] Browser disconnected")
        except Exception as e:
            logger.error(f"[{session_id}] Unexpected error: {e}", exc_info=True)
            session.state = SignalingState.FAILED
            session.error = str(e)
        finally:
            session.state = SignalingState.CLOSED
            self.active_sessions.pop(session_id, None)
            logger.info(f"[{session_id}] WebRTC session ended")

    def _get_camera_webrtc_url(self, ip: str, port: int) -> str:
        """Get camera's WebRTC WebSocket URL"""
        # ONVIF WebRTC typically uses wss://<ip>/onvif/webrtc
        # Some cameras may use different paths
        return f"wss://{ip}:{port}/onvif/webrtc"

    async def _register_with_camera(
        self,
        session: WebRTCSession,
        username: str,
        password: str,
    ) -> None:
        """Register with camera using ONVIF WebRTC authentication"""
        session.state = SignalingState.REGISTERING

        # Generate auth token using ONVIF WS-UsernameToken style
        nonce = secrets.token_bytes(16)
        created = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

        # Password digest = Base64(SHA1(nonce + created + password))
        digest_input = nonce + created.encode() + password.encode()
        password_digest = hashlib.sha1(digest_input).hexdigest()

        register_msg = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": JsonRpcMethod.REGISTER.value,
            "params": {
                "username": username,
                "passwordDigest": password_digest,
                "nonce": nonce.hex(),
                "created": created,
            }
        }

        await self._send_to_camera(session, register_msg)
        logger.debug(f"[{session.session_id}] Sent register request to camera")

    async def _proxy_browser_to_camera(self, session: WebRTCSession) -> None:
        """Forward messages from browser to camera"""
        try:
            async for message in session.browser_ws:
                if isinstance(message, bytes):
                    message = message.decode("utf-8")

                try:
                    msg = json.loads(message)
                    await self._handle_browser_message(session, msg)
                except json.JSONDecodeError:
                    logger.warning(f"[{session.session_id}] Invalid JSON from browser: {message[:100]}")

        except ConnectionClosed:
            logger.debug(f"[{session.session_id}] Browser connection closed")

    async def _proxy_camera_to_browser(self, session: WebRTCSession) -> None:
        """Forward messages from camera to browser"""
        if not session.camera_ws:
            return

        try:
            async for message in session.camera_ws:
                if isinstance(message, bytes):
                    message = message.decode("utf-8")

                try:
                    msg = json.loads(message)
                    await self._handle_camera_message(session, msg)
                except json.JSONDecodeError:
                    logger.warning(f"[{session.session_id}] Invalid JSON from camera: {message[:100]}")

        except ConnectionClosed:
            logger.debug(f"[{session.session_id}] Camera connection closed")

    async def _handle_browser_message(self, session: WebRTCSession, msg: Dict) -> None:
        """Handle message from browser"""
        msg_type = msg.get("type", msg.get("method", "unknown"))

        logger.debug(f"[{session.session_id}] Browser -> Camera: {msg_type}")

        if msg_type == "offer":
            # Browser sending SDP offer
            session.sdp_offer = msg.get("sdp")
            session.state = SignalingState.NEGOTIATING

            # Convert to JSON-RPC format for camera
            rpc_msg = {
                "jsonrpc": "2.0",
                "id": msg.get("id", int(time.time())),
                "method": JsonRpcMethod.OPEN.value,
                "params": {
                    "profileToken": session.profile_token,
                    "offer": {
                        "type": "offer",
                        "sdp": session.sdp_offer,
                    }
                }
            }
            await self._send_to_camera(session, rpc_msg)

        elif msg_type == "ice-candidate" or msg_type == "iceCandidate":
            # Browser sending ICE candidate
            candidate = msg.get("candidate")
            if candidate:
                session.ice_candidates_local.append(candidate)

                rpc_msg = {
                    "jsonrpc": "2.0",
                    "id": msg.get("id", int(time.time())),
                    "method": JsonRpcMethod.ADD_ICE_CANDIDATE.value,
                    "params": {
                        "candidate": candidate,
                    }
                }
                await self._send_to_camera(session, rpc_msg)

        elif msg_type == "close":
            # Browser requesting close
            rpc_msg = {
                "jsonrpc": "2.0",
                "id": msg.get("id", int(time.time())),
                "method": JsonRpcMethod.CLOSE.value,
                "params": {}
            }
            await self._send_to_camera(session, rpc_msg)

        else:
            # Forward other messages as-is (JSON-RPC format)
            if session.camera_ws:
                await self._send_to_camera(session, msg)

    async def _handle_camera_message(self, session: WebRTCSession, msg: Dict) -> None:
        """Handle message from camera"""
        # Check if it's a JSON-RPC response or notification
        if "result" in msg:
            # Response to our request
            result = msg.get("result", {})

            # Check for SDP answer in open response
            if "answer" in result:
                session.sdp_answer = result["answer"].get("sdp")
                session.state = SignalingState.STREAMING

                await self._send_to_browser(session, {
                    "type": "answer",
                    "sdp": session.sdp_answer,
                })
                logger.info(f"[{session.session_id}] Received SDP answer from camera")

            elif "registered" in result:
                session.state = SignalingState.REGISTERED
                logger.info(f"[{session.session_id}] Registered with camera")

                await self._send_to_browser(session, {
                    "type": "registered",
                    "configurations": result.get("configurations", []),
                })
            else:
                # Forward other results
                await self._send_to_browser(session, {
                    "type": "result",
                    "id": msg.get("id"),
                    "result": result,
                })

        elif "error" in msg:
            # Error response
            error = msg.get("error", {})
            session.error = error.get("message", "Unknown error")

            await self._send_to_browser(session, {
                "type": "error",
                "code": error.get("code", "UNKNOWN"),
                "message": session.error,
            })
            logger.warning(f"[{session.session_id}] Camera error: {session.error}")

        elif "method" in msg:
            # Notification from camera
            method = msg.get("method")
            params = msg.get("params", {})

            if method == JsonRpcMethod.ON_ICE_CANDIDATE.value:
                # Camera sending ICE candidate
                candidate = params.get("candidate")
                if candidate:
                    session.ice_candidates_remote.append(candidate)
                    await self._send_to_browser(session, {
                        "type": "ice-candidate",
                        "candidate": candidate,
                    })

            elif method == JsonRpcMethod.ON_OPEN.value:
                # Stream opened
                session.state = SignalingState.STREAMING
                await self._send_to_browser(session, {
                    "type": "stream-opened",
                    "params": params,
                })

            elif method == JsonRpcMethod.ON_CLOSE.value:
                # Stream closed
                await self._send_to_browser(session, {
                    "type": "stream-closed",
                    "reason": params.get("reason", "Unknown"),
                })

            elif method == JsonRpcMethod.ON_ERROR.value:
                # Stream error
                await self._send_to_browser(session, {
                    "type": "error",
                    "code": params.get("code", "STREAM_ERROR"),
                    "message": params.get("message", "Stream error"),
                })
            else:
                # Forward unknown notifications
                await self._send_to_browser(session, {
                    "type": "notification",
                    "method": method,
                    "params": params,
                })

    async def _handle_rtsp_fallback(
        self,
        session: WebRTCSession,
        username: str,
        password: str,
    ) -> None:
        """
        Handle cameras that don't support native WebRTC.

        Sends RTSP URL to browser for client-side WebRTC conversion
        using a media server or browser plugin.
        """
        logger.info(f"[{session.session_id}] Using RTSP fallback mode")

        # Get RTSP URL from camera via ONVIF
        from integrations.onvif_client import ONVIFClient

        try:
            client = ONVIFClient()
            camera = await client.connect_camera(
                session.camera_ip,
                session.camera_port,
                username,
                password,
            )

            # Get available profiles and find the best one
            profiles = await client.get_media_profiles(camera)
            profile_token = session.profile_token

            # If default token doesn't work, find first H.264 profile
            if profiles:
                # Prefer H.264 profile for better compatibility
                h264_profile = next(
                    (p for p in profiles if p.get("encoding") == "H264"),
                    None
                )
                if h264_profile:
                    profile_token = h264_profile.get("token", profile_token)
                    logger.info(f"[{session.session_id}] Using profile: {h264_profile.get('name')} ({profile_token})")
                elif profiles:
                    # Fall back to first available profile
                    profile_token = profiles[0].get("token", profile_token)
                    logger.info(f"[{session.session_id}] Using first profile: {profiles[0].get('name')} ({profile_token})")

            # Get stream URI
            stream_uri = await client.get_stream_uri(camera, profile_token)

            await self._send_to_browser(session, {
                "type": "rtsp-fallback",
                "message": "Camera does not support native WebRTC. Use RTSP stream.",
                "rtspUrl": stream_uri,
                "iceServers": self.get_ice_servers_config(),
                "hint": "Use a media server (e.g., Janus, mediasoup) or browser extension for RTSP-to-WebRTC conversion",
            })

            # Keep connection open for potential future use
            while True:
                try:
                    message = await asyncio.wait_for(
                        session.browser_ws.recv(),
                        timeout=30.0
                    )
                    # Handle any browser messages in fallback mode
                    msg = json.loads(message)
                    if msg.get("type") == "close":
                        break
                except asyncio.TimeoutError:
                    # Send keepalive
                    await self._send_to_browser(session, {"type": "ping"})
                except ConnectionClosed:
                    break

        except Exception as e:
            logger.error(f"[{session.session_id}] RTSP fallback failed: {e}")
            await self._send_to_browser(session, {
                "type": "error",
                "code": "RTSP_FALLBACK_FAILED",
                "message": f"Could not get RTSP URL: {e}",
            })

    async def _send_to_browser(self, session: WebRTCSession, msg: Dict) -> None:
        """Send message to browser WebSocket"""
        try:
            await session.browser_ws.send_text(json.dumps(msg))
        except Exception as e:
            logger.debug(f"[{session.session_id}] Failed to send to browser: {e}")

    async def _send_to_camera(self, session: WebRTCSession, msg: Dict) -> None:
        """Send message to camera WebSocket"""
        if session.camera_ws:
            try:
                await session.camera_ws.send(json.dumps(msg))
            except Exception as e:
                logger.debug(f"[{session.session_id}] Failed to send to camera: {e}")

    def get_active_sessions(self) -> List[Dict[str, Any]]:
        """Get list of active WebRTC sessions"""
        return [s.to_dict() for s in self.active_sessions.values()]

    def get_session(self, session_id: str) -> Optional[WebRTCSession]:
        """Get session by ID"""
        return self.active_sessions.get(session_id)

    async def close_session(self, session_id: str) -> bool:
        """Close a specific session"""
        session = self.active_sessions.get(session_id)
        if session:
            try:
                await self._send_to_browser(session, {"type": "close", "reason": "Server closed session"})
                if session.camera_ws:
                    await session.camera_ws.close()
            except Exception:
                pass
            self.active_sessions.pop(session_id, None)
            return True
        return False

    async def close_all_sessions(self) -> int:
        """Close all active sessions"""
        count = len(self.active_sessions)
        for session_id in list(self.active_sessions.keys()):
            await self.close_session(session_id)
        return count


# Global gateway instance
_webrtc_gateway: Optional[ONVIFWebRTCGateway] = None


def get_webrtc_gateway() -> ONVIFWebRTCGateway:
    """Get or create WebRTC gateway singleton"""
    global _webrtc_gateway
    if _webrtc_gateway is None:
        _webrtc_gateway = ONVIFWebRTCGateway()
    return _webrtc_gateway
