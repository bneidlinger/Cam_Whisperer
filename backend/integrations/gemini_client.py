# backend/integrations/gemini_client.py
"""
Google Gemini Vision API Client for camera optimization
Uses Google's Gemini 2.5 with vision capabilities via google-genai SDK
"""

from google import genai
from google.genai import types
import json
import base64
from typing import Dict, Any, Optional, Tuple
import logging

from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class GeminiVisionClient:
    """Client for interacting with Google Gemini Vision API"""

    def __init__(self):
        """Initialize Gemini client with API key from settings"""
        self.client = genai.Client(api_key=settings.google_api_key)
        self.model = settings.gemini_model
        self.max_tokens = settings.gemini_max_tokens
        self.temperature = settings.gemini_temperature

    def optimize_camera_settings(
        self,
        camera_context: Dict[str, Any],
        current_settings: Dict[str, Any],
        capabilities: Dict[str, Any],
        constraints: Dict[str, Any],
        sample_frame: Optional[str] = None,
        datasheet_specs: Optional[Dict[str, Any]] = None,
    ) -> Tuple[Dict[str, Any], float, str, list]:
        """
        Generate optimal camera settings using Gemini Vision

        Args:
            camera_context: Camera info (id, location, scene_type, purpose)
            current_settings: Current camera configuration
            capabilities: Hardware capabilities
            constraints: Bandwidth/retention constraints
            sample_frame: Base64-encoded image (optional)
            datasheet_specs: Camera datasheet specifications (optional)

        Returns:
            Tuple of (recommended_settings, confidence, explanation, warnings)
        """
        try:
            # Build the prompt (reuse same structure as Claude)
            prompt = self._build_optimization_prompt(
                camera_context, current_settings, capabilities, constraints, datasheet_specs
            )

            # Build content parts for Gemini
            contents = []

            # Add image if provided (Gemini needs raw bytes, not base64 string)
            if sample_frame:
                image_bytes, mime_type = self._extract_base64_image(sample_frame)
                if image_bytes:
                    logger.debug(f"Adding image with media type: {mime_type}")
                    contents.append(
                        types.Part.from_bytes(
                            data=image_bytes,
                            mime_type=mime_type,
                        )
                    )

            # Add text prompt
            contents.append(prompt)

            logger.info(
                f"Calling Gemini Vision API for camera {camera_context.get('id')}"
            )

            # Call Gemini API
            response = self.client.models.generate_content(
                model=self.model,
                contents=contents,
                config=types.GenerateContentConfig(
                    max_output_tokens=self.max_tokens,
                    temperature=self.temperature,
                )
            )

            # Extract response text
            response_text = response.text

            logger.debug(f"Gemini response: {response_text[:500]}...")

            # Parse the JSON response
            settings_data = self._parse_gemini_response(response_text)

            # Extract components
            recommended_settings = {
                "stream": settings_data.get("stream", current_settings.get("stream")),
                "exposure": settings_data.get(
                    "exposure", current_settings.get("exposure")
                ),
                "lowLight": settings_data.get(
                    "lowLight", current_settings.get("lowLight")
                ),
                "image": settings_data.get("image", current_settings.get("image", {})),
            }

            explanation = settings_data.get(
                "explanation", "AI-generated optimization settings."
            )

            # Extract warnings from Gemini's response
            ai_warnings = settings_data.get("warnings", [])
            if isinstance(ai_warnings, list):
                # Filter out placeholder text
                ai_warnings = [
                    w for w in ai_warnings
                    if w and "List any" not in w and len(w) > 5
                ]
            else:
                ai_warnings = []

            # Calculate confidence based on completeness and constraints
            confidence = self._calculate_confidence(
                settings_data, constraints, capabilities
            )

            logger.info(
                f"Gemini optimization complete. Confidence: {confidence:.2f}, Warnings: {len(ai_warnings)}"
            )

            return recommended_settings, confidence, explanation, ai_warnings

        except Exception as e:
            logger.error(f"Gemini Vision API error: {str(e)}", exc_info=True)
            raise

    def _build_optimization_prompt(
        self,
        camera_context: Dict[str, Any],
        current_settings: Dict[str, Any],
        capabilities: Dict[str, Any],
        constraints: Dict[str, Any],
        datasheet_specs: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Build the optimization prompt for Gemini"""

        scene_type = camera_context.get("sceneType", "unknown")
        purpose = camera_context.get("purpose", "overview")
        location = camera_context.get("location", "unspecified location")
        bandwidth_limit = constraints.get("bandwidthLimitMbps", "unlimited")
        retention_days = constraints.get("targetRetentionDays", "unspecified")

        # Build datasheet section if specs are available
        datasheet_section = ""
        if datasheet_specs:
            # Format datasheet specs for the prompt
            specs_text = json.dumps(datasheet_specs, indent=2)
            datasheet_section = f"""

MANUFACTURER DATASHEET SPECIFICATIONS:
The following specifications are from the official camera datasheet. Use these to inform your recommendations,
especially for maximum supported values, sensor capabilities, and manufacturer-recommended settings.
{specs_text}
"""

        prompt = f"""You are an expert surveillance camera optimization engineer with 20+ years of field experience in video management systems, camera configuration, and evidence-quality video capture.

CAMERA CONTEXT:
- Location: {location}
- Scene Type: {scene_type}
- Primary Purpose: {purpose}
- Camera Model: {camera_context.get('model', 'unknown')}
- Manufacturer: {camera_context.get('manufacturer', 'unknown')}

SENSOR TECHNOLOGY DETECTION:
Identify the sensor technology from the model name or datasheet specs and apply appropriate strategy:

- **ColorVu/Full-Color** (keywords: ColorVu, full color, 24/7 color):
  Optimized for preserving color in low light. Strategy: Manage exposure triangle to keep
  camera in color mode as long as possible. Avoid switching to IR/B&W. Use lower DNR to
  preserve color fidelity. These cameras have large aperture lenses and high-sensitivity sensors.

- **Starlight/Darkfighter/LightHunter** (keywords: Starlight, Darkfighter, LightHunter, ultra low-light):
  Maximum low-light sensitivity for B&W clarity. Strategy: Prioritize sensitivity, use higher
  DNR levels to manage noise. Accept B&W mode for best low-light performance. These cameras
  excel at long-range detection in near-darkness.

- **Standard IR cameras**:
  Traditional day/night cameras with IR illumination. Strategy: Balance IR intensity with
  scene requirements. Use moderate DNR. IR mode Auto is typically best.

- **WDR Type** (if identifiable):
  True WDR (hardware) vs Digital WDR (D-WDR/software). True WDR handles high-contrast scenes
  better with less processing overhead. D-WDR consumes CPU resources that may impact
  concurrent analytics performance.
{datasheet_section}
CURRENT SETTINGS:
{json.dumps(current_settings, indent=2)}

HARDWARE CAPABILITIES:
{json.dumps(capabilities, indent=2)}

CONSTRAINTS:
- Bandwidth Limit: {bandwidth_limit} Mbps
- Retention Target: {retention_days} days

CODEC SELECTION STRATEGY:
When recommending video codec, consider computational load vs compression efficiency:

- **H.265 (HEVC)**: RECOMMENDED DEFAULT for real-time edge streaming.
  ~50% better compression than H.264 with manageable encoding load.
  Integrated in ONVIF Profile T, broad compatibility.

- **H.264 (AVC)**: Use when camera has limited processing power, runs
  concurrent edge analytics, or for maximum compatibility with older VMS.
  Lower compression but minimal CPU impact.

- **H.266 (VVC)**: AVOID for real-time streaming. Encoding is 27-174x slower
  than AV1. Only suitable for archival streams or static scenes where
  latency is irrelevant. Check if camera actually supports this.

- **AV1**: Good compression but CPU-intensive encoding. Better suited for
  server-side transcoding than edge encoding. Rare in surveillance cameras.

Rule: If camera runs edge analytics (AI detection), prefer H.264 or H.265
to leave CPU headroom. Never recommend VVC for real-time monitoring.

TASK:
Analyze the camera context and generate optimal settings that:
1. Maximize evidence quality for the stated purpose ({purpose})
2. Stay within bandwidth and storage constraints
3. Handle the scene type appropriately ({scene_type})
4. Prevent common deployment mistakes (motion blur, excessive noise, poor WDR config)
5. Consider codec computational load vs edge analytics requirements

SCENE TYPE GUIDELINES:
- "entrance": Enable WDR for glass/bright backgrounds, faster shutter for faces
- "parking": License plate optimization - very fast shutter (1/500+), high FPS
- "hallway": Balance motion clarity with low-light performance
- "perimeter": Prioritize detection over identification, wider FOV
- "cashwrap": High detail for transactions, good color reproduction

PURPOSE GUIDELINES (with constraint hierarchy):
- "facial": Shutter 1/250 minimum (NON-NEGOTIABLE), 20+ FPS, optimize for skin tones.
  Use Shutter Priority mode. Moderate gain limit. Light DNR to preserve facial detail.

- "plates" (LPR/ANPR): This is the most constrained purpose:
  * Shutter 1/500+ (NON-NEGOTIABLE) - motion freeze is absolute priority
  * WDR OFF (prevents ghosting artifacts on moving plates - critical for OCR)
  * HLC ON (masks headlight glare)
  * Use Shutter Priority mode - let camera auto-adjust gain/iris
  * Accept higher gain/noise - noise is preferable to motion blur for OCR accuracy
  * H.265 for bandwidth efficiency
  * Note: Physical installation constraints (angle ±5°, offset <15°) are critical

- "overview": Broader coverage, lower FPS acceptable (10-15), can use slower shutter

- "evidence": Prioritize quality over bandwidth, high bitrate, CBR mode for consistent quality

- "intrusion": Prioritize detection over identification, higher FPS for motion capture

Return your recommendations in this EXACT JSON structure (no additional text):

{{
  "stream": {{
    "resolution": "1920x1080",
    "codec": "H.265",
    "fps": 20,
    "bitrateMbps": 3.5,
    "bitrateMode": "VBR",
    "gopSize": 40,
    "profile": "Main"
  }},
  "exposure": {{
    "mode": "Auto",
    "shutter": "1/250",
    "iris": "Auto",
    "gainLimit": 36,
    "wdr": "High",
    "blc": "Off",
    "hlc": "Off"
  }},
  "lowLight": {{
    "irMode": "Auto",
    "irIntensity": 50,
    "dayNightMode": "Auto",
    "dnr": "Medium",
    "slowShutter": "Off",
    "sensitivity": "Medium"
  }},
  "image": {{
    "brightness": 50,
    "contrast": 55,
    "saturation": 50,
    "sharpness": 60,
    "whiteBalance": "Auto",
    "defog": "Off"
  }},
  "warnings": [
    "List any constraint violations, capability limitations, or concerns here"
  ],
  "explanation": "2-3 sentence technical explanation of key recommendations and trade-offs. Reference scene analysis if image provided."
}}

CRITICAL: Return ONLY valid JSON. No markdown code blocks, no extra text, just the JSON object.
"""

        return prompt

    def _extract_base64_image(self, data_url: str) -> Tuple[Optional[bytes], Optional[str]]:
        """
        Extract image bytes and media type from data URL.
        Gemini API requires raw bytes, not base64 strings.

        Args:
            data_url: Data URL like "data:image/png;base64,iVBORw0..."

        Returns:
            Tuple of (image_bytes, media_type) or (None, None) if invalid
        """
        try:
            if "base64," in data_url:
                # Parse data URL format: data:image/jpeg;base64,<data>
                parts = data_url.split("base64,")
                base64_data = parts[1]

                # Extract media type from the prefix
                prefix = parts[0]  # "data:image/jpeg;"
                media_type = "image/jpeg"  # default

                if prefix.startswith("data:"):
                    # Extract media type between "data:" and ";"
                    type_part = prefix[5:]  # Remove "data:"
                    if ";" in type_part:
                        media_type = type_part.split(";")[0]
                    elif type_part:
                        media_type = type_part

                # Validate media type is an image type Gemini supports
                supported_types = ["image/jpeg", "image/png", "image/gif", "image/webp"]
                if media_type not in supported_types:
                    logger.warning(f"Unsupported media type {media_type}, defaulting to image/jpeg")
                    media_type = "image/jpeg"

                # Decode base64 to bytes (Gemini needs bytes, not base64 string)
                image_bytes = base64.b64decode(base64_data)
                return image_bytes, media_type

            # Raw base64 without data URL prefix - assume JPEG
            image_bytes = base64.b64decode(data_url)
            return image_bytes, "image/jpeg"

        except Exception as e:
            logger.warning(f"Failed to extract base64 image: {e}")
            return None, None

    def _parse_gemini_response(self, response_text: str) -> Dict[str, Any]:
        """Parse Gemini's JSON response"""
        try:
            # Remove markdown code blocks if present
            cleaned = response_text.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            if cleaned.startswith("```"):
                cleaned = cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]

            cleaned = cleaned.strip()

            # Try to parse JSON
            try:
                return json.loads(cleaned)
            except json.JSONDecodeError:
                # Try to find and extract JSON object from the response
                # Sometimes models add extra text before/after
                start_idx = cleaned.find('{')
                end_idx = cleaned.rfind('}')
                if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                    json_str = cleaned[start_idx:end_idx + 1]
                    return json.loads(json_str)
                raise

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Gemini response as JSON: {e}")
            logger.debug(f"Raw response: {response_text}")
            raise ValueError(f"Gemini returned invalid JSON: {str(e)}")

    def _calculate_confidence(
        self,
        settings: Dict[str, Any],
        constraints: Dict[str, Any],
        capabilities: Dict[str, Any],
    ) -> float:
        """Calculate confidence score based on settings quality"""

        confidence = 0.8  # Base confidence for AI response

        # Check if bandwidth constraint is met
        bandwidth_limit = constraints.get("bandwidthLimitMbps")
        recommended_bitrate = settings.get("stream", {}).get("bitrateMbps", 0)

        if bandwidth_limit and recommended_bitrate:
            if recommended_bitrate <= bandwidth_limit:
                confidence += 0.1  # Bonus for meeting constraint
            else:
                confidence -= 0.2  # Penalty for exceeding

        # Check if settings are within capabilities
        max_fps = capabilities.get("maxFps", 30)
        recommended_fps = settings.get("stream", {}).get("fps", 0)

        if recommended_fps and recommended_fps <= max_fps:
            confidence += 0.05
        else:
            confidence -= 0.15

        # Check for warnings
        warnings = settings.get("warnings", [])
        if len(warnings) > 0:
            confidence -= 0.05 * len(warnings)

        # Clamp between 0 and 1
        return max(0.0, min(1.0, confidence))


# Global client instance
_gemini_client: Optional[GeminiVisionClient] = None


def get_gemini_client() -> GeminiVisionClient:
    """Get or create Gemini client singleton"""
    global _gemini_client
    if _gemini_client is None:
        _gemini_client = GeminiVisionClient()
    return _gemini_client
