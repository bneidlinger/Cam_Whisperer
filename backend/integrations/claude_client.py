# backend/integrations/claude_client.py
"""
Claude Vision API Client for camera optimization
Uses Anthropic's Claude Sonnet 4.5 with vision capabilities
"""

import anthropic
import json
import base64
from typing import Dict, Any, Optional, Tuple
import logging

from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class ClaudeVisionClient:
    """Client for interacting with Claude Vision API"""

    def __init__(self):
        """Initialize Claude client with API key from settings"""
        self.client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        self.model = settings.claude_model
        self.max_tokens = settings.claude_max_tokens
        self.temperature = settings.claude_temperature

    def optimize_camera_settings(
        self,
        camera_context: Dict[str, Any],
        current_settings: Dict[str, Any],
        capabilities: Dict[str, Any],
        constraints: Dict[str, Any],
        sample_frame: Optional[str] = None,
        datasheet_specs: Optional[Dict[str, Any]] = None,
    ) -> Tuple[Dict[str, Any], float, str]:
        """
        Generate optimal camera settings using Claude Vision

        Args:
            camera_context: Camera info (id, location, scene_type, purpose)
            current_settings: Current camera configuration
            capabilities: Hardware capabilities
            constraints: Bandwidth/retention constraints
            sample_frame: Base64-encoded image (optional)
            datasheet_specs: Camera datasheet specifications (optional)

        Returns:
            Tuple of (recommended_settings, confidence, explanation)
        """
        try:
            # Build the prompt
            prompt = self._build_optimization_prompt(
                camera_context, current_settings, capabilities, constraints, datasheet_specs
            )

            # Build message content
            message_content = []

            # Add image if provided
            if sample_frame:
                image_data = self._extract_base64_image(sample_frame)
                if image_data:
                    message_content.append(
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/jpeg",
                                "data": image_data,
                            },
                        }
                    )

            # Add text prompt
            message_content.append({"type": "text", "text": prompt})

            logger.info(
                f"Calling Claude Vision API for camera {camera_context.get('id')}"
            )

            # Call Claude API
            response = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                messages=[{"role": "user", "content": message_content}],
            )

            # Extract response text
            response_text = response.content[0].text

            logger.debug(f"Claude response: {response_text[:500]}...")

            # Parse the JSON response
            settings_data = self._parse_claude_response(response_text)

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

            # Calculate confidence based on completeness and constraints
            confidence = self._calculate_confidence(
                settings_data, constraints, capabilities
            )

            logger.info(
                f"Claude optimization complete. Confidence: {confidence:.2f}"
            )

            return recommended_settings, confidence, explanation

        except Exception as e:
            logger.error(f"Claude Vision API error: {str(e)}", exc_info=True)
            raise

    def _build_optimization_prompt(
        self,
        camera_context: Dict[str, Any],
        current_settings: Dict[str, Any],
        capabilities: Dict[str, Any],
        constraints: Dict[str, Any],
        datasheet_specs: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Build the optimization prompt for Claude"""

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
{datasheet_section}
CURRENT SETTINGS:
{json.dumps(current_settings, indent=2)}

HARDWARE CAPABILITIES:
{json.dumps(capabilities, indent=2)}

CONSTRAINTS:
- Bandwidth Limit: {bandwidth_limit} Mbps
- Retention Target: {retention_days} days

TASK:
Analyze the camera context and generate optimal settings that:
1. Maximize evidence quality for the stated purpose ({purpose})
2. Stay within bandwidth and storage constraints
3. Handle the scene type appropriately ({scene_type})
4. Prevent common deployment mistakes (motion blur, excessive noise, poor WDR config)

SCENE TYPE GUIDELINES:
- "entrance": Enable WDR for glass/bright backgrounds, faster shutter for faces
- "parking": License plate optimization - very fast shutter (1/500+), high FPS
- "hallway": Balance motion clarity with low-light performance
- "perimeter": Prioritize detection over identification, wider FOV
- "cashwrap": High detail for transactions, good color reproduction

PURPOSE GUIDELINES:
- "facial": Shutter 1/250 minimum, 20+ FPS, optimize for skin tones
- "plates": Shutter 1/500+ minimum, H.265 for bandwidth, high contrast
- "overview": Broader coverage, lower FPS acceptable (10-15)
- "evidence": Prioritize quality over bandwidth, high bitrate

Return your recommendations in this EXACT JSON structure (no additional text):

{{
  "stream": {{
    "resolution": "1920x1080",
    "codec": "H.265",
    "fps": 20,
    "bitrateMbps": 3.5,
    "keyframeInterval": 40,
    "cbr": true
  }},
  "exposure": {{
    "shutter": "1/250",
    "iris": "Auto",
    "gainLimit": "36dB",
    "wdr": "High",
    "backlightComp": "Off"
  }},
  "lowLight": {{
    "irMode": "Auto",
    "irIntensity": "Medium",
    "noiseReduction": "Low",
    "slowShutter": "Off"
  }},
  "image": {{
    "sharpening": "High",
    "contrast": "55",
    "saturation": "50"
  }},
  "warnings": [
    "List any constraint violations or concerns here"
  ],
  "explanation": "Provide a detailed 2-3 paragraph technical explanation of your key recommendations and the trade-offs made. Explain WHY you chose these settings, not just WHAT they are. Reference the scene analysis if an image was provided."
}}

CRITICAL: Return ONLY valid JSON. No markdown code blocks, no extra text, just the JSON object.
"""

        return prompt

    def _extract_base64_image(self, data_url: str) -> Optional[str]:
        """Extract base64 image data from data URL"""
        try:
            if "base64," in data_url:
                return data_url.split("base64,")[1]
            return data_url
        except Exception as e:
            logger.warning(f"Failed to extract base64 image: {e}")
            return None

    def _parse_claude_response(self, response_text: str) -> Dict[str, Any]:
        """Parse Claude's JSON response"""
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

            # Parse JSON
            return json.loads(cleaned)

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Claude response as JSON: {e}")
            logger.debug(f"Raw response: {response_text}")
            raise ValueError(f"Claude returned invalid JSON: {str(e)}")

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
_claude_client: Optional[ClaudeVisionClient] = None


def get_claude_client() -> ClaudeVisionClient:
    """Get or create Claude client singleton"""
    global _claude_client
    if _claude_client is None:
        _claude_client = ClaudeVisionClient()
    return _claude_client
