# tests/backend/test_metadata_parser.py
"""
Tests for ONVIF Analytics Metadata Parser (Phase 4.2)
"""

import pytest
import sys
from pathlib import Path
from datetime import datetime

# Add backend to path
backend_path = Path(__file__).parent.parent.parent / "backend"
sys.path.insert(0, str(backend_path))

from integrations.metadata_parser import (
    MetadataParser,
    BoundingBox,
    DetectedObject,
    MotionRegion,
    AnalyticsFrame,
    ObjectClass,
    parse_analytics_metadata,
    get_metadata_parser,
)


class TestBoundingBox:
    """Tests for BoundingBox dataclass"""

    def test_creates_valid_bounding_box(self):
        """Should create bounding box with normalized coordinates"""
        bbox = BoundingBox(left=0.1, top=0.2, right=0.5, bottom=0.8)

        assert bbox.left == 0.1
        assert bbox.top == 0.2
        assert bbox.right == 0.5
        assert bbox.bottom == 0.8

    def test_calculates_width_and_height(self):
        """Should correctly calculate width and height"""
        bbox = BoundingBox(left=0.1, top=0.2, right=0.5, bottom=0.8)

        assert bbox.width == pytest.approx(0.4)
        assert bbox.height == pytest.approx(0.6)

    def test_calculates_center(self):
        """Should correctly calculate center point"""
        bbox = BoundingBox(left=0.0, top=0.0, right=1.0, bottom=1.0)

        center = bbox.center
        assert center[0] == pytest.approx(0.5)
        assert center[1] == pytest.approx(0.5)

    def test_calculates_area(self):
        """Should correctly calculate area"""
        bbox = BoundingBox(left=0.0, top=0.0, right=0.5, bottom=0.5)

        assert bbox.area == pytest.approx(0.25)

    def test_converts_to_pixels(self):
        """Should convert normalized coords to pixel values"""
        bbox = BoundingBox(left=0.1, top=0.2, right=0.5, bottom=0.8)

        pixels = bbox.to_pixels(width=1920, height=1080)

        assert pixels["x"] == 192  # 0.1 * 1920
        assert pixels["y"] == 216  # 0.2 * 1080
        assert pixels["width"] == 768  # 0.4 * 1920
        assert pixels["height"] == 648  # 0.6 * 1080

    def test_to_dict_returns_all_fields(self):
        """Should return dictionary with all fields"""
        bbox = BoundingBox(left=0.1, top=0.2, right=0.5, bottom=0.8)

        result = bbox.to_dict()

        assert "left" in result
        assert "top" in result
        assert "right" in result
        assert "bottom" in result
        assert "width" in result
        assert "height" in result

    def test_from_dict_parses_correctly(self):
        """Should parse bounding box from dictionary"""
        data = {"left": 0.1, "top": 0.2, "right": 0.5, "bottom": 0.8}

        bbox = BoundingBox.from_dict(data)

        assert bbox is not None
        assert bbox.left == 0.1
        assert bbox.bottom == 0.8

    def test_from_dict_handles_capitalized_keys(self):
        """Should handle capitalized key names"""
        data = {"Left": 0.1, "Top": 0.2, "Right": 0.5, "Bottom": 0.8}

        bbox = BoundingBox.from_dict(data)

        assert bbox is not None
        assert bbox.left == 0.1


class TestObjectClass:
    """Tests for ObjectClass enum"""

    def test_from_string_exact_match(self):
        """Should match exact class names"""
        assert ObjectClass.from_string("Human") == ObjectClass.HUMAN
        assert ObjectClass.from_string("Vehicle") == ObjectClass.VEHICLE
        assert ObjectClass.from_string("Face") == ObjectClass.FACE

    def test_from_string_case_insensitive(self):
        """Should match case-insensitively"""
        assert ObjectClass.from_string("human") == ObjectClass.HUMAN
        assert ObjectClass.from_string("VEHICLE") == ObjectClass.VEHICLE
        assert ObjectClass.from_string("fAcE") == ObjectClass.FACE

    def test_from_string_returns_unknown_for_invalid(self):
        """Should return UNKNOWN for unrecognized values"""
        assert ObjectClass.from_string("alien") == ObjectClass.UNKNOWN
        assert ObjectClass.from_string("") == ObjectClass.UNKNOWN
        assert ObjectClass.from_string(None) == ObjectClass.UNKNOWN


