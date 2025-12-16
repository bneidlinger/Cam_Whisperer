# backend/integrations/metadata_parser.py
"""
ONVIF Analytics Metadata Parser (Profile M)

Parses analytics metadata from camera streams including:
- Object detection bounding boxes
- Object classification (human, vehicle, face)
- Motion regions
- Line crossing events
- Scene analytics

Phase 4: Profile M Analytics Integration

The metadata is typically delivered as:
1. XML frames embedded in RTP stream (synchronized with video)
2. MQTT JSON payloads (real-time push)
3. ONVIF Events service responses

Coordinates are normalized (0.0 to 1.0) relative to video resolution.
"""

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
from xml.etree import ElementTree as ET

logger = logging.getLogger(__name__)

# ONVIF namespace prefixes
NAMESPACES = {
    "tt": "http://www.onvif.org/ver10/schema",
    "tns1": "http://www.onvif.org/ver10/topics",
    "wsnt": "http://docs.oasis-open.org/wsn/b-2",
    "wsa": "http://www.w3.org/2005/08/addressing",
}


class ObjectClass(str, Enum):
    """Standard object classifications (Profile M)"""
    HUMAN = "Human"
    FACE = "Face"
    BODY = "Body"
    VEHICLE = "Vehicle"
    CAR = "Car"
    TRUCK = "Truck"
    MOTORCYCLE = "Motorcycle"
    BICYCLE = "Bicycle"
    ANIMAL = "Animal"
    LICENSE_PLATE = "LicensePlate"
    BAG = "Bag"
    UNKNOWN = "Unknown"

    @classmethod
    def from_string(cls, value: str) -> "ObjectClass":
        """Parse object class from string, case-insensitive"""
        if not value:
            return cls.UNKNOWN
        normalized = value.lower().replace("_", "").replace("-", "")
        for obj_class in cls:
            if obj_class.value.lower() == normalized:
                return obj_class
        # Try partial match
        for obj_class in cls:
            if normalized in obj_class.value.lower():
                return obj_class
        return cls.UNKNOWN


@dataclass
class BoundingBox:
    """
    Normalized bounding box coordinates.

    All values are 0.0 to 1.0 relative to video resolution.
    This ensures bounding boxes remain valid if resolution changes.
    """
    left: float
    top: float
    right: float
    bottom: float

    @property
    def width(self) -> float:
        return self.right - self.left

    @property
    def height(self) -> float:
        return self.bottom - self.top

    @property
    def center(self) -> Tuple[float, float]:
        return ((self.left + self.right) / 2, (self.top + self.bottom) / 2)

    @property
    def area(self) -> float:
        return self.width * self.height

    def to_pixels(self, width: int, height: int) -> Dict[str, int]:
        """Convert normalized coordinates to pixel values"""
        return {
            "x": int(self.left * width),
            "y": int(self.top * height),
            "width": int(self.width * width),
            "height": int(self.height * height),
        }

    def to_dict(self) -> Dict[str, float]:
        return {
            "left": round(self.left, 4),
            "top": round(self.top, 4),
            "right": round(self.right, 4),
            "bottom": round(self.bottom, 4),
            "width": round(self.width, 4),
            "height": round(self.height, 4),
        }

    @classmethod
    def from_xml(cls, element: ET.Element) -> Optional["BoundingBox"]:
        """Parse BoundingBox from ONVIF XML element"""
        try:
            return cls(
                left=float(element.get("left", element.get("Left", 0))),
                top=float(element.get("top", element.get("Top", 0))),
                right=float(element.get("right", element.get("Right", 0))),
                bottom=float(element.get("bottom", element.get("Bottom", 0))),
            )
        except (ValueError, TypeError) as e:
            logger.warning(f"Failed to parse bounding box: {e}")
            return None

    @classmethod
    def from_dict(cls, data: Dict) -> Optional["BoundingBox"]:
        """Parse BoundingBox from dictionary"""
        try:
            # Support both camelCase and snake_case
            return cls(
                left=float(data.get("left", data.get("Left", 0))),
                top=float(data.get("top", data.get("Top", 0))),
                right=float(data.get("right", data.get("Right", 0))),
                bottom=float(data.get("bottom", data.get("Bottom", 0))),
            )
        except (ValueError, TypeError, KeyError):
            return None


