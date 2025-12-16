# backend/integrations/mqtt_events.py
"""
MQTT Event Bridge for ONVIF Cameras (Profile M)

Bridges ONVIF camera events to an MQTT broker for real-time notifications.
Replaces inefficient SOAP PullPoint polling with push-based pub/sub.

Phase 4: Profile M Analytics Integration

Architecture:
    Camera ----ONVIF Events----> Event Bridge ----MQTT----> Broker
                                      |
                                 PlatoniCam
                                      |
                              Subscribers (apps, alerts, analytics)

Benefits over PullPoint:
- Real-time delivery (vs polling delay)
- Lower network overhead
- Standard IoT integration pattern
- Serverless-friendly (can trigger Lambda/Functions)
"""

import asyncio
import json
import logging
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set
from uuid import uuid4

logger = logging.getLogger(__name__)

# MQTT client (paho-mqtt)
try:
    import paho.mqtt.client as mqtt
    from paho.mqtt.enums import CallbackAPIVersion
    MQTT_AVAILABLE = True
except ImportError:
    logger.warning("paho-mqtt not installed. Install with: pip install paho-mqtt>=2.0.0")
    MQTT_AVAILABLE = False
    mqtt = None
    CallbackAPIVersion = None


class EventType(str, Enum):
    """Common ONVIF event types (Profile M)"""
    MOTION = "tns1:RuleEngine/CellMotionDetector/Motion"
    MOTION_ALARM = "tns1:VideoSource/MotionAlarm"
    LINE_CROSSING = "tns1:RuleEngine/LineDetector/Crossed"
    INTRUSION = "tns1:RuleEngine/FieldDetector/ObjectsInside"
    TAMPERING = "tns1:VideoSource/GlobalSceneChange/ImagingService"
    FACE_DETECTED = "tns1:RuleEngine/FaceDetector/Detected"
    AUDIO_DETECTION = "tns1:AudioAnalytics/Audio/DetectedSound"
    DIGITAL_INPUT = "tns1:Device/Trigger/DigitalInput"
    RELAY_OUTPUT = "tns1:Device/Trigger/Relay"
    PTZ_PRESET = "tns1:PTZController/PTZPresets/Preset"
    RECORDING = "tns1:RecordingHistory/Track/State"
    STORAGE = "tns1:Device/HardwareFailure/StorageFailure"


@dataclass
class CameraEvent:
    """Represents a camera event received via MQTT or ONVIF"""
    event_id: str
    camera_id: str
    camera_ip: str
    topic: str
    event_type: Optional[EventType]
    timestamp: datetime
    data: Dict[str, Any]
    source_token: Optional[str] = None
    raw_payload: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "eventId": self.event_id,
            "cameraId": self.camera_id,
            "cameraIp": self.camera_ip,
            "topic": self.topic,
            "eventType": self.event_type.value if self.event_type else None,
            "timestamp": self.timestamp.isoformat() + "Z",
            "data": self.data,
            "sourceToken": self.source_token,
        }

    @classmethod
    def from_mqtt_payload(cls, camera_id: str, camera_ip: str, payload: dict) -> "CameraEvent":
        """Create CameraEvent from MQTT JSON payload"""
        topic = payload.get("Topic", payload.get("topic", "unknown"))

        # Try to match event type
        event_type = None
        for et in EventType:
            if et.value.lower() in topic.lower():
                event_type = et
                break

        # Parse timestamp
        timestamp_str = payload.get("UtcTime", payload.get("utcTime", payload.get("timestamp")))
        if timestamp_str:
            try:
                timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
            except ValueError:
                timestamp = datetime.utcnow()
        else:
            timestamp = datetime.utcnow()

        return cls(
            event_id=str(uuid4()),
            camera_id=camera_id,
            camera_ip=camera_ip,
            topic=topic,
            event_type=event_type,
            timestamp=timestamp,
            data=payload.get("Data", payload.get("data", {})),
            source_token=payload.get("Source", {}).get("VideoSourceToken"),
            raw_payload=json.dumps(payload),
        )


@dataclass
class MQTTBrokerConfig:
    """MQTT broker connection configuration"""
    host: str = "localhost"
    port: int = 1883
    username: Optional[str] = None
    password: Optional[str] = None
    use_tls: bool = False
    ca_cert_path: Optional[str] = None
    client_cert_path: Optional[str] = None
    client_key_path: Optional[str] = None
    keepalive: int = 60
    client_id: str = field(default_factory=lambda: f"platonicam-{uuid4().hex[:8]}")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "host": self.host,
            "port": self.port,
            "username": self.username,
            "useTls": self.use_tls,
            "clientId": self.client_id,
        }


