# tests/backend/test_mqtt_events.py
"""
Tests for MQTT Event Bridge (Phase 4.1)
"""

import pytest
import sys
import json
from pathlib import Path
from datetime import datetime
from unittest.mock import patch, MagicMock, AsyncMock

# Add backend to path
backend_path = Path(__file__).parent.parent.parent / "backend"
sys.path.insert(0, str(backend_path))


class TestCameraEvent:
    """Tests for CameraEvent dataclass"""

    def test_import_camera_event(self):
        """Should be able to import CameraEvent"""
        from integrations.mqtt_events import CameraEvent
        assert CameraEvent is not None

    def test_creates_camera_event(self):
        """Should create camera event with all fields"""
        from integrations.mqtt_events import CameraEvent, EventType

        event = CameraEvent(
            event_id="evt-123",
            camera_id="cam-192-168-1-100",
            camera_ip="192.168.1.100",
            topic="platonicam/192.168.1.100/motion",
            event_type=EventType.MOTION,
            timestamp=datetime.utcnow(),
            data={"IsMotion": True},
        )

        assert event.event_id == "evt-123"
        assert event.camera_ip == "192.168.1.100"
        assert event.event_type == EventType.MOTION

    def test_to_dict_serializes_correctly(self):
        """Should serialize to dictionary with camelCase keys"""
        from integrations.mqtt_events import CameraEvent, EventType

        event = CameraEvent(
            event_id="evt-123",
            camera_id="cam-1",
            camera_ip="192.168.1.100",
            topic="test/topic",
            event_type=EventType.MOTION,
            timestamp=datetime(2025, 1, 15, 10, 30, 0),
            data={"IsMotion": True},
        )

        result = event.to_dict()

        assert result["eventId"] == "evt-123"
        assert result["cameraId"] == "cam-1"
        assert result["cameraIp"] == "192.168.1.100"
        assert "2025-01-15" in result["timestamp"]

    def test_from_mqtt_payload_parses_motion_event(self):
        """Should parse motion event from MQTT payload"""
        from integrations.mqtt_events import CameraEvent, EventType

        payload = {
            "Topic": "tns1:RuleEngine/CellMotionDetector/Motion",
            "UtcTime": "2025-01-15T10:30:00Z",
            "Source": {"VideoSourceToken": "vs-1"},
            "Data": {"IsMotion": True},
        }

        event = CameraEvent.from_mqtt_payload("cam-1", "192.168.1.100", payload)

        assert event.camera_id == "cam-1"
        assert event.camera_ip == "192.168.1.100"
        assert event.event_type == EventType.MOTION
        assert event.data["IsMotion"] is True


class TestEventType:
    """Tests for EventType enum"""

    def test_motion_event_type(self):
        """Should have MOTION event type"""
        from integrations.mqtt_events import EventType

        assert EventType.MOTION.value == "tns1:RuleEngine/CellMotionDetector/Motion"

    def test_line_crossing_event_type(self):
        """Should have LINE_CROSSING event type"""
        from integrations.mqtt_events import EventType

        assert EventType.LINE_CROSSING.value == "tns1:RuleEngine/LineDetector/Crossed"

    def test_all_event_types_have_values(self):
        """All event types should have string values"""
        from integrations.mqtt_events import EventType

        for event_type in EventType:
            assert isinstance(event_type.value, str)
            assert len(event_type.value) > 0


class TestMQTTBrokerConfig:
    """Tests for MQTTBrokerConfig dataclass"""

    def test_creates_config_with_defaults(self):
        """Should create config with default values"""
        from integrations.mqtt_events import MQTTBrokerConfig

        config = MQTTBrokerConfig()

        assert config.host == "localhost"
        assert config.port == 1883
        assert config.use_tls is False

    def test_creates_config_with_custom_values(self):
        """Should create config with custom values"""
        from integrations.mqtt_events import MQTTBrokerConfig

        config = MQTTBrokerConfig(
            host="mqtt.example.com",
            port=8883,
            username="user",
            password="pass",
            use_tls=True,
        )

        assert config.host == "mqtt.example.com"
        assert config.port == 8883
        assert config.username == "user"
        assert config.use_tls is True

    def test_to_dict_excludes_password(self):
        """Should exclude password from dict output"""
        from integrations.mqtt_events import MQTTBrokerConfig

        config = MQTTBrokerConfig(
            host="localhost",
            username="user",
            password="secret",
        )

        result = config.to_dict()

        assert "host" in result
        assert "username" in result
        assert "password" not in result

    def test_generates_unique_client_id(self):
        """Should generate unique client ID by default"""
        from integrations.mqtt_events import MQTTBrokerConfig

        config1 = MQTTBrokerConfig()
        config2 = MQTTBrokerConfig()

        assert config1.client_id != config2.client_id
        assert config1.client_id.startswith("platonicam-")


