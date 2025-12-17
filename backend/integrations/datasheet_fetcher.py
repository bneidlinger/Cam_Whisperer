# backend/integrations/datasheet_fetcher.py
"""
Datasheet fetching integration for camera specifications.
Handles web search, hardcoded URLs, PDF download, and parsing.
"""

import asyncio
import logging
import re
import os
from io import BytesIO
from typing import Dict, Any, Optional, Tuple, List
from datetime import datetime
import httpx

logger = logging.getLogger(__name__)

# User agent for web requests
USER_AGENT = "PlatoniCam/0.6.0 (Camera Optimization System)"

# Hardcoded manufacturer datasheet URL patterns
# "patterns" is a list of URL templates to try in order
# "search_hint" is used for DuckDuckGo fallback search
MANUFACTURER_URLS = {
    "axis": {
        "patterns": [
            "https://www.axis.com/dam/public/a1/b2/c3/{model}-datasheet-en-US.pdf",
        ],
        "search_hint": "site:axis.com datasheet",
    },
    "bosch": {
        "patterns": [],
        "search_hint": "site:commerce.boschsecurity.com datasheet",
    },
    "hanwha": {
        "patterns": [
            # Hanwha Vision CDN patterns (most common)
            "https://hanwhavision.eu/wp-content/uploads/products/{model}/DataSheet_{model}_EN.pdf",
            "https://hanwhavision.eu/wp-content/uploads/products/{model_lower}/DataSheet_{model}_EN.pdf",
            "https://www.hanwhavision.com/wp-content/uploads/{model}/DataSheet_{model}_EN.pdf",
            # Hanwha America
            "https://hanwhavisionamerica.com/wp-content/uploads/2024/01/{model}-Datasheet.pdf",
            "https://hanwhavisionamerica.com/wp-content/uploads/2023/01/{model}-Datasheet.pdf",
            # Legacy Samsung/Hanwha CDNs
            "https://www.hanwhasecurity.com/wp-content/uploads/{model}/{model}_Spec_Sheet.pdf",
        ],
        "search_hint": "site:hanwhavision.com OR site:hanwhavision.eu datasheet",
    },
    "samsung": {  # Hanwha was Samsung - use same patterns
        "patterns": [
            "https://hanwhavision.eu/wp-content/uploads/products/{model}/DataSheet_{model}_EN.pdf",
        ],
        "search_hint": "site:hanwhavision.com datasheet",
    },
    "vivotek": {
        "patterns": [
            "https://www.vivotek.com/website/uploads/ProductDatasheet/{model}.pdf",
        ],
        "search_hint": "site:vivotek.com datasheet",
    },
    "uniview": {
        "patterns": [
            "https://global.uniview.com/Support/Download_Center/Datasheet/Network_Camera/{model}.pdf",
        ],
        "search_hint": "site:uniview.com datasheet",
    },
    "hikvision": {
        "patterns": [
            "https://www.hikvision.com/content/dam/hikvision/products/S000000001/S000000010/{model}/Datasheet/{model}_Datasheet.pdf",
        ],
        "search_hint": "site:hikvision.com datasheet",
    },
    "dahua": {
        "patterns": [
            "https://www.dahuasecurity.com/asset/upload/uploads/soft/{model}.pdf",
        ],
        "search_hint": "site:dahuasecurity.com datasheet",
    },
    "i-pro": {
        "patterns": [
            "https://i-pro.com/products_and_solutions/assets/{model}_spec.pdf",
        ],
        "search_hint": "site:i-pro.com datasheet",
    },
    "panasonic": {  # i-PRO was Panasonic
        "patterns": [],
        "search_hint": "site:i-pro.com datasheet",
    },
}

# Keywords to search for in PDFs
SPEC_KEYWORDS = [
    "image settings",
    "resolution",
    "wdr",
    "wide dynamic range",
    "exposure",
    "shutter",
    "gain",
    "onvif profile",
    "compression",
    "bitrate",
    "h.264",
    "h.265",
    "ir range",
    "infrared",
    "low light",
    "day/night",
    "sensor",
    "lens",
    "field of view",
    "illumination",
    "lux",
]