class TestDetectedObject:
    """Tests for DetectedObject dataclass"""

    def test_creates_detected_object(self):
        """Should create detected object with all fields"""
        bbox = BoundingBox(left=0.1, top=0.2, right=0.5, bottom=0.8)
        obj = DetectedObject(
            object_id="obj-1",
            object_class=ObjectClass.HUMAN,
            confidence=0.95,
            bounding_box=bbox,
        )

        assert obj.object_id == "obj-1"
        assert obj.object_class == ObjectClass.HUMAN
        assert obj.confidence == 0.95

    def test_to_dict_includes_all_fields(self):
        """Should include all fields in dictionary"""
        bbox = BoundingBox(left=0.1, top=0.2, right=0.5, bottom=0.8)
        obj = DetectedObject(
            object_id="obj-1",
            object_class=ObjectClass.VEHICLE,
            confidence=0.88,
            bounding_box=bbox,
            track_id="track-42",
        )

        result = obj.to_dict()

        assert result["objectId"] == "obj-1"
        assert result["class"] == "Vehicle"
        assert result["confidence"] == pytest.approx(0.88, rel=0.01)
        assert result["trackId"] == "track-42"
        assert "boundingBox" in result


class TestMetadataParser:
    """Tests for MetadataParser class"""

    @pytest.fixture
    def parser(self):
        return MetadataParser()

    def test_parse_xml_with_objects(self, parser):
        """Should parse XML metadata with detected objects"""
        xml_data = """<?xml version="1.0" encoding="UTF-8"?>
        <tt:Frame xmlns:tt="http://www.onvif.org/ver10/schema" UtcTime="2025-01-15T10:30:00Z">
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
        """

        frame = parser.parse_xml(xml_data)

        assert frame is not None
        assert len(frame.objects) == 1
        assert frame.objects[0].object_class == ObjectClass.HUMAN
        assert frame.objects[0].confidence == pytest.approx(0.95)

    def test_parse_xml_with_multiple_objects(self, parser):
        """Should parse multiple objects from XML"""
        xml_data = """<?xml version="1.0" encoding="UTF-8"?>
        <tt:Frame xmlns:tt="http://www.onvif.org/ver10/schema" UtcTime="2025-01-15T10:30:00Z">
            <tt:Object ObjectId="1">
                <tt:Appearance>
                    <tt:Shape>
                        <tt:BoundingBox left="0.1" top="0.1" right="0.2" bottom="0.3"/>
                    </tt:Shape>
                    <tt:Class>
                        <tt:Type Likelihood="0.9">Human</tt:Type>
                    </tt:Class>
                </tt:Appearance>
            </tt:Object>
            <tt:Object ObjectId="2">
                <tt:Appearance>
                    <tt:Shape>
                        <tt:BoundingBox left="0.5" top="0.5" right="0.8" bottom="0.9"/>
                    </tt:Shape>
                    <tt:Class>
                        <tt:Type Likelihood="0.85">Vehicle</tt:Type>
                    </tt:Class>
                </tt:Appearance>
            </tt:Object>
        </tt:Frame>
        """

        frame = parser.parse_xml(xml_data)

        assert frame is not None
        assert len(frame.objects) == 2

    def test_parse_xml_extracts_timestamp(self, parser):
        """Should extract UTC timestamp from frame"""
        xml_data = """<?xml version="1.0" encoding="UTF-8"?>
        <tt:Frame xmlns:tt="http://www.onvif.org/ver10/schema" UtcTime="2025-06-15T14:30:45Z">
        </tt:Frame>
        """

        frame = parser.parse_xml(xml_data)

        assert frame is not None
        assert frame.timestamp.year == 2025
        assert frame.timestamp.month == 6
        assert frame.timestamp.day == 15

    def test_parse_xml_returns_none_for_invalid(self, parser):
        """Should return None for invalid XML"""
        result = parser.parse_xml("not valid xml")
        assert result is None

    def test_parse_json_with_objects(self, parser):
        """Should parse JSON metadata with detected objects"""
        json_data = {
            "UtcTime": "2025-01-15T10:30:00Z",
            "Objects": [
                {
                    "ObjectId": "obj-1",
                    "Type": "Human",
                    "Likelihood": 0.92,
                    "BoundingBox": {
                        "left": 0.1,
                        "top": 0.2,
                        "right": 0.4,
                        "bottom": 0.7
                    }
                }
            ]
        }

        frame = parser.parse_json(json_data)

        assert frame is not None
        assert len(frame.objects) == 1
        assert frame.objects[0].object_class == ObjectClass.HUMAN
        assert frame.objects[0].confidence == pytest.approx(0.92)

    def test_parse_json_handles_motion_data(self, parser):
        """Should parse motion detection data from JSON"""
        json_data = {
            "UtcTime": "2025-01-15T10:30:00Z",
            "Data": {
                "IsMotion": True
            }
        }

        frame = parser.parse_json(json_data)

        assert frame is not None
        assert len(frame.motion_regions) == 1
        assert frame.motion_regions[0].active is True

    def test_parse_json_with_lowercase_keys(self, parser):
        """Should handle lowercase JSON keys"""
        json_data = {
            "timestamp": "2025-01-15T10:30:00Z",
            "objects": [
                {
                    "objectId": "1",
                    "class": "Vehicle",
                    "confidence": 0.88,
                    "boundingBox": {
                        "left": 0.2,
                        "top": 0.3,
                        "right": 0.6,
                        "bottom": 0.8
                    }
                }
            ]
        }

        frame = parser.parse_json(json_data)

        assert frame is not None
        assert len(frame.objects) == 1
        assert frame.objects[0].object_class == ObjectClass.VEHICLE


