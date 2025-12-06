#!/usr/bin/env python3
"""
CamOpt AI Test Tracker

Scans ai_outputs folder and creates comprehensive test tracking logs.
Tracks all optimization tests, analyzes trends, and generates reports.

Usage:
    python test_tracker.py                    # Scan and update logs
    python test_tracker.py --report           # Generate markdown report
    python test_tracker.py --analyze          # Show statistics
"""

import json
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any
from collections import Counter


class TestTracker:
    """Track and analyze CamOpt AI optimization tests"""

    def __init__(self, outputs_dir: str = "ai_outputs"):
        """Initialize tracker"""
        self.outputs_dir = Path(outputs_dir)
        self.log_file = self.outputs_dir / "test_log.json"
        self.report_file = self.outputs_dir / "TEST_REPORT.md"

        # Create directory if it doesn't exist
        self.outputs_dir.mkdir(exist_ok=True)

    def scan_test_results(self) -> List[Dict[str, Any]]:
        """Scan ai_outputs folder for all test result JSON files"""

        if not self.outputs_dir.exists():
            print(f"Directory not found: {self.outputs_dir}")
            return []

        # Find all JSON files
        json_files = sorted(self.outputs_dir.glob("response_*.json"))

        if not json_files:
            print(f"No test results found in {self.outputs_dir}")
            return []

        print(f"Found {len(json_files)} test result(s)")

        results = []
        for json_file in json_files:
            try:
                with open(json_file, "r") as f:
                    data = json.load(f)

                # Extract metadata
                test_entry = self._extract_metadata(data, json_file)
                results.append(test_entry)

                print(f"  [OK] {json_file.name}")

            except Exception as e:
                print(f"  [ERROR] {json_file.name}: {e}")

        return results

    def _extract_metadata(self, response: Dict[str, Any], file_path: Path) -> Dict[str, Any]:
        """Extract key metadata from a test response"""

        settings = response.get("recommendedSettings", {})
        stream = settings.get("stream", {})
        exposure = settings.get("exposure", {})
        low_light = settings.get("lowLight", {})

        # Extract timestamp from filename (response_1764994222876.json)
        filename = file_path.stem
        timestamp_ms = filename.split("_")[1] if "_" in filename else "0"

        try:
            timestamp = datetime.fromtimestamp(int(timestamp_ms) / 1000)
            timestamp_str = timestamp.isoformat()
        except:
            timestamp_str = response.get("generatedAt", "unknown")

        return {
            "test_id": file_path.stem,
            "timestamp": timestamp_str,
            "file": file_path.name,
            "aiProvider": response.get("aiProvider", "unknown"),
            "confidence": response.get("confidence", 0.0),
            "processingTime": response.get("processingTime", 0.0),
            "warnings": response.get("warnings", []),
            "warningCount": len(response.get("warnings", [])),
            "settings": {
                "codec": stream.get("codec"),
                "resolution": stream.get("resolution"),
                "fps": stream.get("fps"),
                "bitrate": stream.get("bitrateMbps"),
                "shutter": exposure.get("shutter"),
                "wdr": exposure.get("wdr"),
                "gainLimit": exposure.get("gainLimit"),
                "irMode": low_light.get("irMode"),
                "noiseReduction": low_light.get("noiseReduction"),
            },
            "explanation_length": len(response.get("explanation", "")),
            "explanation_preview": response.get("explanation", "")[:200] + "...",
        }

    def save_log(self, test_entries: List[Dict[str, Any]]):
        """Save test log to JSON file"""

        log_data = {
            "generated": datetime.now().isoformat(),
            "totalTests": len(test_entries),
            "tests": test_entries,
        }

        with open(self.log_file, "w") as f:
            json.dump(log_data, f, indent=2)

        print(f"\n[OK] Saved test log: {self.log_file}")

    def generate_report(self, test_entries: List[Dict[str, Any]]):
        """Generate human-readable markdown report"""

        report_lines = [
            "# CamOpt AI - Test Results Report",
            "",
            f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"**Total Tests:** {len(test_entries)}",
            "",
            "---",
            "",
        ]

        # Statistics
        report_lines.extend(self._generate_statistics(test_entries))

        # Individual test results
        report_lines.extend([
            "",
            "---",
            "",
            "## Individual Test Results",
            "",
        ])

        for i, test in enumerate(test_entries, 1):
            report_lines.extend(self._format_test_entry(i, test))

        # Write report
        report_content = "\n".join(report_lines)
        with open(self.report_file, "w", encoding="utf-8") as f:
            f.write(report_content)

        print(f"[OK] Generated report: {self.report_file}")

    def _generate_statistics(self, tests: List[Dict[str, Any]]) -> List[str]:
        """Generate statistics section"""

        lines = [
            "## Statistics",
            "",
            "### Overall Metrics",
            "",
        ]

        if not tests:
            lines.append("*No test data available*")
            return lines

        # Calculate stats
        avg_confidence = sum(t["confidence"] for t in tests) / len(tests)
        avg_processing_time = sum(t["processingTime"] for t in tests) / len(tests)
        total_warnings = sum(t["warningCount"] for t in tests)

        ai_providers = Counter(t["aiProvider"] for t in tests)
        codecs = Counter(t["settings"]["codec"] for t in tests)
        shutters = Counter(t["settings"]["shutter"] for t in tests)
        wdr_settings = Counter(t["settings"]["wdr"] for t in tests)

        lines.extend([
            f"- **Average Confidence:** {avg_confidence:.2%}",
            f"- **Average Processing Time:** {avg_processing_time:.2f}s",
            f"- **Total Warnings:** {total_warnings}",
            "",
            "### AI Provider Usage",
            "",
        ])

        for provider, count in ai_providers.most_common():
            pct = count / len(tests) * 100
            lines.append(f"- **{provider}:** {count} ({pct:.1f}%)")

        lines.extend([
            "",
            "### Common Recommendations",
            "",
            "**Codecs:**",
        ])

        for codec, count in codecs.most_common():
            lines.append(f"- {codec}: {count}")

        lines.extend([
            "",
            "**Shutter Speeds:**",
        ])

        for shutter, count in shutters.most_common():
            lines.append(f"- {shutter}: {count}")

        lines.extend([
            "",
            "**WDR Settings:**",
        ])

        for wdr, count in wdr_settings.most_common():
            lines.append(f"- {wdr}: {count}")

        return lines

    def _format_test_entry(self, index: int, test: Dict[str, Any]) -> List[str]:
        """Format a single test entry for the report"""

        timestamp = test["timestamp"][:19]  # Trim milliseconds

        lines = [
            f"### Test #{index}: {test['test_id']}",
            "",
            f"**Timestamp:** {timestamp}",
            f"**AI Provider:** `{test['aiProvider']}`",
            f"**Confidence:** {test['confidence']:.2%}",
            f"**Processing Time:** {test['processingTime']:.2f}s",
            f"**Warnings:** {test['warningCount']}",
            "",
            "**Recommended Settings:**",
            "",
            "| Setting | Value |",
            "|---------|-------|",
            f"| Codec | {test['settings']['codec']} |",
            f"| Resolution | {test['settings']['resolution']} |",
            f"| FPS | {test['settings']['fps']} |",
            f"| Bitrate | {test['settings']['bitrate']} Mbps |",
            f"| Shutter | {test['settings']['shutter']} |",
            f"| WDR | {test['settings']['wdr']} |",
            f"| Gain Limit | {test['settings']['gainLimit']} |",
            f"| IR Mode | {test['settings']['irMode']} |",
            f"| Noise Reduction | {test['settings']['noiseReduction']} |",
            "",
            "**Explanation Preview:**",
            "",
            f"> {test['explanation_preview']}",
            "",
            "---",
            "",
        ]

        return lines

    def analyze(self, test_entries: List[Dict[str, Any]]):
        """Print analysis to console"""

        if not test_entries:
            print("No test data to analyze")
            return

        print("\n" + "=" * 60)
        print("CamOpt AI - Test Analysis")
        print("=" * 60)

        avg_confidence = sum(t["confidence"] for t in test_entries) / len(test_entries)
        avg_processing = sum(t["processingTime"] for t in test_entries) / len(test_entries)

        print(f"\nTotal Tests: {len(test_entries)}")
        print(f"Average Confidence: {avg_confidence:.2%}")
        print(f"Average Processing Time: {avg_processing:.2f}s")

        # Most common settings
        codecs = Counter(t["settings"]["codec"] for t in test_entries)
        shutters = Counter(t["settings"]["shutter"] for t in test_entries)

        print(f"\nMost Common Codec: {codecs.most_common(1)[0][0]}")
        print(f"Most Common Shutter: {shutters.most_common(1)[0][0]}")

        # Confidence trend
        print("\nConfidence by Test:")
        for i, test in enumerate(test_entries, 1):
            print(f"  Test {i}: {test['confidence']:.2%}")

        print("\n" + "=" * 60)


def main():
    """Main function"""

    tracker = TestTracker()

    # Parse arguments
    generate_report = "--report" in sys.argv
    analyze = "--analyze" in sys.argv

    # Scan test results
    print("Scanning ai_outputs folder...")
    test_entries = tracker.scan_test_results()

    if not test_entries:
        print("No test results found. Run some optimization tests first!")
        return

    # Save log
    tracker.save_log(test_entries)

    # Generate report if requested
    if generate_report or len(sys.argv) == 1:
        tracker.generate_report(test_entries)

    # Analyze if requested
    if analyze or len(sys.argv) == 1:
        tracker.analyze(test_entries)

    print("\n[SUCCESS] Test tracking complete!")


if __name__ == "__main__":
    main()