class TestONVIFEventBridge:
    """Tests for ONVIFEventBridge class"""

    @pytest.fixture
    def mock_mqtt_available(self):
        """Mock MQTT as available"""
        with patch.dict('sys.modules', {'paho.mqtt.client': MagicMock()}):
            yield

    def test_import_event_bridge(self):
        """Should be able to import ONVIFEventBridge"""
        from integrations.mqtt_events import ONVIFEventBridge, MQTT_AVAILABLE

        # May or may not be available depending on installation
        if MQTT_AVAILABLE:
            assert ONVIFEventBridge is not None

    @pytest.mark.skipif(
        not pytest.importorskip("paho.mqtt.client", reason="paho-mqtt not installed"),
        reason="paho-mqtt required"
    )
    def test_creates_event_bridge(self):
        """Should create event bridge with config"""
        from integrations.mqtt_events import ONVIFEventBridge, MQTTBrokerConfig

        config = MQTTBrokerConfig(host="localhost", port=1883)
        bridge = ONVIFEventBridge(config)

        assert bridge.config.host == "localhost"
        assert bridge.connected is False
        assert len(bridge.event_handlers) == 0

    @pytest.mark.skipif(
        not pytest.importorskip("paho.mqtt.client", reason="paho-mqtt not installed"),
        reason="paho-mqtt required"
    )
    def test_add_event_handler(self):
        """Should register event handlers"""
        from integrations.mqtt_events import ONVIFEventBridge, MQTTBrokerConfig

        config = MQTTBrokerConfig()
        bridge = ONVIFEventBridge(config)

        def handler(event):
            pass

        bridge.add_event_handler(handler)

        assert len(bridge.event_handlers) == 1

    @pytest.mark.skipif(
        not pytest.importorskip("paho.mqtt.client", reason="paho-mqtt not installed"),
        reason="paho-mqtt required"
    )
    def test_remove_event_handler(self):
        """Should remove event handlers"""
        from integrations.mqtt_events import ONVIFEventBridge, MQTTBrokerConfig

        config = MQTTBrokerConfig()
        bridge = ONVIFEventBridge(config)

        def handler(event):
            pass

        bridge.add_event_handler(handler)
        bridge.remove_event_handler(handler)

        assert len(bridge.event_handlers) == 0

    @pytest.mark.skipif(
        not pytest.importorskip("paho.mqtt.client", reason="paho-mqtt not installed"),
        reason="paho-mqtt required"
    )
    def test_get_status_returns_stats(self):
        """Should return status with statistics"""
        from integrations.mqtt_events import ONVIFEventBridge, MQTTBrokerConfig

        config = MQTTBrokerConfig(host="test.local")
        bridge = ONVIFEventBridge(config)

        status = bridge.get_status()

        assert "connected" in status
        assert "broker" in status
        assert "stats" in status
        assert status["broker"]["host"] == "test.local"


class TestModuleFunctions:
    """Tests for module-level functions"""

    def test_get_event_bridge_initially_none(self):
        """Should return None initially"""
        from integrations.mqtt_events import get_event_bridge

        # Reset singleton for test
        import integrations.mqtt_events as module
        module._event_bridge = None

        result = get_event_bridge()
        assert result is None

    def test_shutdown_event_bridge_handles_none(self):
        """Should handle shutdown when bridge is None"""
        from integrations.mqtt_events import shutdown_event_bridge

        # Reset singleton for test
        import integrations.mqtt_events as module
        module._event_bridge = None

        # Should not raise
        shutdown_event_bridge()


class TestMQTTAvailability:
    """Tests for MQTT availability detection"""

    def test_mqtt_available_flag_exists(self):
        """Should have MQTT_AVAILABLE flag"""
        from integrations.mqtt_events import MQTT_AVAILABLE

        assert isinstance(MQTT_AVAILABLE, bool)
