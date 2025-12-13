# backend/services/datasheet_service.py
"""
Datasheet service for managing camera datasheet cache and retrieval.
Provides high-level interface for datasheet operations.
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List

from database import get_db_session
from models.orm import CameraDatasheet, DatasheetFetchLog
from integrations.datasheet_fetcher import get_datasheet_fetcher

logger = logging.getLogger(__name__)


class DatasheetService:
    """Service for managing camera datasheets."""

    def __init__(self):
        self.fetcher = get_datasheet_fetcher()
        self._background_tasks: Dict[str, asyncio.Task] = {}

    def _cache_key(self, manufacturer: str, model: str) -> str:
        """Generate cache key for manufacturer/model combination."""
        return f"{manufacturer.lower()}:{model.lower()}"

    def get_datasheet(
        self, manufacturer: str, model: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get cached datasheet for a camera.
        Returns None if not cached.
        """
        with get_db_session() as db:
            datasheet = (
                db.query(CameraDatasheet)
                .filter(
                    CameraDatasheet.manufacturer.ilike(manufacturer),
                    CameraDatasheet.model.ilike(model),
                )
                .first()
            )

            if datasheet:
                return datasheet.to_optimization_context()

            return None

    def get_datasheet_record(
        self, manufacturer: str, model: str
    ) -> Optional[CameraDatasheet]:
        """
        Get full datasheet database record.
        Returns None if not found.
        """
        with get_db_session() as db:
            return (
                db.query(CameraDatasheet)
                .filter(
                    CameraDatasheet.manufacturer.ilike(manufacturer),
                    CameraDatasheet.model.ilike(model),
                )
                .first()
            )

    async def fetch_and_cache(
        self, manufacturer: str, model: str, force: bool = False
    ) -> Optional[Dict[str, Any]]:
        """
        Fetch datasheet from web and cache in database.

        Args:
            manufacturer: Camera manufacturer name
            model: Camera model name
            force: If True, re-fetch even if cached

        Returns:
            Parsed datasheet specs, or None if fetch failed
        """
        # Check cache first unless force refresh
        if not force:
            cached = self.get_datasheet(manufacturer, model)
            if cached:
                logger.info(f"Using cached datasheet for {manufacturer} {model}")
                return cached

        logger.info(f"Fetching datasheet for {manufacturer} {model}")

        # Fetch from web
        pdf_url, parsed_data = await self.fetcher.fetch_datasheet(
            manufacturer, model
        )

        # Log the fetch attempt
        self._log_fetch_attempt(
            manufacturer=manufacturer,
            model=model,
            success=parsed_data.get("error") is None,
            error_message=parsed_data.get("error"),
            result_url=pdf_url,
            duration_ms=parsed_data.get("fetch_duration_ms"),
        )

        # Cache the result
        if pdf_url or parsed_data.get("specs"):
            self._cache_datasheet(
                manufacturer=manufacturer,
                model=model,
                pdf_url=pdf_url,
                parsed_data=parsed_data,
                source_type="auto_fetch",
            )

            # Return optimization context
            return self.get_datasheet(manufacturer, model)

        return None

    async def get_or_fetch(
        self, manufacturer: str, model: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get cached datasheet or fetch if not available.
        Convenience method combining cache check and fetch.
        """
        # Try cache first
        cached = self.get_datasheet(manufacturer, model)
        if cached:
            return cached

        # Fetch from web
        return await self.fetch_and_cache(manufacturer, model)

    def start_background_fetch(
        self, manufacturer: str, model: str
    ) -> None:
        """
        Start background datasheet fetch task.
        Non-blocking - returns immediately.
        """
        cache_key = self._cache_key(manufacturer, model)

        # Don't start duplicate tasks
        if cache_key in self._background_tasks:
            task = self._background_tasks[cache_key]
            if not task.done():
                logger.debug(f"Background fetch already in progress for {cache_key}")
                return

        # Check if already cached
        if self.get_datasheet(manufacturer, model):
            logger.debug(f"Datasheet already cached for {cache_key}")
            return

        # Start background task
        async def fetch_task():
            try:
                await self.fetch_and_cache(manufacturer, model)
            except Exception as e:
                logger.error(f"Background fetch failed for {cache_key}: {e}")
            finally:
                # Clean up task reference
                self._background_tasks.pop(cache_key, None)

        task = asyncio.create_task(fetch_task())
        self._background_tasks[cache_key] = task
        logger.info(f"Started background datasheet fetch for {manufacturer} {model}")

    def _cache_datasheet(
        self,
        manufacturer: str,
        model: str,
        pdf_url: Optional[str],
        parsed_data: Dict[str, Any],
        source_type: str,
    ) -> None:
        """Cache datasheet in database."""
        with get_db_session() as db:
            # Check for existing record
            existing = (
                db.query(CameraDatasheet)
                .filter(
                    CameraDatasheet.manufacturer.ilike(manufacturer),
                    CameraDatasheet.model.ilike(model),
                )
                .first()
            )

            specs = parsed_data.get("specs", {})

            if existing:
                # Update existing record
                existing.pdf_url = pdf_url
                existing.pdf_filepath = parsed_data.get("local_filepath")
                existing.source_type = source_type
                existing.raw_text = parsed_data.get("raw_text", "")[:50000]  # Limit size
                existing.extracted_specs = specs
                existing.fetch_attempted_at = datetime.utcnow()
                existing.fetch_success = parsed_data.get("error") is None
                existing.updated_at = datetime.utcnow()

                # Update individual fields
                existing.sensor_size = specs.get("sensor_size")
                existing.max_resolution = specs.get("max_resolution")
                existing.min_illumination = specs.get("min_illumination")
                existing.wdr_max_db = specs.get("wdr_max_db")
                existing.supported_codecs = specs.get("supported_codecs")
                existing.max_bitrate_mbps = specs.get("max_bitrate_mbps")
                existing.ir_range_meters = specs.get("ir_range_meters")
                existing.onvif_profiles = specs.get("onvif_profiles")

            else:
                # Create new record
                datasheet = CameraDatasheet(
                    manufacturer=manufacturer,
                    model=model,
                    model_normalized=CameraDatasheet.normalize_model(model),
                    pdf_url=pdf_url,
                    pdf_filepath=parsed_data.get("local_filepath"),
                    source_type=source_type,
                    raw_text=parsed_data.get("raw_text", "")[:50000],
                    extracted_specs=specs,
                    fetch_attempted_at=datetime.utcnow(),
                    fetch_success=parsed_data.get("error") is None,
                    sensor_size=specs.get("sensor_size"),
                    max_resolution=specs.get("max_resolution"),
                    min_illumination=specs.get("min_illumination"),
                    wdr_max_db=specs.get("wdr_max_db"),
                    supported_codecs=specs.get("supported_codecs"),
                    max_bitrate_mbps=specs.get("max_bitrate_mbps"),
                    ir_range_meters=specs.get("ir_range_meters"),
                    onvif_profiles=specs.get("onvif_profiles"),
                )
                db.add(datasheet)

            db.commit()
            logger.info(f"Cached datasheet for {manufacturer} {model}")

    def _log_fetch_attempt(
        self,
        manufacturer: str,
        model: str,
        success: bool,
        error_message: Optional[str] = None,
        result_url: Optional[str] = None,
        duration_ms: Optional[int] = None,
    ) -> None:
        """Log datasheet fetch attempt for debugging."""
        with get_db_session() as db:
            log_entry = DatasheetFetchLog(
                manufacturer=manufacturer,
                model=model,
                success=success,
                error_message=error_message,
                result_url=result_url,
                duration_ms=duration_ms,
            )
            db.add(log_entry)
            db.commit()

    def save_manual_datasheet(
        self,
        manufacturer: str,
        model: str,
        specs: Dict[str, Any],
        pdf_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Save manually provided datasheet specs.

        Args:
            manufacturer: Camera manufacturer
            model: Camera model
            specs: Specification dictionary
            pdf_url: Optional URL to datasheet PDF

        Returns:
            Saved datasheet as optimization context
        """
        parsed_data = {
            "specs": specs,
            "raw_text": "",
            "error": None,
        }

        self._cache_datasheet(
            manufacturer=manufacturer,
            model=model,
            pdf_url=pdf_url,
            parsed_data=parsed_data,
            source_type="manual_upload",
        )

        return self.get_datasheet(manufacturer, model)

    def delete_datasheet(self, manufacturer: str, model: str) -> bool:
        """
        Delete cached datasheet.
        Returns True if deleted, False if not found.
        """
        with get_db_session() as db:
            deleted = (
                db.query(CameraDatasheet)
                .filter(
                    CameraDatasheet.manufacturer.ilike(manufacturer),
                    CameraDatasheet.model.ilike(model),
                )
                .delete()
            )
            db.commit()
            return deleted > 0

    def list_cached_datasheets(
        self, manufacturer: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        List all cached datasheets.
        Optionally filter by manufacturer.
        """
        with get_db_session() as db:
            query = db.query(CameraDatasheet)

            if manufacturer:
                query = query.filter(
                    CameraDatasheet.manufacturer.ilike(f"%{manufacturer}%")
                )

            datasheets = query.all()
            return [ds.to_dict() for ds in datasheets]


# Singleton instance
_service_instance: Optional[DatasheetService] = None


def get_datasheet_service() -> DatasheetService:
    """Get singleton DatasheetService instance."""
    global _service_instance
    if _service_instance is None:
        _service_instance = DatasheetService()
    return _service_instance
