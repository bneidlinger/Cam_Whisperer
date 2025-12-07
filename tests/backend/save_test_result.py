#!/usr/bin/env python3
"""
Helper script to save optimization test results

Usage:
    # Save from clipboard
    python save_test_result.py

    # Save from file
    python save_test_result.py response.json

    # Save with custom name
    python save_test_result.py --name "entrance_test_v2"
"""

import json
import sys
from pathlib import Path
from datetime import datetime
import pyperclip  # pip install pyperclip


def save_result(data: dict, name: str = None):
    """Save test result to ai_outputs folder"""

    # Create ai_outputs directory if needed
    outputs_dir = Path("ai_outputs")
    outputs_dir.mkdir(exist_ok=True)

    # Generate filename
    if name:
        filename = f"{name}.json"
    else:
        timestamp = int(datetime.now().timestamp() * 1000)
        filename = f"response_{timestamp}.json"

    filepath = outputs_dir / filename

    # Save JSON
    with open(filepath, "w") as f:
        json.dump(data, f, indent=2)

    print(f"[OK] Saved test result: {filepath}")

    # Show summary
    confidence = data.get("confidence", 0)
    ai_provider = data.get("aiProvider", "unknown")
    processing_time = data.get("processingTime", 0)

    print(f"\nSummary:")
    print(f"  AI Provider: {ai_provider}")
    print(f"  Confidence: {confidence:.2%}")
    print(f"  Processing Time: {processing_time:.2f}s")

    settings = data.get("recommendedSettings", {})
    stream = settings.get("stream", {})
    print(f"  Codec: {stream.get('codec')}")
    print(f"  Shutter: {settings.get('exposure', {}).get('shutter')}")

    print(f"\nRun tracker to update logs:")
    print(f"  python test_tracker.py")


def main():
    """Main function"""

    # Check for custom name
    custom_name = None
    if "--name" in sys.argv:
        name_idx = sys.argv.index("--name") + 1
        if name_idx < len(sys.argv):
            custom_name = sys.argv[name_idx]

    # Check if file provided
    if len(sys.argv) > 1 and not sys.argv[1].startswith("--"):
        input_file = sys.argv[1]
        print(f"Reading from file: {input_file}")

        with open(input_file, "r") as f:
            data = json.load(f)

    else:
        # Try to get from clipboard
        print("Reading from clipboard...")
        try:
            clipboard_text = pyperclip.paste()
            data = json.loads(clipboard_text)
            print("[OK] Parsed JSON from clipboard")
        except ImportError:
            print("Error: pyperclip not installed")
            print("Install with: pip install pyperclip")
            print("Or provide JSON file: python save_test_result.py response.json")
            sys.exit(1)
        except json.JSONDecodeError as e:
            print(f"Error: Invalid JSON in clipboard")
            print(f"  {e}")
            print("\nPaste the full JSON response from the API, then run this script.")
            sys.exit(1)

    # Save result
    save_result(data, custom_name)


if __name__ == "__main__":
    main()
