"""
Pytest configuration and fixtures for PlatoniCam tests.
"""

import pytest
import sys
from pathlib import Path

# Add backend to path for imports
backend_path = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_path))


@pytest.fixture
def sample_camera():
    """Sample camera data for testing."""
    return {
        "id": "CAM-001",
        "ip": "192.168.1.100",
        "location": "Main Entrance",
        "sceneType": "entrance",
        "purpose": "facial",
        "manufacturer": "Test",
        "model": "TestCam-1000"
    }


@pytest.fixture
def sample_capabilities():
    """Sample camera capabilities for testing."""
    return {
        "supportedCodecs": ["H.264", "H.265"],
        "supportedResolutions": ["1920x1080", "2560x1440", "3840x2160"],
        "maxFps": 30,
        "hasWdr": True,
        "hasIr": True
    }


@pytest.fixture
def sample_context():
    """Sample optimization context for testing."""
    return {
        "bandwidthLimitMbps": 8,
        "targetRetentionDays": 30,
        "sampleFrame": None
    }


@pytest.fixture
def sample_settings():
    """Sample recommended settings for testing."""
    return {
        "stream": {
            "resolution": "1920x1080",
            "codec": "H.265",
            "fps": 20,
            "bitrateMbps": 4,
            "bitrateMode": "VBR"
        },
        "exposure": {
            "mode": "Auto",
            "wdr": "Medium",
            "shutter": "1/250"
        },
        "lowLight": {
            "irMode": "Auto",
            "noiseReduction": "Medium"
        },
        "image": {
            "sharpness": 50,
            "contrast": 50,
            "saturation": 50
        }
    }
