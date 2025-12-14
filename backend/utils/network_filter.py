# backend/utils/network_filter.py
"""
Network filtering utilities for camera discovery.

Provides MAC address, OUI (vendor), and subnet filtering to restrict
discovery results to known/trusted devices.

Security benefits:
- Prevents accidental discovery of non-camera devices
- Limits exposure to rogue devices on the network
- Enables vendor-specific deployments (e.g., "only Hanwha cameras")
- Supports network segmentation compliance
"""

import logging
import ipaddress
from typing import List, Dict, Optional, Set
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


# Well-known camera manufacturer OUIs (first 3 bytes of MAC address)
# Format: "XX:XX:XX" (uppercase, colon-separated)
CAMERA_MANUFACTURER_OUIS = {
    # Hanwha Techwin (Samsung)
    "00:09:18": "Hanwha Techwin",
    "00:16:6C": "Hanwha Techwin",
    "00:1E:E3": "Hanwha Techwin",
    "00:26:2D": "Hanwha Techwin",
    "F4:D9:FB": "Hanwha Techwin",
    "FC:D7:33": "Hanwha Techwin",

    # Axis Communications
    "00:40:8C": "Axis Communications",
    "AC:CC:8E": "Axis Communications",
    "B8:A4:4F": "Axis Communications",

    # Hikvision
    "28:57:BE": "Hikvision",
    "44:19:B6": "Hikvision",
    "54:C4:15": "Hikvision",
    "BC:AD:28": "Hikvision",
    "C0:56:E3": "Hikvision",
    "E0:50:8B": "Hikvision",

    # Dahua
    "3C:EF:8C": "Dahua",
    "4C:11:BF": "Dahua",
    "90:02:A9": "Dahua",
    "A0:BD:1D": "Dahua",
    "E0:50:8B": "Dahua",

    # Uniview
    "24:28:FD": "Uniview",

    # Bosch Security
    "00:04:13": "Bosch Security",
    "00:07:5F": "Bosch Security",

    # Vivotek
    "00:02:D1": "Vivotek",
    "00:90:FB": "Vivotek",

    # Panasonic
    "00:04:3B": "Panasonic",
    "00:13:C3": "Panasonic",
    "00:80:45": "Panasonic",

    # Sony
    "00:1A:80": "Sony",
    "00:1D:BA": "Sony",

    # Pelco
    "00:13:B6": "Pelco",
    "00:14:F8": "Pelco",

    # Arecont Vision
    "00:02:F7": "Arecont Vision",

    # Avigilon
    "00:18:85": "Avigilon",
    "1C:FA:68": "Avigilon",

    # FLIR
    "00:40:7F": "FLIR",
}


@dataclass
class NetworkFilterConfig:
    """
    Configuration for network filtering.

    Attributes:
        enabled: Whether filtering is enabled
        mode: 'whitelist' (only allow listed) or 'blacklist' (block listed)
        allowed_ouis: Set of allowed OUI prefixes (e.g., {"00:09:18", "00:40:8C"})
        allowed_macs: Set of specific allowed MAC addresses
        blocked_macs: Set of specific blocked MAC addresses
        allowed_subnets: Set of allowed IP subnets (CIDR notation)
        allow_unknown_oui: Whether to allow devices with unknown/no OUI
        vendor_filter: Set of allowed vendor names (case-insensitive)
    """
    enabled: bool = False
    mode: str = "whitelist"
    allowed_ouis: Set[str] = field(default_factory=set)
    allowed_macs: Set[str] = field(default_factory=set)
    blocked_macs: Set[str] = field(default_factory=set)
    allowed_subnets: Set[str] = field(default_factory=set)
    allow_unknown_oui: bool = True
    vendor_filter: Set[str] = field(default_factory=set)


