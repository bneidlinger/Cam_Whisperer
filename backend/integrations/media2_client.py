"""
ONVIF Media2 Service Client (Profile T)

This module provides Profile T (Media2) service integration for:
- H.265/HEVC encoder configuration
- RTSPS (secure RTSP over TLS) streaming
- Advanced imaging controls
- Bidirectional audio support

Profile T is the mandatory successor to Profile S (deprecated Oct 2025).
Media2 service uses media2.wsdl (Ver 2.0) instead of media.wsdl (Ver 1.0).

Key differences from Profile S:
- Separates Video Source configuration from Video Encoder configuration
- Native H.265 support with full parameter control
- HTTPS/RTSPS transport security
- Standardized imaging service integration
"""

import logging
from typing import List, Dict, Optional, Any
import asyncio
from concurrent.futures import ThreadPoolExecutor

from onvif import ONVIFCamera

logger = logging.getLogger(__name__)


class Media2Client:
    """
    ONVIF Media2 Service Client for Profile T cameras.

    Use this client for cameras that support Profile T (Media2 service).
    Falls back gracefully to Profile S methods when Media2 is unavailable.
    """

    def __init__(self, timeout: int = 10):
        """
        Initialize Media2 client.

        Args:
            timeout: Operation timeout in seconds
        """
        self.timeout = timeout
        self.executor = ThreadPoolExecutor(max_workers=5)

    async def _run_in_executor(self, func, *args):
        """Run blocking ONVIF operation in thread pool"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self.executor, func, *args)

    # =========================================================================
    # SERVICE DETECTION
    # =========================================================================

    async def has_media2_service(self, camera: ONVIFCamera) -> bool:
        """
        Check if camera supports Media2 service (Profile T).

        Args:
            camera: Connected ONVIFCamera instance

        Returns:
            True if Media2 service is available
        """
        try:
            device_mgmt = camera.create_devicemgmt_service()
            services = await self._run_in_executor(
                device_mgmt.GetServices,
                {"IncludeCapability": False}
            )

            for service in services:
                namespace = getattr(service, 'Namespace', '')
                if 'media2' in namespace.lower() or 'media/ver20' in namespace.lower():
                    logger.info("Media2 service (Profile T) detected")
                    return True

            logger.debug("Media2 service not found - camera uses Profile S only")
            return False

        except Exception as e:
            logger.warning(f"Could not check for Media2 service: {e}")
            return False

    async def get_media2_service(self, camera: ONVIFCamera):
        """
        Get Media2 service from camera.

        Args:
            camera: Connected ONVIFCamera instance

        Returns:
            Media2 service object or None if not available
        """
        try:
            # Try to create Media2 service
            media2 = await self._run_in_executor(
                camera.create_media2_service
            )
            return media2
        except Exception as e:
            logger.warning(f"Could not create Media2 service: {e}")
            return None

    # =========================================================================
    # PROFILE T MEDIA PROFILES
    # =========================================================================

    async def get_profiles(self, camera: ONVIFCamera) -> List[Dict]:
        """
        Get media profiles using Media2 service.

        Profile T separates configurations more cleanly than Profile S.

        Args:
            camera: Connected ONVIFCamera instance

        Returns:
            List of profile dictionaries with detailed configuration
        """
        media2 = await self.get_media2_service(camera)
        if not media2:
            logger.warning("Media2 service not available, falling back to Media service")
            return await self._get_profiles_legacy(camera)

        try:
            profiles = await self._run_in_executor(
                media2.GetProfiles,
                {"Type": "All"}  # Get all profile types
            )

            result = []
            for profile in profiles:
                profile_data = {
                    "token": profile.token,
                    "name": profile.Name if hasattr(profile, 'Name') else None,
                    "fixed": profile.fixed if hasattr(profile, 'fixed') else False,
                    # Media2 specific - configurations are referenced by token
                    "configurations": {
                        "video_source": None,
                        "video_encoder": None,
                        "audio_source": None,
                        "audio_encoder": None,
                        "ptz": None,
                        "analytics": None,
                        "metadata": None,
                    }
                }

                # Extract configuration tokens
                if hasattr(profile, 'Configurations'):
                    configs = profile.Configurations
                    if hasattr(configs, 'VideoSource'):
                        profile_data["configurations"]["video_source"] = configs.VideoSource.token
                    if hasattr(configs, 'VideoEncoder'):
                        profile_data["configurations"]["video_encoder"] = configs.VideoEncoder.token
                    if hasattr(configs, 'AudioSource'):
                        profile_data["configurations"]["audio_source"] = configs.AudioSource.token
                    if hasattr(configs, 'AudioEncoder'):
                        profile_data["configurations"]["audio_encoder"] = configs.AudioEncoder.token
                    if hasattr(configs, 'PTZ'):
                        profile_data["configurations"]["ptz"] = configs.PTZ.token

                result.append(profile_data)

            logger.info(f"Found {len(result)} Media2 profiles")
            return result

        except Exception as e:
            logger.error(f"Failed to get Media2 profiles: {e}")
            raise

    async def _get_profiles_legacy(self, camera: ONVIFCamera) -> List[Dict]:
        """Fallback to Profile S media profiles"""
        try:
            media = camera.create_media_service()
            profiles = await self._run_in_executor(media.GetProfiles)

            result = []
            for profile in profiles:
                result.append({
                    "token": profile.token,
                    "name": profile.Name,
                    "fixed": getattr(profile, 'fixed', False),
                    "legacy": True,  # Mark as Profile S
                })
            return result
        except Exception as e:
            logger.error(f"Failed to get legacy profiles: {e}")
            return []

    # =========================================================================
    # H.265 ENCODER CONFIGURATION (Profile T only)
    # =========================================================================

    async def get_video_encoder_configurations(self, camera: ONVIFCamera) -> List[Dict]:
        """
        Get video encoder configurations using Media2 service.

        Media2 provides detailed H.265 configuration options not available in Profile S.

        Args:
            camera: Connected ONVIFCamera instance

        Returns:
            List of encoder configuration dictionaries
        """
        media2 = await self.get_media2_service(camera)
        if not media2:
            return await self._get_encoder_configs_legacy(camera)

        try:
            configs = await self._run_in_executor(
                media2.GetVideoEncoderConfigurations
            )

            result = []
            for config in configs:
                encoder_data = {
                    "token": config.token,
                    "name": config.Name,
                    "encoding": config.Encoding,  # H264, H265, JPEG
                    "profile_t": True,
                    "resolution": {
                        "width": config.Resolution.Width,
                        "height": config.Resolution.Height
                    } if hasattr(config, 'Resolution') else None,
                    "quality": config.Quality if hasattr(config, 'Quality') else None,
                    "rate_control": None,
                    "h264": None,
                    "h265": None,
                    "multicast": None,
                }

                # Rate control settings
                if hasattr(config, 'RateControl') and config.RateControl:
                    rc = config.RateControl
                    encoder_data["rate_control"] = {
                        "frame_rate_limit": rc.FrameRateLimit if hasattr(rc, 'FrameRateLimit') else None,
                        "bitrate_limit": rc.BitrateLimit if hasattr(rc, 'BitrateLimit') else None,
                        "constant_bitrate": rc.ConstantBitRate if hasattr(rc, 'ConstantBitRate') else None,
                    }

                # H.264 specific settings
                if hasattr(config, 'H264') and config.H264:
                    h264 = config.H264
                    encoder_data["h264"] = {
                        "gov_length": h264.GovLength if hasattr(h264, 'GovLength') else None,
                        "profile": h264.H264Profile if hasattr(h264, 'H264Profile') else None,
                    }

                # H.265 specific settings (Profile T only!)
                if hasattr(config, 'H265') and config.H265:
                    h265 = config.H265
                    encoder_data["h265"] = {
                        "gov_length": h265.GovLength if hasattr(h265, 'GovLength') else None,
                        "profile": h265.H265Profile if hasattr(h265, 'H265Profile') else None,
                    }

                result.append(encoder_data)

            logger.info(f"Found {len(result)} Media2 encoder configurations")
            return result

        except Exception as e:
            logger.error(f"Failed to get Media2 encoder configs: {e}")
            raise

    async def _get_encoder_configs_legacy(self, camera: ONVIFCamera) -> List[Dict]:
        """Fallback to Profile S encoder configurations"""
        try:
            media = camera.create_media_service()
            configs = await self._run_in_executor(media.GetVideoEncoderConfigurations)

            result = []
            for config in configs:
                result.append({
                    "token": config.token,
                    "name": config.Name,
                    "encoding": config.Encoding,
                    "profile_t": False,  # Mark as Profile S
                    "resolution": {
                        "width": config.Resolution.Width,
                        "height": config.Resolution.Height
                    },
                    "quality": config.Quality,
                    "rate_control": {
                        "frame_rate_limit": config.RateControl.FrameRateLimit,
                        "bitrate_limit": config.RateControl.BitrateLimit,
                    } if hasattr(config, 'RateControl') else None,
                })
            return result
        except Exception as e:
            logger.error(f"Failed to get legacy encoder configs: {e}")
            return []

    async def get_video_encoder_config_options(
        self,
        camera: ONVIFCamera,
        config_token: str
    ) -> Dict:
        """
        Get available options for a video encoder configuration.

        This tells us what resolutions, codecs, and parameters the camera supports.
        Critical for knowing if H.265 is actually available.

        Args:
            camera: Connected ONVIFCamera instance
            config_token: Encoder configuration token

        Returns:
            Dictionary with available options
        """
        media2 = await self.get_media2_service(camera)
        if not media2:
            return await self._get_encoder_options_legacy(camera, config_token)

        try:
            options = await self._run_in_executor(
                media2.GetVideoEncoderConfigurationOptions,
                {"ConfigurationToken": config_token}
            )

            result = {
                "encoding_options": [],
                "quality_range": None,
                "h264_options": None,
                "h265_options": None,
                "resolution_options": [],
            }

            # Available encodings (H264, H265, JPEG)
            if hasattr(options, 'Encoding'):
                result["encoding_options"] = list(options.Encoding) if options.Encoding else []

            # Quality range
            if hasattr(options, 'QualityRange') and options.QualityRange:
                result["quality_range"] = {
                    "min": options.QualityRange.Min,
                    "max": options.QualityRange.Max,
                }

            # H.264 options
            if hasattr(options, 'H264') and options.H264:
                h264 = options.H264
                result["h264_options"] = {
                    "profiles": list(h264.H264ProfilesSupported) if hasattr(h264, 'H264ProfilesSupported') else [],
                    "gov_length_range": {
                        "min": h264.GovLengthRange.Min,
                        "max": h264.GovLengthRange.Max,
                    } if hasattr(h264, 'GovLengthRange') else None,
                    "resolutions": self._parse_resolutions(h264.ResolutionsAvailable) if hasattr(h264, 'ResolutionsAvailable') else [],
                    "frame_rate_range": {
                        "min": h264.FrameRateRange.Min,
                        "max": h264.FrameRateRange.Max,
                    } if hasattr(h264, 'FrameRateRange') else None,
                }

            # H.265 options (Profile T only!)
            if hasattr(options, 'H265') and options.H265:
                h265 = options.H265
                result["h265_options"] = {
                    "profiles": list(h265.H265ProfilesSupported) if hasattr(h265, 'H265ProfilesSupported') else [],
                    "gov_length_range": {
                        "min": h265.GovLengthRange.Min,
                        "max": h265.GovLengthRange.Max,
                    } if hasattr(h265, 'GovLengthRange') else None,
                    "resolutions": self._parse_resolutions(h265.ResolutionsAvailable) if hasattr(h265, 'ResolutionsAvailable') else [],
                    "frame_rate_range": {
                        "min": h265.FrameRateRange.Min,
                        "max": h265.FrameRateRange.Max,
                    } if hasattr(h265, 'FrameRateRange') else None,
                }
                logger.info("H.265 encoder options available")

            return result

        except Exception as e:
            logger.error(f"Failed to get encoder options: {e}")
            raise

    async def _get_encoder_options_legacy(self, camera: ONVIFCamera, config_token: str) -> Dict:
        """Fallback to Profile S encoder options"""
        try:
            media = camera.create_media_service()
            options = await self._run_in_executor(
                media.GetVideoEncoderConfigurationOptions,
                {"ConfigurationToken": config_token}
            )

            return {
                "encoding_options": ["H264", "JPEG"],  # Profile S doesn't have H265
                "quality_range": {
                    "min": options.QualityRange.Min,
                    "max": options.QualityRange.Max,
                } if hasattr(options, 'QualityRange') else None,
                "h264_options": None,  # Simplified for legacy
                "h265_options": None,  # Not available in Profile S
                "profile_s_only": True,
            }
        except Exception as e:
            logger.error(f"Failed to get legacy encoder options: {e}")
            return {}

    def _parse_resolutions(self, resolutions) -> List[str]:
        """Parse resolution objects into string list"""
        if not resolutions:
            return []
        return [f"{r.Width}x{r.Height}" for r in resolutions]

    async def set_video_encoder_configuration(
        self,
        camera: ONVIFCamera,
        config_token: str,
        settings: Dict
    ) -> bool:
        """
        Set video encoder configuration using Media2 service.

        Supports H.265 configuration (Profile T only).

        Args:
            camera: Connected ONVIFCamera instance
            config_token: Encoder configuration token
            settings: Settings to apply:
                - encoding: "H264" or "H265"
                - resolution: "1920x1080"
                - fps: 30
                - bitrate_kbps: 4000
                - gov_length: 30 (GOP size)
                - profile: "Main" or "High" (for H.264/H.265)
                - constant_bitrate: True/False (CBR/VBR)

        Returns:
            True if successful
        """
        media2 = await self.get_media2_service(camera)
        if not media2:
            return await self._set_encoder_config_legacy(camera, config_token, settings)

        try:
            # Get current configuration
            current = await self._run_in_executor(
                media2.GetVideoEncoderConfiguration,
                {"ConfigurationToken": config_token}
            )

            # Apply new settings
            if "encoding" in settings:
                current.Encoding = settings["encoding"]

            if "resolution" in settings:
                res = settings["resolution"]
                if isinstance(res, str) and "x" in res:
                    width, height = map(int, res.split("x"))
                    current.Resolution.Width = width
                    current.Resolution.Height = height

            if "quality" in settings:
                current.Quality = settings["quality"]

            # Rate control settings
            if hasattr(current, 'RateControl') and current.RateControl:
                if "fps" in settings:
                    current.RateControl.FrameRateLimit = settings["fps"]
                if "bitrate_kbps" in settings:
                    current.RateControl.BitrateLimit = settings["bitrate_kbps"]
                if "constant_bitrate" in settings:
                    current.RateControl.ConstantBitRate = settings["constant_bitrate"]

            # H.264 specific settings
            if settings.get("encoding") == "H264" and hasattr(current, 'H264'):
                if current.H264 is None:
                    # Need to create H264 settings object - this is camera specific
                    logger.warning("H264 settings object not present, skipping H264-specific config")
                else:
                    if "gov_length" in settings:
                        current.H264.GovLength = settings["gov_length"]
                    if "profile" in settings:
                        current.H264.H264Profile = settings["profile"]

            # H.265 specific settings (Profile T only!)
            if settings.get("encoding") == "H265":
                if not hasattr(current, 'H265') or current.H265 is None:
                    logger.warning("H265 settings object not present - camera may not support H.265")
                else:
                    if "gov_length" in settings:
                        current.H265.GovLength = settings["gov_length"]
                    if "profile" in settings:
                        current.H265.H265Profile = settings["profile"]
                    logger.info(f"Configuring H.265 encoder: GOP={settings.get('gov_length')}, Profile={settings.get('profile')}")

            # Apply configuration
            await self._run_in_executor(
                media2.SetVideoEncoderConfiguration,
                {"Configuration": current}
            )

            logger.info(f"Successfully applied Media2 encoder configuration: {settings.get('encoding', 'unchanged')}")
            return True

        except Exception as e:
            logger.error(f"Failed to set Media2 encoder config: {e}")
            raise

    async def _set_encoder_config_legacy(
        self,
        camera: ONVIFCamera,
        config_token: str,
        settings: Dict
    ) -> bool:
        """Fallback to Profile S encoder configuration"""
        if settings.get("encoding") == "H265":
            logger.error("H.265 encoding requested but camera only supports Profile S (no H.265)")
            raise ValueError("H.265 requires Profile T support - this camera only supports Profile S")

        try:
            media = camera.create_media_service()

            current = await self._run_in_executor(
                media.GetVideoEncoderConfiguration,
                {"ConfigurationToken": config_token}
            )

            # Apply settings (limited to Profile S capabilities)
            if "resolution" in settings:
                res = settings["resolution"]
                if isinstance(res, str) and "x" in res:
                    width, height = map(int, res.split("x"))
                    current.Resolution.Width = width
                    current.Resolution.Height = height

            if "fps" in settings:
                current.RateControl.FrameRateLimit = settings["fps"]
            if "bitrate_kbps" in settings:
                current.RateControl.BitrateLimit = settings["bitrate_kbps"]

            await self._run_in_executor(
                media.SetVideoEncoderConfiguration,
                {"Configuration": current, "ForcePersistence": True}
            )

            logger.info("Applied legacy (Profile S) encoder configuration")
            return True

        except Exception as e:
            logger.error(f"Failed to set legacy encoder config: {e}")
            raise

    # =========================================================================
    # STREAMING URIS (with RTSPS support)
    # =========================================================================

    async def get_stream_uri(
        self,
        camera: ONVIFCamera,
        profile_token: str,
        protocol: str = "RtspUnicast",
        secure: bool = False
    ) -> Dict:
        """
        Get streaming URI using Media2 service.

        Supports RTSPS (secure RTSP over TLS) when secure=True.

        Args:
            camera: Connected ONVIFCamera instance
            profile_token: Media profile token
            protocol: Stream protocol - "RtspUnicast", "RtspMulticast", "HTTP"
            secure: Use HTTPS/RTSPS transport (Profile T feature)

        Returns:
            Dictionary with URI and transport info
        """
        media2 = await self.get_media2_service(camera)
        if not media2:
            return await self._get_stream_uri_legacy(camera, profile_token, secure)

        try:
            # Media2 uses different transport specification
            stream_setup = {
                "Protocol": protocol,
            }

            uri_response = await self._run_in_executor(
                media2.GetStreamUri,
                {
                    "ProfileToken": profile_token,
                    "Protocol": "https" if secure else "rtsp"
                }
            )

            uri = uri_response.Uri if hasattr(uri_response, 'Uri') else str(uri_response)

            result = {
                "uri": uri,
                "protocol": protocol,
                "secure": secure,
                "profile_t": True,
            }

            # Check if URI is actually RTSPS
            if secure and not uri.startswith("rtsps://"):
                logger.warning(f"Requested secure stream but got non-RTSPS URI: {uri}")
                result["secure"] = False

            logger.info(f"Got stream URI: {uri[:50]}...")
            return result

        except Exception as e:
            logger.error(f"Failed to get Media2 stream URI: {e}")
            # Fallback to legacy
            return await self._get_stream_uri_legacy(camera, profile_token, secure)

    async def _get_stream_uri_legacy(
        self,
        camera: ONVIFCamera,
        profile_token: str,
        secure: bool = False
    ) -> Dict:
        """Fallback to Profile S stream URI"""
        if secure:
            logger.warning("RTSPS requested but camera only supports Profile S - using RTSP")

        try:
            media = camera.create_media_service()

            stream_setup = {
                "Stream": "RTP-Unicast",
                "Transport": {"Protocol": "RTSP"}
            }

            uri_response = await self._run_in_executor(
                media.GetStreamUri,
                {"StreamSetup": stream_setup, "ProfileToken": profile_token}
            )

            return {
                "uri": uri_response.Uri,
                "protocol": "RTSP",
                "secure": False,
                "profile_t": False,
            }

        except Exception as e:
            logger.error(f"Failed to get legacy stream URI: {e}")
            raise

    async def get_snapshot_uri(self, camera: ONVIFCamera, profile_token: str) -> str:
        """
        Get snapshot URI using Media2 service.

        Args:
            camera: Connected ONVIFCamera instance
            profile_token: Media profile token

        Returns:
            Snapshot URI
        """
        media2 = await self.get_media2_service(camera)
        if not media2:
            return await self._get_snapshot_uri_legacy(camera, profile_token)

        try:
            uri_response = await self._run_in_executor(
                media2.GetSnapshotUri,
                {"ProfileToken": profile_token}
            )

            uri = uri_response.Uri if hasattr(uri_response, 'Uri') else str(uri_response)
            logger.info(f"Got Media2 snapshot URI: {uri[:50]}...")
            return uri

        except Exception as e:
            logger.warning(f"Media2 GetSnapshotUri failed, trying legacy: {e}")
            return await self._get_snapshot_uri_legacy(camera, profile_token)

    async def _get_snapshot_uri_legacy(self, camera: ONVIFCamera, profile_token: str) -> str:
        """Fallback to Profile S snapshot URI"""
        try:
            media = camera.create_media_service()
            uri_response = await self._run_in_executor(
                media.GetSnapshotUri,
                {"ProfileToken": profile_token}
            )
            return uri_response.Uri
        except Exception as e:
            logger.error(f"Failed to get legacy snapshot URI: {e}")
            raise


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

async def check_h265_support(camera: ONVIFCamera) -> Dict:
    """
    Check if camera supports H.265 encoding.

    Args:
        camera: Connected ONVIFCamera instance

    Returns:
        Dictionary with H.265 support info
    """
    client = Media2Client()

    result = {
        "h265_supported": False,
        "profile_t": False,
        "h265_profiles": [],
        "max_h265_resolution": None,
    }

    # Check for Media2 service
    has_media2 = await client.has_media2_service(camera)
    result["profile_t"] = has_media2

    if not has_media2:
        logger.info("Camera does not support Profile T - H.265 not available")
        return result

    # Get encoder configurations
    try:
        configs = await client.get_video_encoder_configurations(camera)

        for config in configs:
            # Check if any config supports H.265
            if config.get("h265"):
                result["h265_supported"] = True

            # Get options for detailed H.265 support
            options = await client.get_video_encoder_config_options(camera, config["token"])

            if options.get("h265_options"):
                result["h265_supported"] = True
                h265_opts = options["h265_options"]
                result["h265_profiles"] = h265_opts.get("profiles", [])

                resolutions = h265_opts.get("resolutions", [])
                if resolutions:
                    result["max_h265_resolution"] = resolutions[0]  # Usually sorted highest first

    except Exception as e:
        logger.warning(f"Error checking H.265 support: {e}")

    return result


async def configure_h265_stream(
    camera: ONVIFCamera,
    config_token: str,
    resolution: str = "1920x1080",
    fps: int = 30,
    bitrate_kbps: int = 4000,
    gov_length: int = 30,
    profile: str = "Main"
) -> bool:
    """
    Configure camera for H.265 streaming.

    Convenience function that sets up optimal H.265 settings.

    Args:
        camera: Connected ONVIFCamera instance
        config_token: Encoder configuration token
        resolution: Target resolution (e.g., "1920x1080", "2560x1440", "3840x2160")
        fps: Frame rate
        bitrate_kbps: Target bitrate in Kbps
        gov_length: GOP length (keyframe interval)
        profile: H.265 profile ("Main", "Main10")

    Returns:
        True if successful
    """
    client = Media2Client()

    # Check H.265 support first
    h265_info = await check_h265_support(camera)
    if not h265_info["h265_supported"]:
        raise ValueError("Camera does not support H.265 encoding")

    # Apply H.265 configuration
    settings = {
        "encoding": "H265",
        "resolution": resolution,
        "fps": fps,
        "bitrate_kbps": bitrate_kbps,
        "gov_length": gov_length,
        "profile": profile,
        "constant_bitrate": False,  # VBR is generally better for H.265
    }

    return await client.set_video_encoder_configuration(camera, config_token, settings)