class DatasheetFetcher:
    """Fetches and parses camera datasheet PDFs."""

    def __init__(
        self,
        download_dir: str = "./datasheets",
        timeout_seconds: int = 10,
        rate_limit_delay: float = 1.0,
    ):
        self.download_dir = download_dir
        self.timeout_seconds = timeout_seconds
        self.rate_limit_delay = rate_limit_delay
        self._last_request_time = 0

        # Ensure download directory exists
        os.makedirs(download_dir, exist_ok=True)

    async def _rate_limit(self) -> None:
        """Enforce rate limiting between requests."""
        now = asyncio.get_event_loop().time()
        elapsed = now - self._last_request_time
        if elapsed < self.rate_limit_delay:
            await asyncio.sleep(self.rate_limit_delay - elapsed)
        self._last_request_time = asyncio.get_event_loop().time()

    def _normalize_manufacturer(self, manufacturer: str) -> str:
        """Normalize manufacturer name for matching."""
        if not manufacturer:
            return ""
        normalized = manufacturer.lower().strip()
        # Handle common variations
        if "hanwha" in normalized or "samsung" in normalized:
            return "hanwha"
        if "i-pro" in normalized or "panasonic" in normalized:
            return "i-pro"
        return normalized

    def get_hardcoded_urls(
        self, manufacturer: str, model: str
    ) -> List[str]:
        """
        Get list of hardcoded datasheet URLs to try for known manufacturers.
        Returns empty list if no patterns exist.
        """
        norm_manufacturer = self._normalize_manufacturer(manufacturer)
        if norm_manufacturer not in MANUFACTURER_URLS:
            return []

        patterns = MANUFACTURER_URLS[norm_manufacturer].get("patterns", [])
        if not patterns:
            return []

        urls = []
        for pattern in patterns:
            try:
                # Replace {model} and {model_lower} placeholders
                url = pattern.format(model=model, model_lower=model.lower())
                urls.append(url)
            except KeyError:
                # Pattern has placeholder we don't have, skip it
                pass
        return urls

    def get_hardcoded_url(
        self, manufacturer: str, model: str
    ) -> Optional[str]:
        """
        Get first hardcoded datasheet URL for known manufacturers.
        Returns None if no pattern exists.
        (Backwards compatible - use get_hardcoded_urls for all patterns)
        """
        urls = self.get_hardcoded_urls(manufacturer, model)
        return urls[0] if urls else None

    async def search_datasheet_pdf(
        self, manufacturer: str, model: str
    ) -> Optional[str]:
        """
        Search for datasheet PDF using DuckDuckGo.
        Returns the first PDF URL found, or None.
        """
        try:
            from duckduckgo_search import DDGS
        except ImportError:
            logger.warning("duckduckgo-search not installed, skipping web search")
            return None

        await self._rate_limit()

        # Build search query
        norm_manufacturer = self._normalize_manufacturer(manufacturer)
        search_hint = ""
        if norm_manufacturer in MANUFACTURER_URLS:
            search_hint = MANUFACTURER_URLS[norm_manufacturer].get("search_hint", "")

        query = f"{manufacturer} {model} datasheet filetype:pdf {search_hint}".strip()
        logger.info(f"Searching for datasheet: {query}")

        try:
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=5))

            # Filter for PDF results
            pdf_urls = [
                r["href"]
                for r in results
                if r.get("href", "").lower().endswith(".pdf")
            ]

            if pdf_urls:
                logger.info(f"Found datasheet PDF: {pdf_urls[0]}")
                return pdf_urls[0]

            # If no direct PDF links, check for any promising results
            for result in results:
                href = result.get("href", "")
                if "datasheet" in href.lower() or "pdf" in href.lower():
                    logger.info(f"Found potential datasheet page: {href}")
                    return href

            logger.info(f"No datasheet PDF found for {manufacturer} {model}")
            return None

        except Exception as e:
            logger.error(f"Search failed: {e}")
            return None

    async def download_pdf(self, url: str) -> Optional[bytes]:
        """
        Download PDF from URL.
        Returns PDF content as bytes, or None on failure.
        """
        await self._rate_limit()

        headers = {"User-Agent": USER_AGENT}

        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.get(url, headers=headers, follow_redirects=True)

                if response.status_code != 200:
                    logger.error(
                        f"Failed to download PDF: HTTP {response.status_code}"
                    )
                    return None

                content_type = response.headers.get("content-type", "")
                if "pdf" not in content_type.lower() and not url.lower().endswith(".pdf"):
                    logger.warning(f"URL may not be a PDF: {content_type}")

                return response.content

        except httpx.TimeoutException:
            logger.error(f"Timeout downloading PDF from {url}")
            return None
        except Exception as e:
            logger.error(f"Error downloading PDF: {e}")
            return None

    def parse_pdf(self, pdf_content: bytes) -> Dict[str, Any]:
        """
        Parse PDF and extract relevant specifications.
        Returns dict with extracted specs and raw text.
        """
        try:
            import pdfplumber
        except ImportError:
            logger.warning("pdfplumber not installed, skipping PDF parsing")
            return {"error": "pdfplumber not installed"}

        extracted = {
            "raw_text": "",
            "relevant_sections": [],
            "specs": {},
        }

        try:
            with pdfplumber.open(BytesIO(pdf_content)) as pdf:
                all_text = []

                for page_num, page in enumerate(pdf.pages):
                    text = page.extract_text() or ""
                    all_text.append(text)

                    # Check if page contains relevant keywords
                    text_lower = text.lower()
                    for keyword in SPEC_KEYWORDS:
                        if keyword in text_lower:
                            extracted["relevant_sections"].append(
                                {
                                    "page": page_num + 1,
                                    "keyword": keyword,
                                    "text": text.strip()[:500],  # First 500 chars
                                }
                            )
                            break

                extracted["raw_text"] = "\n\n".join(all_text)

                # Extract structured specs using regex patterns
                extracted["specs"] = self._extract_structured_specs(
                    extracted["raw_text"]
                )

        except Exception as e:
            logger.error(f"Error parsing PDF: {e}")
            extracted["error"] = str(e)

        return extracted

    def _extract_structured_specs(self, text: str) -> Dict[str, Any]:
        """
        Extract structured specifications from raw text using regex.
        """
        specs = {}
        text_lower = text.lower()

        # Resolution patterns
        resolution_match = re.search(
            r"(\d{3,4})\s*[xX×]\s*(\d{3,4})", text
        )
        if resolution_match:
            specs["max_resolution"] = (
                f"{resolution_match.group(1)}x{resolution_match.group(2)}"
            )

        # Sensor size patterns
        sensor_match = re.search(
            r"(1/[0-9.]+)\s*(?:inch|\")?", text_lower
        )
        if sensor_match:
            specs["sensor_size"] = sensor_match.group(1) + " inch"

        # Min illumination patterns
        lux_match = re.search(
            r"(\d+\.?\d*)\s*lux", text_lower
        )
        if lux_match:
            specs["min_illumination"] = f"{lux_match.group(1)} lux"

        # WDR dB patterns
        wdr_match = re.search(
            r"wdr[:\s]*(\d+)\s*db", text_lower
        )
        if wdr_match:
            specs["wdr_max_db"] = int(wdr_match.group(1))

        # Codec patterns
        codecs = []
        if "h.264" in text_lower or "h264" in text_lower:
            codecs.append("H.264")
        if "h.265" in text_lower or "h265" in text_lower or "hevc" in text_lower:
            codecs.append("H.265")
        if "mjpeg" in text_lower:
            codecs.append("MJPEG")
        if codecs:
            specs["supported_codecs"] = codecs

        # Bitrate patterns
        bitrate_match = re.search(
            r"(\d+)\s*(?:mbps|mb/s)", text_lower
        )
        if bitrate_match:
            specs["max_bitrate_mbps"] = float(bitrate_match.group(1))

        # IR range patterns
        ir_match = re.search(
            r"ir[:\s]*(?:range)?[:\s]*(\d+)\s*(?:m|meters?)", text_lower
        )
        if ir_match:
            specs["ir_range_meters"] = float(ir_match.group(1))

        # ONVIF profile patterns
        onvif_profiles = []
        if "profile s" in text_lower:
            onvif_profiles.append("S")
        if "profile g" in text_lower:
            onvif_profiles.append("G")
        if "profile t" in text_lower:
            onvif_profiles.append("T")
        if "profile m" in text_lower:
            onvif_profiles.append("M")
        if onvif_profiles:
            specs["onvif_profiles"] = onvif_profiles

        # IP rating patterns
        ip_match = re.search(r"(ip\d{2})", text_lower)
        if ip_match:
            specs["ip_rating"] = ip_match.group(1).upper()

        # Power consumption patterns
        power_match = re.search(
            r"(\d+\.?\d*)\s*w(?:atts?)?", text_lower
        )
        if power_match:
            specs["power_consumption_watts"] = float(power_match.group(1))

        return specs

    async def fetch_datasheet(
        self, manufacturer: str, model: str
    ) -> Tuple[Optional[str], Dict[str, Any]]:
        """
        Fetch and parse datasheet for a camera.

        Tries in order:
        1. All hardcoded URL patterns for the manufacturer
        2. DuckDuckGo web search as fallback

        Returns:
            Tuple of (pdf_url, parsed_data) where parsed_data contains:
            - raw_text: Full extracted text
            - specs: Structured specifications dict
            - relevant_sections: List of relevant page excerpts
            - error: Error message if failed
        """
        start_time = datetime.now()
        pdf_url = None
        pdf_content = None
        parsed_data = {"error": None, "specs": {}, "raw_text": ""}

        try:
            # Try all hardcoded URLs first
            hardcoded_urls = self.get_hardcoded_urls(manufacturer, model)
            for url in hardcoded_urls:
                logger.info(f"Trying hardcoded URL: {url}")
                content = await self.download_pdf(url)
                if content:
                    pdf_url = url
                    pdf_content = content
                    logger.info(f"Successfully downloaded from: {url}")
                    break
                else:
                    logger.debug(f"URL failed: {url}")

            # Fall back to web search if no hardcoded URLs worked
            if not pdf_content:
                logger.info(f"Hardcoded URLs failed, trying web search for {manufacturer} {model}")
                search_url = await self.search_datasheet_pdf(manufacturer, model)
                if search_url:
                    pdf_content = await self.download_pdf(search_url)
                    if pdf_content:
                        pdf_url = search_url

            if pdf_content:
                parsed_data = self.parse_pdf(pdf_content)

                # Save PDF locally for caching
                if pdf_url:
                    filename = f"{manufacturer}_{model}.pdf".replace(" ", "_").replace("/", "_")
                    filepath = os.path.join(self.download_dir, filename)
                    with open(filepath, "wb") as f:
                        f.write(pdf_content)
                    parsed_data["local_filepath"] = filepath

            else:
                parsed_data["error"] = "No datasheet found or download failed"

        except Exception as e:
            logger.error(f"Error fetching datasheet: {e}")
            parsed_data["error"] = str(e)

        duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
        parsed_data["fetch_duration_ms"] = duration_ms

        return pdf_url, parsed_data


# Singleton instance
_fetcher_instance: Optional[DatasheetFetcher] = None


def get_datasheet_fetcher() -> DatasheetFetcher:
    """Get singleton DatasheetFetcher instance."""
    global _fetcher_instance
    if _fetcher_instance is None:
        _fetcher_instance = DatasheetFetcher()
    return _fetcher_instance
