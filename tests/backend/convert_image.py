#!/usr/bin/env python3
"""
Convert an image file to base64 data URL for CamOpt AI testing

Usage:
    python convert_image.py camera_snapshot.jpg
    python convert_image.py camera_snapshot.jpg --output request.json
"""

import base64
import sys
import json
from pathlib import Path


def image_to_base64_url(image_path: str) -> str:
    """Convert image file to base64 data URL"""

    # Read image file
    with open(image_path, "rb") as f:
        image_data = f.read()

    # Encode to base64
    b64_data = base64.b64encode(image_data).decode("utf-8")

    # Determine media type
    ext = Path(image_path).suffix.lower()
    media_type_map = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp"
    }
    media_type = media_type_map.get(ext, "image/jpeg")

    # Create data URL
    data_url = f"data:{media_type};base64,{b64_data}"

    return data_url


def create_sample_request(image_path: str) -> dict:
    """Create a sample OptimizeRequest with the image"""

    data_url = image_to_base64_url(image_path)

    request = {
        "camera": {
            "id": "test-camera-with-image",
            "ip": "192.168.1.100",
            "vendor": "Hanwha",
            "model": "QNV-7080R",
            "location": "Test Location",
            "sceneType": "entrance",
            "purpose": "facial"
        },
        "capabilities": {
            "maxResolution": "3840x2160",
            "supportedCodecs": ["H.264", "H.265"],
            "maxFps": 30,
            "wdrLevels": ["Off", "Low", "Medium", "High"],
            "irModes": ["Off", "Auto", "On"],
            "hasLPRMode": False
        },
        "currentSettings": {
            "stream": {
                "resolution": "1920x1080",
                "codec": "H.264",
                "fps": 30,
                "bitrateMbps": 6.0
            },
            "exposure": {
                "shutter": "1/30",
                "wdr": "Off"
            },
            "lowLight": {
                "irMode": "Auto"
            }
        },
        "context": {
            "bandwidthLimitMbps": 4.0,
            "targetRetentionDays": 30,
            "notes": "Testing with actual camera snapshot",
            "sampleFrame": data_url
        }
    }

    return request


def main():
    """Main function"""

    if len(sys.argv) < 2:
        print("Usage: python convert_image.py <image_file> [--output <json_file>]")
        print("\nExample:")
        print("  python convert_image.py camera_snapshot.jpg")
        print("  python convert_image.py camera_snapshot.jpg --output request.json")
        sys.exit(1)

    image_path = sys.argv[1]

    # Check if file exists
    if not Path(image_path).exists():
        print(f"Error: File not found: {image_path}")
        sys.exit(1)

    print(f"Converting {image_path} to base64...")

    # Check file size
    file_size_mb = Path(image_path).stat().st_size / (1024 * 1024)
    if file_size_mb > 10:
        print(f"Warning: Image is {file_size_mb:.1f} MB (max recommended: 10 MB)")
        print("Consider resizing the image for faster API calls.")

    # Convert to data URL
    data_url = image_to_base64_url(image_path)

    print(f"✓ Converted successfully")
    print(f"  Size: {file_size_mb:.2f} MB")
    print(f"  Base64 length: {len(data_url):,} characters")

    # Check if --output flag
    if "--output" in sys.argv:
        output_idx = sys.argv.index("--output") + 1
        if output_idx < len(sys.argv):
            output_path = sys.argv[output_idx]
            request = create_sample_request(image_path)

            with open(output_path, "w") as f:
                json.dump(request, f, indent=2)

            print(f"\n✓ Full request saved to: {output_path}")
            print(f"\nTest it with:")
            print(f'  curl -X POST http://localhost:8000/api/optimize \\')
            print(f'    -H "Content-Type: application/json" \\')
            print(f'    -d @{output_path}')
        else:
            print("Error: --output requires a filename")
            sys.exit(1)
    else:
        # Just print the data URL (truncated)
        print(f"\nData URL (first 100 chars):")
        print(f"  {data_url[:100]}...")
        print(f"\nTo create a full API request:")
        print(f"  python convert_image.py {image_path} --output request.json")


if __name__ == "__main__":
    main()