@dataclass
class DetectedObject:
    """Represents a detected object in a video frame"""
    object_id: str
    object_class: ObjectClass
    confidence: float  # 0.0 to 1.0
    bounding_box: BoundingBox
    timestamp: Optional[datetime] = None
    attributes: Dict[str, Any] = field(default_factory=dict)

    # Optional tracking info
    track_id: Optional[str] = None
    velocity: Optional[Tuple[float, float]] = None  # (vx, vy) normalized per second

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "objectId": self.object_id,
            "class": self.object_class.value,
            "confidence": round(self.confidence, 3),
            "boundingBox": self.bounding_box.to_dict(),
        }
        if self.timestamp:
            result["timestamp"] = self.timestamp.isoformat() + "Z"
        if self.attributes:
            result["attributes"] = self.attributes
        if self.track_id:
            result["trackId"] = self.track_id
        if self.velocity:
            result["velocity"] = {"vx": self.velocity[0], "vy": self.velocity[1]}
        return result


@dataclass
class MotionRegion:
    """Represents a motion detection region"""
    region_id: str
    active: bool
    bounding_box: Optional[BoundingBox] = None
    sensitivity: Optional[float] = None  # 0.0 to 1.0
    polygon: Optional[List[Tuple[float, float]]] = None  # Custom shape

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "regionId": self.region_id,
            "active": self.active,
        }
        if self.bounding_box:
            result["boundingBox"] = self.bounding_box.to_dict()
        if self.sensitivity is not None:
            result["sensitivity"] = round(self.sensitivity, 3)
        if self.polygon:
            result["polygon"] = [{"x": p[0], "y": p[1]} for p in self.polygon]
        return result


@dataclass
class AnalyticsFrame:
    """
    Represents a single frame of analytics metadata.

    Synchronized with video via UTC timestamp.
    """
    timestamp: datetime
    source_token: Optional[str] = None
    objects: List[DetectedObject] = field(default_factory=list)
    motion_regions: List[MotionRegion] = field(default_factory=list)
    scene_mode: Optional[str] = None
    raw_xml: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat() + "Z",
            "sourceToken": self.source_token,
            "objects": [obj.to_dict() for obj in self.objects],
            "motionRegions": [mr.to_dict() for mr in self.motion_regions],
            "sceneMode": self.scene_mode,
            "objectCount": len(self.objects),
            "hasMotion": any(mr.active for mr in self.motion_regions),
        }