class TestAnalyticsFrame:
    """Tests for AnalyticsFrame dataclass"""

    def test_to_dict_includes_summary(self):
        """Should include object count and motion status in dict"""
        bbox = BoundingBox(left=0.1, top=0.2, right=0.5, bottom=0.8)
        obj = DetectedObject(
            object_id="1",
            object_class=ObjectClass.HUMAN,
            confidence=0.9,
            bounding_box=bbox,
        )
        motion = MotionRegion(region_id="m1", active=True)

        frame = AnalyticsFrame(
            timestamp=datetime.utcnow(),
            objects=[obj],
            motion_regions=[motion],
        )

        result = frame.to_dict()

        assert result["objectCount"] == 1
        assert result["hasMotion"] is True

    def test_has_motion_false_when_no_active_regions(self):
        """Should report hasMotion=False when no active regions"""
        motion = MotionRegion(region_id="m1", active=False)

        frame = AnalyticsFrame(
            timestamp=datetime.utcnow(),
            motion_regions=[motion],
        )

        result = frame.to_dict()
        assert result["hasMotion"] is False


class TestParseAnalyticsMetadata:
    """Tests for convenience parse function"""

    def test_parses_xml_string(self):
        """Should auto-detect and parse XML string"""
        xml_data = """<?xml version="1.0"?>
        <tt:Frame xmlns:tt="http://www.onvif.org/ver10/schema" UtcTime="2025-01-15T10:30:00Z">
        </tt:Frame>
        """

        result = parse_analytics_metadata(xml_data)
        assert result is not None

    def test_parses_json_dict(self):
        """Should auto-detect and parse JSON dict"""
        json_data = {
            "UtcTime": "2025-01-15T10:30:00Z",
            "Objects": []
        }

        result = parse_analytics_metadata(json_data)
        assert result is not None

    def test_parses_bytes(self):
        """Should auto-detect and parse bytes (RTP payload)"""
        xml_bytes = b"""<?xml version="1.0"?>
        <tt:Frame xmlns:tt="http://www.onvif.org/ver10/schema" UtcTime="2025-01-15T10:30:00Z">
        </tt:Frame>
        """

        result = parse_analytics_metadata(xml_bytes)
        assert result is not None


class TestGetMetadataParser:
    """Tests for singleton parser getter"""

    def test_returns_same_instance(self):
        """Should return same parser instance (singleton)"""
        parser1 = get_metadata_parser()
        parser2 = get_metadata_parser()

        assert parser1 is parser2