class ONVIFEventBridge:
    """
    Bridge ONVIF cameras to MQTT broker for real-time events.

    Per ONVIF Profile M specification, cameras can be configured to publish
    events directly to an MQTT broker using the AddEventBroker command.

    This class:
    1. Configures cameras to publish to the MQTT broker
    2. Subscribes to camera event topics
    3. Processes and dispatches events to registered handlers
    """

    def __init__(self, broker_config: MQTTBrokerConfig):
        """
        Initialize the event bridge.

        Args:
            broker_config: MQTT broker connection configuration
        """
        if not MQTT_AVAILABLE:
            raise RuntimeError("paho-mqtt not installed. Install with: pip install paho-mqtt>=2.0.0")

        self.config = broker_config
        self.client: Optional[mqtt.Client] = None
        self.connected = False
        self.subscribed_topics: Set[str] = set()
        self.event_handlers: List[Callable[[CameraEvent], None]] = []
        self.camera_topics: Dict[str, str] = {}  # camera_id -> topic_prefix
        self._reconnect_task: Optional[asyncio.Task] = None

        # Event statistics
        self.stats = {
            "events_received": 0,
            "events_processed": 0,
            "events_dropped": 0,
            "last_event_time": None,
            "connected_since": None,
        }

    def _create_client(self) -> mqtt.Client:
        """Create and configure MQTT client"""
        client = mqtt.Client(
            callback_api_version=CallbackAPIVersion.VERSION2,
            client_id=self.config.client_id,
        )

        # Set credentials if provided
        if self.config.username:
            client.username_pw_set(self.config.username, self.config.password)

        # Configure TLS if enabled
        if self.config.use_tls:
            import ssl
            client.tls_set(
                ca_certs=self.config.ca_cert_path,
                certfile=self.config.client_cert_path,
                keyfile=self.config.client_key_path,
                cert_reqs=ssl.CERT_REQUIRED if self.config.ca_cert_path else ssl.CERT_NONE,
            )

        # Set callbacks
        client.on_connect = self._on_connect
        client.on_disconnect = self._on_disconnect
        client.on_message = self._on_message

        return client

    def _on_connect(self, client, userdata, flags, reason_code, properties=None):
        """Handle MQTT connection"""
        if reason_code == 0:
            self.connected = True
            self.stats["connected_since"] = datetime.utcnow().isoformat()
            logger.info(f"Connected to MQTT broker at {self.config.host}:{self.config.port}")

            # Resubscribe to topics on reconnect
            for topic in self.subscribed_topics:
                client.subscribe(topic)
                logger.info(f"Resubscribed to topic: {topic}")
        else:
            logger.error(f"MQTT connection failed with code: {reason_code}")

    def _on_disconnect(self, client, userdata, flags, reason_code, properties=None):
        """Handle MQTT disconnection"""
        self.connected = False
        logger.warning(f"Disconnected from MQTT broker: {reason_code}")

    def _on_message(self, client, userdata, msg):
        """Handle incoming MQTT message"""
        self.stats["events_received"] += 1

        try:
            # Parse topic to extract camera info
            topic_parts = msg.topic.split("/")

            # Expected topic format: platonicam/{camera_ip}/events/{event_type}
            # or custom: {prefix}/{camera_id}/{...}
            camera_id = "unknown"
            camera_ip = "unknown"

            if len(topic_parts) >= 2:
                if topic_parts[0] == "platonicam":
                    camera_ip = topic_parts[1]
                    camera_id = f"cam-{camera_ip.replace('.', '-')}"
                else:
                    camera_id = topic_parts[1]
                    # Try to find IP from our mapping
                    for cid, prefix in self.camera_topics.items():
                        if cid == camera_id or prefix in msg.topic:
                            camera_id = cid
                            break

            # Parse payload
            try:
                payload = json.loads(msg.payload.decode("utf-8"))
            except json.JSONDecodeError:
                # Might be XML or plain text
                payload = {"raw": msg.payload.decode("utf-8", errors="replace")}

            # Create event object
            event = CameraEvent.from_mqtt_payload(camera_id, camera_ip, payload)

            logger.debug(f"Received event: {event.event_type} from {camera_ip}")

            # Dispatch to handlers
            for handler in self.event_handlers:
                try:
                    handler(event)
                except Exception as e:
                    logger.error(f"Event handler error: {e}")

            self.stats["events_processed"] += 1
            self.stats["last_event_time"] = datetime.utcnow().isoformat()

        except Exception as e:
            logger.error(f"Failed to process MQTT message: {e}")
            self.stats["events_dropped"] += 1

    async def connect(self) -> bool:
        """
        Connect to the MQTT broker.

        Returns:
            True if connection successful
        """
        try:
            self.client = self._create_client()
            self.client.connect_async(
                self.config.host,
                self.config.port,
                keepalive=self.config.keepalive
            )
            self.client.loop_start()

            # Wait for connection
            for _ in range(50):  # 5 second timeout
                if self.connected:
                    return True
                await asyncio.sleep(0.1)

            logger.warning("MQTT connection timeout")
            return False

        except Exception as e:
            logger.error(f"Failed to connect to MQTT broker: {e}")
            return False

    def disconnect(self):
        """Disconnect from MQTT broker"""
        if self.client:
            self.client.loop_stop()
            self.client.disconnect()
            self.connected = False
            logger.info("Disconnected from MQTT broker")

    def subscribe(self, topic: str, qos: int = 1) -> bool:
        """
        Subscribe to an MQTT topic.

        Args:
            topic: Topic pattern (supports wildcards: +, #)
            qos: Quality of Service level (0, 1, or 2)

        Returns:
            True if subscription successful
        """
        if not self.client or not self.connected:
            logger.warning("Cannot subscribe: not connected")
            return False

        try:
            result, _ = self.client.subscribe(topic, qos)
            if result == mqtt.MQTT_ERR_SUCCESS:
                self.subscribed_topics.add(topic)
                logger.info(f"Subscribed to topic: {topic}")
                return True
            else:
                logger.error(f"Subscribe failed with code: {result}")
                return False
        except Exception as e:
            logger.error(f"Subscribe error: {e}")
            return False

    def unsubscribe(self, topic: str) -> bool:
        """Unsubscribe from an MQTT topic"""
        if not self.client:
            return False

        try:
            self.client.unsubscribe(topic)
            self.subscribed_topics.discard(topic)
            logger.info(f"Unsubscribed from topic: {topic}")
            return True
        except Exception as e:
            logger.error(f"Unsubscribe error: {e}")
            return False

    def add_event_handler(self, handler: Callable[[CameraEvent], None]):
        """
        Register an event handler callback.

        Args:
            handler: Function that receives CameraEvent objects
        """
        self.event_handlers.append(handler)
        logger.info(f"Added event handler: {handler.__name__}")

    def remove_event_handler(self, handler: Callable[[CameraEvent], None]):
        """Remove an event handler"""
        if handler in self.event_handlers:
            self.event_handlers.remove(handler)

    async def configure_camera_mqtt(
        self,
        camera_ip: str,
        camera_port: int,
        username: str,
        password: str,
        topic_prefix: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Configure a camera to publish events to the MQTT broker.

        Uses ONVIF AddEventBroker command (Profile M).

        Args:
            camera_ip: Camera IP address
            camera_port: Camera ONVIF port
            username: Camera username
            password: Camera password
            topic_prefix: MQTT topic prefix (default: platonicam/{camera_ip})

        Returns:
            Result dictionary with success status and details
        """
        from integrations.onvif_client import ONVIFClient

        result = {
            "success": False,
            "camera_ip": camera_ip,
            "broker_host": self.config.host,
            "topic_prefix": topic_prefix or f"platonicam/{camera_ip}",
            "error": None,
        }

        if topic_prefix is None:
            topic_prefix = f"platonicam/{camera_ip}"

        try:
            client = ONVIFClient()
            camera = await client.connect_camera(
                ip=camera_ip,
                port=camera_port,
                username=username,
                password=password
            )

            # Get event service
            loop = asyncio.get_event_loop()

            try:
                event_service = camera.create_events_service()
            except Exception as e:
                result["error"] = f"Camera does not support Events service: {e}"
                logger.warning(result["error"])
                return result

            # Build MQTT broker address
            protocol = "mqtts" if self.config.use_tls else "mqtt"
            broker_address = f"{protocol}://{self.config.host}:{self.config.port}"

            # Create event broker configuration
            event_broker_config = {
                "Address": broker_address,
                "TopicPrefix": topic_prefix,
            }

            # Add credentials if configured
            if self.config.username:
                event_broker_config["UserName"] = self.config.username
                event_broker_config["Password"] = self.config.password

            # Try to add event broker (Profile M command)
            try:
                await loop.run_in_executor(
                    client.executor,
                    event_service.AddEventBroker,
                    {"EventBroker": event_broker_config}
                )
                result["success"] = True
                result["topic_prefix"] = topic_prefix

                # Track this camera
                camera_id = f"cam-{camera_ip.replace('.', '-')}"
                self.camera_topics[camera_id] = topic_prefix

                # Subscribe to this camera's events
                self.subscribe(f"{topic_prefix}/#")

                logger.info(f"Configured camera {camera_ip} to publish events to {broker_address}")

            except Exception as e:
                error_str = str(e).lower()
                if "not implemented" in error_str or "not supported" in error_str:
                    result["error"] = "Camera does not support MQTT event publishing (Profile M required)"
                elif "already" in error_str:
                    result["error"] = "Event broker already configured on camera"
                    result["success"] = True  # Not really an error
                else:
                    result["error"] = f"AddEventBroker failed: {e}"
                logger.warning(f"Failed to configure MQTT on camera: {result['error']}")

            return result

        except Exception as e:
            result["error"] = str(e)
            logger.error(f"Failed to configure camera MQTT: {e}")
            return result

    async def remove_camera_mqtt(
        self,
        camera_ip: str,
        camera_port: int,
        username: str,
        password: str,
    ) -> Dict[str, Any]:
        """
        Remove MQTT event broker configuration from camera.

        Args:
            camera_ip: Camera IP address
            camera_port: Camera ONVIF port
            username: Camera username
            password: Camera password

        Returns:
            Result dictionary
        """
        from integrations.onvif_client import ONVIFClient

        result = {
            "success": False,
            "camera_ip": camera_ip,
            "error": None,
        }

        try:
            client = ONVIFClient()
            camera = await client.connect_camera(
                ip=camera_ip,
                port=camera_port,
                username=username,
                password=password
            )

            loop = asyncio.get_event_loop()
            event_service = camera.create_events_service()

            # Get current brokers
            try:
                brokers = await loop.run_in_executor(
                    client.executor,
                    event_service.GetEventBrokers
                )

                # Delete each broker
                for broker in brokers:
                    address = broker.Address if hasattr(broker, 'Address') else str(broker)
                    await loop.run_in_executor(
                        client.executor,
                        event_service.DeleteEventBroker,
                        {"Address": address}
                    )
                    logger.info(f"Removed event broker: {address}")

                result["success"] = True

            except Exception as e:
                if "not implemented" in str(e).lower():
                    result["error"] = "Camera does not support MQTT event management"
                else:
                    result["error"] = str(e)

            # Remove from tracking
            camera_id = f"cam-{camera_ip.replace('.', '-')}"
            if camera_id in self.camera_topics:
                topic = self.camera_topics.pop(camera_id)
                self.unsubscribe(f"{topic}/#")

            return result

        except Exception as e:
            result["error"] = str(e)
            logger.error(f"Failed to remove camera MQTT config: {e}")
            return result

    def get_status(self) -> Dict[str, Any]:
        """Get current bridge status and statistics"""
        return {
            "connected": self.connected,
            "broker": {
                "host": self.config.host,
                "port": self.config.port,
                "clientId": self.config.client_id,
            },
            "subscriptions": list(self.subscribed_topics),
            "cameras": list(self.camera_topics.keys()),
            "handlers": len(self.event_handlers),
            "stats": self.stats,
        }


# Singleton instance
_event_bridge: Optional[ONVIFEventBridge] = None


def get_event_bridge() -> Optional[ONVIFEventBridge]:
    """Get the global event bridge instance"""
    return _event_bridge


async def init_event_bridge(config: MQTTBrokerConfig) -> ONVIFEventBridge:
    """
    Initialize the global event bridge.

    Args:
        config: MQTT broker configuration

    Returns:
        Initialized ONVIFEventBridge instance
    """
    global _event_bridge

    if _event_bridge is not None:
        _event_bridge.disconnect()

    _event_bridge = ONVIFEventBridge(config)
    await _event_bridge.connect()

    return _event_bridge


def shutdown_event_bridge():
    """Shutdown the global event bridge"""
    global _event_bridge

    if _event_bridge is not None:
        _event_bridge.disconnect()
        _event_bridge = None