class NetworkFilter:
    """
    Filter discovered devices by MAC address, OUI, and network criteria.

    Provides defense-in-depth for camera discovery:
    1. MAC whitelist/blacklist - specific device control
    2. OUI filtering - vendor-level control
    3. Subnet filtering - network segmentation
    4. Vendor name filtering - manufacturer-level control
    """

    def __init__(self, config: Optional[NetworkFilterConfig] = None):
        """
        Initialize network filter.

        Args:
            config: Filter configuration (uses permissive defaults if None)
        """
        self.config = config or NetworkFilterConfig()
        self._oui_lookup = CAMERA_MANUFACTURER_OUIS.copy()

    @staticmethod
    def normalize_mac(mac: str) -> str:
        """
        Normalize MAC address to uppercase colon-separated format.

        Args:
            mac: MAC address in any common format

        Returns:
            Normalized MAC (e.g., "00:09:18:AB:CD:EF")
        """
        if not mac:
            return ""

        # Remove common separators and convert to uppercase
        clean = mac.upper().replace("-", "").replace(":", "").replace(".", "")

        # Validate length
        if len(clean) != 12:
            return ""

        # Validate hex characters
        try:
            int(clean, 16)
        except ValueError:
            return ""

        # Format as colon-separated
        return ":".join(clean[i:i+2] for i in range(0, 12, 2))

    @staticmethod
    def extract_oui(mac: str) -> str:
        """
        Extract OUI (first 3 bytes) from MAC address.

        Args:
            mac: MAC address (any format)

        Returns:
            OUI prefix (e.g., "00:09:18")
        """
        normalized = NetworkFilter.normalize_mac(mac)
        if len(normalized) >= 8:
            return normalized[:8]
        return ""

    def get_vendor_from_mac(self, mac: str) -> Optional[str]:
        """
        Look up vendor name from MAC address OUI.

        Args:
            mac: MAC address

        Returns:
            Vendor name or None if unknown
        """
        oui = self.extract_oui(mac)
        return self._oui_lookup.get(oui)

    def is_mac_allowed(self, mac: str) -> bool:
        """
        Check if a MAC address is allowed by current filter rules.

        Args:
            mac: MAC address to check

        Returns:
            True if allowed, False if blocked
        """
        if not self.config.enabled:
            return True

        normalized = self.normalize_mac(mac)

        # Check explicit blacklist first (always blocks)
        if normalized and normalized in self.config.blocked_macs:
            logger.debug(f"MAC {normalized} is explicitly blocked")
            return False

        # Check explicit whitelist (always allows)
        if normalized and normalized in self.config.allowed_macs:
            logger.debug(f"MAC {normalized} is explicitly allowed")
            return True

        # If no MAC available and we're strict, block
        if not normalized:
            return self.config.allow_unknown_oui

        # Check OUI filter
        if self.config.allowed_ouis:
            oui = self.extract_oui(normalized)
            if oui not in self.config.allowed_ouis:
                logger.debug(f"MAC {normalized} OUI {oui} not in allowed list")
                return False

        return True

    def is_ip_allowed(self, ip: str) -> bool:
        """
        Check if an IP address is in allowed subnets.

        Args:
            ip: IP address to check

        Returns:
            True if allowed, False if blocked
        """
        if not self.config.enabled:
            return True

        if not self.config.allowed_subnets:
            return True  # No subnet restriction

        if not ip:
            return False

        try:
            ip_obj = ipaddress.ip_address(ip)

            for subnet_str in self.config.allowed_subnets:
                try:
                    subnet = ipaddress.ip_network(subnet_str, strict=False)
                    if ip_obj in subnet:
                        logger.debug(f"IP {ip} is in allowed subnet {subnet_str}")
                        return True
                except ValueError:
                    continue

            logger.debug(f"IP {ip} not in any allowed subnet")
            return False

        except ValueError:
            logger.warning(f"Invalid IP address: {ip}")
            return False

    def is_vendor_allowed(self, vendor: str) -> bool:
        """
        Check if a vendor name is allowed.

        Args:
            vendor: Vendor/manufacturer name

        Returns:
            True if allowed, False if blocked
        """
        if not self.config.enabled:
            return True

        if not self.config.vendor_filter:
            return True  # No vendor restriction

        if not vendor:
            return self.config.allow_unknown_oui

        vendor_lower = vendor.lower()
        allowed_lower = {v.lower() for v in self.config.vendor_filter}

        # Check for partial matches (e.g., "Hanwha" matches "Hanwha Techwin")
        for allowed in allowed_lower:
            if allowed in vendor_lower or vendor_lower in allowed:
                return True

        logger.debug(f"Vendor '{vendor}' not in allowed list")
        return False

    def filter_camera(self, camera: Dict) -> bool:
        """
        Check if a discovered camera should be included.

        Args:
            camera: Camera dict with ip, mac, vendor fields

        Returns:
            True if camera passes all filters
        """
        if not self.config.enabled:
            return True

        ip = camera.get("ip", "")
        mac = camera.get("mac", "")
        vendor = camera.get("vendor") or camera.get("manufacturer", "")

        # Check all filters
        if not self.is_ip_allowed(ip):
            logger.info(f"Filtered out camera at {ip}: IP not in allowed subnets")
            return False

        if mac and not self.is_mac_allowed(mac):
            logger.info(f"Filtered out camera at {ip}: MAC {mac} not allowed")
            return False

        if not self.is_vendor_allowed(vendor):
            logger.info(f"Filtered out camera at {ip}: Vendor '{vendor}' not allowed")
            return False

        return True

    def filter_cameras(self, cameras: List[Dict]) -> List[Dict]:
        """
        Filter a list of discovered cameras.

        Args:
            cameras: List of camera dicts

        Returns:
            Filtered list containing only allowed cameras
        """
        if not self.config.enabled:
            return cameras

        filtered = [cam for cam in cameras if self.filter_camera(cam)]

        removed = len(cameras) - len(filtered)
        if removed > 0:
            logger.info(f"Network filter removed {removed}/{len(cameras)} cameras")

        return filtered

    def enrich_with_vendor(self, cameras: List[Dict]) -> List[Dict]:
        """
        Enrich camera list with vendor info from MAC OUI lookup.

        Args:
            cameras: List of camera dicts

        Returns:
            Same list with vendor_from_mac field added
        """
        for camera in cameras:
            mac = camera.get("mac", "")
            if mac:
                vendor = self.get_vendor_from_mac(mac)
                if vendor:
                    camera["vendor_from_mac"] = vendor
                    # Use MAC vendor if camera vendor is unknown
                    if not camera.get("vendor") or camera.get("vendor") == "Unknown":
                        camera["vendor"] = vendor

        return cameras