class MetadataParser:
    """
    Parser for ONVIF analytics metadata (Profile M).

    Handles both XML (from RTP stream) and JSON (from MQTT) formats.
    """

    def __init__(self):
        self.object_counter = 0

    def parse_xml(self, xml_data: str) -> Optional[AnalyticsFrame]:
        """
        Parse ONVIF XML metadata frame.

        Expected format (from Profile M specification):
        <tt:Frame UtcTime="2025-01-15T10:30:00Z">
            <tt:Object ObjectId="42">
                <tt:Appearance>
                    <tt:Shape>
                        <tt:BoundingBox left="0.1" top="0.2" right="0.3" bottom="0.6"/>
                    </tt:Shape>
                    <tt:Class>
                        <tt:Type Likelihood="0.95">Human</tt:Type>
                    </tt:Class>
                </tt:Appearance>
            </tt:Object>
        </tt:Frame>

        Args:
            xml_data: XML string from metadata stream

        Returns:
            Parsed AnalyticsFrame or None if parsing fails
        """
        try:
            # Handle namespace prefixes
            # Register namespaces to preserve prefixes
            for prefix, uri in NAMESPACES.items():
                ET.register_namespace(prefix, uri)

            root = ET.fromstring(xml_data)

            # Find Frame element (might be root or nested)
            frame_elem = root
            if not root.tag.endswith("Frame"):
                frame_elem = root.find(".//tt:Frame", NAMESPACES)
                if frame_elem is None:
                    frame_elem = root.find(".//{http://www.onvif.org/ver10/schema}Frame")

            if frame_elem is None:
                # Try without namespace
                frame_elem = root.find(".//Frame")
                if frame_elem is None:
                    logger.debug("No Frame element found in metadata")
                    return None

            # Parse timestamp
            utc_time = frame_elem.get("UtcTime", frame_elem.get("utcTime"))
            if utc_time:
                try:
                    timestamp = datetime.fromisoformat(utc_time.replace("Z", "+00:00"))
                except ValueError:
                    timestamp = datetime.utcnow()
            else:
                timestamp = datetime.utcnow()

            frame = AnalyticsFrame(
                timestamp=timestamp,
                source_token=frame_elem.get("VideoSourceToken"),
                raw_xml=xml_data,
            )

            # Parse objects - try multiple XPath patterns
            # Use full namespace URI first (most reliable with ElementTree)
            obj_elements = frame_elem.findall(".//{http://www.onvif.org/ver10/schema}Object")
            if not obj_elements:
                obj_elements = frame_elem.findall(".//tt:Object", NAMESPACES)
            if not obj_elements:
                obj_elements = frame_elem.findall(".//Object")

            for obj_elem in obj_elements:
                obj = self._parse_object_xml(obj_elem)
                if obj:
                    frame.objects.append(obj)

            # Parse motion regions - try multiple XPath patterns
            motion_elements = frame_elem.findall(".//tt:Transformation", NAMESPACES)
            if not motion_elements:
                motion_elements = frame_elem.findall(".//MotionRegion")

            for motion_elem in motion_elements:
                motion = self._parse_motion_region_xml(motion_elem)
                if motion:
                    frame.motion_regions.append(motion)

            return frame

        except ET.ParseError as e:
            logger.warning(f"XML parse error: {e}")
            return None
        except Exception as e:
            logger.error(f"Metadata parse error: {e}")
            return None

    def _parse_object_xml(self, elem: ET.Element) -> Optional[DetectedObject]:
        """Parse a single Object element from XML"""
        try:
            object_id = elem.get("ObjectId", elem.get("objectId", str(self.object_counter)))
            self.object_counter += 1

            # Find bounding box - use full namespace URI first (most reliable)
            bbox_elem = elem.find(".//{http://www.onvif.org/ver10/schema}BoundingBox")
            if bbox_elem is None:
                bbox_elem = elem.find(".//tt:BoundingBox", NAMESPACES)
            if bbox_elem is None:
                bbox_elem = elem.find(".//BoundingBox")
            if bbox_elem is None:
                return None

            bbox = BoundingBox.from_xml(bbox_elem)
            if not bbox:
                return None

            # Find class/type - use full namespace URI first (most reliable)
            obj_class = ObjectClass.UNKNOWN
            confidence = 0.5

            type_elem = elem.find(".//{http://www.onvif.org/ver10/schema}Type")
            if type_elem is None:
                type_elem = elem.find(".//tt:Type", NAMESPACES)
            if type_elem is None:
                type_elem = elem.find(".//Type")
            if type_elem is not None:
                obj_class = ObjectClass.from_string(type_elem.text or "")
                likelihood = type_elem.get("Likelihood", type_elem.get("likelihood"))
                if likelihood:
                    try:
                        confidence = float(likelihood)
                    except ValueError:
                        pass

            # Parse additional attributes
            attributes = {}
            attr_elements = elem.findall(".//tt:Attribute", NAMESPACES)
            if not attr_elements:
                attr_elements = elem.findall(".//Attribute")
            for attr_elem in attr_elements:
                name = attr_elem.get("Name", attr_elem.get("name"))
                value = attr_elem.get("Value", attr_elem.get("value", attr_elem.text))
                if name and value:
                    attributes[name] = value

            return DetectedObject(
                object_id=object_id,
                object_class=obj_class,
                confidence=confidence,
                bounding_box=bbox,
                attributes=attributes,
            )

        except Exception as e:
            logger.warning(f"Failed to parse object: {e}")
            return None

    def _parse_motion_region_xml(self, elem: ET.Element) -> Optional[MotionRegion]:
        """Parse motion region from XML"""
        try:
            region_id = elem.get("RegionId", elem.get("regionId", "motion-0"))

            # Check if motion is active
            state_elem = elem.find(".//State") or elem.find(".//tt:State", NAMESPACES)
            active = True
            if state_elem is not None:
                active = state_elem.text.lower() in ("true", "1", "active")

            # Parse bounds
            bbox = None
            bbox_elem = elem.find(".//BoundingBox") or elem.find(".//tt:BoundingBox", NAMESPACES)
            if bbox_elem is not None:
                bbox = BoundingBox.from_xml(bbox_elem)

            return MotionRegion(
                region_id=region_id,
                active=active,
                bounding_box=bbox,
            )

        except Exception as e:
            logger.warning(f"Failed to parse motion region: {e}")
            return None

    def parse_json(self, json_data: Dict) -> Optional[AnalyticsFrame]:
        """
        Parse JSON analytics metadata (from MQTT or API).

        Supports various JSON formats from different camera vendors.

        Args:
            json_data: Dictionary from JSON payload

        Returns:
            Parsed AnalyticsFrame or None
        """
        try:
            # Parse timestamp
            timestamp_str = (
                json_data.get("UtcTime") or
                json_data.get("utcTime") or
                json_data.get("timestamp") or
                json_data.get("Timestamp")
            )
            if timestamp_str:
                try:
                    timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
                except ValueError:
                    timestamp = datetime.utcnow()
            else:
                timestamp = datetime.utcnow()

            frame = AnalyticsFrame(
                timestamp=timestamp,
                source_token=json_data.get("VideoSourceToken", json_data.get("sourceToken")),
            )

            # Parse objects (various formats)
            objects_data = (
                json_data.get("Objects") or
                json_data.get("objects") or
                json_data.get("detections") or
                json_data.get("Detections") or
                []
            )

            for obj_data in objects_data:
                obj = self._parse_object_json(obj_data)
                if obj:
                    frame.objects.append(obj)

            # Check for single object format
            if not frame.objects and "BoundingBox" in json_data:
                obj = self._parse_object_json(json_data)
                if obj:
                    frame.objects.append(obj)

            # Parse motion data
            motion_data = json_data.get("Data", {}).get("IsMotion")
            if motion_data is not None:
                frame.motion_regions.append(MotionRegion(
                    region_id="motion-default",
                    active=bool(motion_data),
                ))

            return frame

        except Exception as e:
            logger.error(f"JSON metadata parse error: {e}")
            return None

    def _parse_object_json(self, data: Dict) -> Optional[DetectedObject]:
        """Parse a single object from JSON data"""
        try:
            # Get bounding box
            bbox_data = (
                data.get("BoundingBox") or
                data.get("boundingBox") or
                data.get("bbox") or
                data
            )
            bbox = BoundingBox.from_dict(bbox_data)
            if not bbox:
                return None

            # Get class
            class_str = (
                data.get("Type") or
                data.get("type") or
                data.get("class") or
                data.get("Class") or
                data.get("label") or
                "Unknown"
            )
            obj_class = ObjectClass.from_string(class_str)

            # Get confidence
            confidence = float(
                data.get("Likelihood") or
                data.get("likelihood") or
                data.get("confidence") or
                data.get("Confidence") or
                data.get("score") or
                0.5
            )

            object_id = str(
                data.get("ObjectId") or
                data.get("objectId") or
                data.get("id") or
                self.object_counter
            )
            self.object_counter += 1

            return DetectedObject(
                object_id=object_id,
                object_class=obj_class,
                confidence=confidence,
                bounding_box=bbox,
                track_id=data.get("trackId", data.get("TrackId")),
            )

        except Exception as e:
            logger.warning(f"Failed to parse JSON object: {e}")
            return None

    def parse_rtp_metadata(self, rtp_payload: bytes) -> Optional[AnalyticsFrame]:
        """
        Parse metadata from RTP payload.

        The metadata is typically embedded as XML in the RTP payload,
        either as a separate track or in SEI NAL units for H.264/H.265.

        Args:
            rtp_payload: Raw RTP payload bytes

        Returns:
            Parsed AnalyticsFrame or None
        """
        try:
            # Try to decode as UTF-8 XML
            xml_data = rtp_payload.decode("utf-8", errors="ignore")

            # Look for XML content
            if "<" in xml_data and ">" in xml_data:
                # Extract XML portion (might have binary prefix)
                xml_start = xml_data.find("<?xml")
                if xml_start == -1:
                    xml_start = xml_data.find("<tt:")
                if xml_start == -1:
                    xml_start = xml_data.find("<Frame")

                if xml_start >= 0:
                    xml_data = xml_data[xml_start:]
                    return self.parse_xml(xml_data)

            return None

        except Exception as e:
            logger.debug(f"Failed to parse RTP metadata: {e}")
            return None


# Singleton parser instance
_parser: Optional[MetadataParser] = None


def get_metadata_parser() -> MetadataParser:
    """Get the global metadata parser instance"""
    global _parser
    if _parser is None:
        _parser = MetadataParser()
    return _parser


def parse_analytics_metadata(data: Any) -> Optional[AnalyticsFrame]:
    """
    Convenience function to parse metadata from various formats.

    Args:
        data: XML string, JSON dict, or bytes

    Returns:
        Parsed AnalyticsFrame or None
    """
    parser = get_metadata_parser()

    if isinstance(data, bytes):
        return parser.parse_rtp_metadata(data)
    elif isinstance(data, str):
        return parser.parse_xml(data)
    elif isinstance(data, dict):
        return parser.parse_json(data)
    else:
        logger.warning(f"Unknown metadata format: {type(data)}")
        return None