# Global filter instance
_network_filter: Optional[NetworkFilter] = None


def get_network_filter() -> NetworkFilter:
    """Get or create the global network filter."""
    global _network_filter
    if _network_filter is None:
        # Default: filtering disabled, but ready to enable
        _network_filter = NetworkFilter(NetworkFilterConfig(
            enabled=False,
            allow_unknown_oui=True,
        ))
    return _network_filter


def configure_network_filter(
    enabled: bool = False,
    allowed_ouis: Optional[List[str]] = None,
    allowed_macs: Optional[List[str]] = None,
    blocked_macs: Optional[List[str]] = None,
    allowed_subnets: Optional[List[str]] = None,
    vendor_filter: Optional[List[str]] = None,
    allow_unknown_oui: bool = True,
) -> NetworkFilter:
    """
    Configure the global network filter.

    Args:
        enabled: Enable filtering
        allowed_ouis: List of allowed OUI prefixes
        allowed_macs: List of explicitly allowed MAC addresses
        blocked_macs: List of blocked MAC addresses
        allowed_subnets: List of allowed subnets (CIDR)
        vendor_filter: List of allowed vendor names
        allow_unknown_oui: Allow devices with unknown OUI

    Returns:
        Configured NetworkFilter instance
    """
    global _network_filter

    config = NetworkFilterConfig(
        enabled=enabled,
        allowed_ouis=set(allowed_ouis or []),
        allowed_macs={NetworkFilter.normalize_mac(m) for m in (allowed_macs or [])},
        blocked_macs={NetworkFilter.normalize_mac(m) for m in (blocked_macs or [])},
        allowed_subnets=set(allowed_subnets or []),
        vendor_filter=set(vendor_filter or []),
        allow_unknown_oui=allow_unknown_oui,
    )

    _network_filter = NetworkFilter(config)
    logger.info(f"Network filter configured: enabled={enabled}, "
                f"OUIs={len(config.allowed_ouis)}, "
                f"subnets={len(config.allowed_subnets)}")

    return _network_filter


# Convenience function to get all known camera OUIs
def get_known_camera_ouis() -> Dict[str, str]:
    """
    Get dictionary of known camera manufacturer OUIs.

    Returns:
        Dict mapping OUI prefix to vendor name
    """
    return CAMERA_MANUFACTURER_OUIS.copy()
