# backend/services/camera_service.py
"""
Camera inventory service.

Provides CRUD operations for camera management with database persistence.
Handles camera registration, updates, and queries.
"""

import logging
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any

from database import get_db_session
from models.orm import Camera

logger = logging.getLogger(__name__)


class CameraService:
    """Service for managing camera inventory in the database."""

    def register_camera(
        self,
        ip: str,
        port: int = 80,
        vendor: Optional[str] = None,
        model: Optional[str] = None,
        location: Optional[str] = None,
        scene_type: Optional[str] = None,
        purpose: Optional[str] = None,
        capabilities: Optional[Dict[str, Any]] = None,
        onvif_username: Optional[str] = None,
        onvif_password: Optional[str] = None,
        discovery_method: Optional[str] = None,
        vms_system: Optional[str] = None,
        vms_camera_id: Optional[str] = None,
        camera_id: Optional[str] = None,
    ) -> Camera:
        """
        Register a new camera or update existing by IP.

        Args:
            ip: Camera IP address (required)
            port: Camera port (default 80)
            vendor: Camera manufacturer
            model: Camera model
            location: Physical location description
            scene_type: Scene type (entrance, parking, etc.)
            purpose: Primary purpose (facial, plates, etc.)
            capabilities: Hardware capabilities dict
            onvif_username: ONVIF credentials
            onvif_password: ONVIF credentials (stored as-is for now)
            discovery_method: How camera was found (onvif, wave, manual)
            vms_system: VMS system name if applicable
            vms_camera_id: Camera ID in VMS
            camera_id: Optional custom ID (auto-generated if not provided)

        Returns:
            Created or updated Camera object
        """
        with get_db_session() as session:
            # Check for existing camera by IP
            existing = session.query(Camera).filter(
                Camera.ip == ip,
                Camera.deleted_at.is_(None)
            ).first()

            if existing:
                # Update existing camera
                logger.info(f"Updating existing camera {existing.id} at {ip}")
                if vendor:
                    existing.vendor = vendor
                if model:
                    existing.model = model
                if location:
                    existing.location = location
                if scene_type:
                    existing.scene_type = scene_type
                if purpose:
                    existing.purpose = purpose
                if capabilities:
                    existing.capabilities = capabilities
                if onvif_username:
                    existing.onvif_username = onvif_username
                if onvif_password:
                    existing.onvif_password_encrypted = onvif_password
                if discovery_method:
                    existing.discovery_method = discovery_method
                if vms_system:
                    existing.vms_system = vms_system
                if vms_camera_id:
                    existing.vms_camera_id = vms_camera_id
                existing.last_seen_at = datetime.utcnow()
                existing.port = port
                session.flush()
                # Expunge from session before returning
                session.expunge(existing)
                return existing
            else:
                # Create new camera
                new_id = camera_id or str(uuid.uuid4())[:8]
                camera = Camera(
                    id=new_id,
                    ip=ip,
                    port=port,
                    vendor=vendor,
                    model=model,
                    location=location,
                    scene_type=scene_type,
                    purpose=purpose,
                    capabilities=capabilities,
                    onvif_username=onvif_username,
                    onvif_password_encrypted=onvif_password,
                    discovery_method=discovery_method,
                    vms_system=vms_system,
                    vms_camera_id=vms_camera_id,
                    last_seen_at=datetime.utcnow(),
                )
                session.add(camera)
                session.flush()
                # Expunge from session before returning
                session.expunge(camera)
                logger.info(f"Registered new camera {new_id} at {ip}")
                return camera

    def get_camera(self, camera_id: str) -> Optional[Camera]:
        """
        Get camera by ID.

        Args:
            camera_id: Camera identifier

        Returns:
            Camera object or None if not found
        """
        with get_db_session() as session:
            camera = session.query(Camera).filter(
                Camera.id == camera_id,
                Camera.deleted_at.is_(None)
            ).first()
            if camera:
                # Detach from session for use outside context
                session.expunge(camera)
            return camera

    def get_camera_by_ip(self, ip: str, port: Optional[int] = None) -> Optional[Camera]:
        """
        Get camera by IP address.

        Args:
            ip: Camera IP address
            port: Optional port filter

        Returns:
            Camera object or None if not found
        """
        with get_db_session() as session:
            query = session.query(Camera).filter(
                Camera.ip == ip,
                Camera.deleted_at.is_(None)
            )
            if port:
                query = query.filter(Camera.port == port)
            camera = query.first()
            if camera:
                session.expunge(camera)
            return camera

    def list_cameras(
        self,
        scene_type: Optional[str] = None,
        purpose: Optional[str] = None,
        vendor: Optional[str] = None,
        discovery_method: Optional[str] = None,
        include_deleted: bool = False,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Camera]:
        """
        List cameras with optional filters.

        Args:
            scene_type: Filter by scene type
            purpose: Filter by purpose
            vendor: Filter by vendor
            discovery_method: Filter by discovery method
            include_deleted: Include soft-deleted cameras
            limit: Max results
            offset: Pagination offset

        Returns:
            List of Camera objects
        """
        with get_db_session() as session:
            query = session.query(Camera)

            if not include_deleted:
                query = query.filter(Camera.deleted_at.is_(None))

            if scene_type:
                query = query.filter(Camera.scene_type == scene_type)
            if purpose:
                query = query.filter(Camera.purpose == purpose)
            if vendor:
                query = query.filter(Camera.vendor.ilike(f"%{vendor}%"))
            if discovery_method:
                query = query.filter(Camera.discovery_method == discovery_method)

            query = query.order_by(Camera.created_at.desc())
            query = query.offset(offset).limit(limit)

            cameras = query.all()
            # Detach all from session
            for camera in cameras:
                session.expunge(camera)
            return cameras

    def update_camera(
        self,
        camera_id: str,
        **updates: Any,
    ) -> Optional[Camera]:
        """
        Update camera metadata.

        Args:
            camera_id: Camera identifier
            **updates: Fields to update

        Returns:
            Updated Camera or None if not found
        """
        allowed_fields = {
            "location", "scene_type", "purpose", "vendor", "model",
            "capabilities", "onvif_username", "onvif_password_encrypted",
            "vms_system", "vms_camera_id", "port"
        }

        with get_db_session() as session:
            camera = session.query(Camera).filter(
                Camera.id == camera_id,
                Camera.deleted_at.is_(None)
            ).first()

            if not camera:
                logger.warning(f"Camera {camera_id} not found for update")
                return None

            for key, value in updates.items():
                if key in allowed_fields and value is not None:
                    setattr(camera, key, value)

            session.flush()
            session.expunge(camera)
            logger.info(f"Updated camera {camera_id}")
            return camera

    def delete_camera(self, camera_id: str, hard: bool = False) -> bool:
        """
        Delete camera (soft delete by default).

        Args:
            camera_id: Camera identifier
            hard: If True, permanently delete

        Returns:
            True if deleted, False if not found
        """
        with get_db_session() as session:
            camera = session.query(Camera).filter(Camera.id == camera_id).first()

            if not camera:
                return False

            if hard:
                session.delete(camera)
                logger.info(f"Hard deleted camera {camera_id}")
            else:
                camera.deleted_at = datetime.utcnow()
                logger.info(f"Soft deleted camera {camera_id}")

            return True

    def touch_camera(self, camera_id: str) -> bool:
        """
        Update last_seen_at timestamp for a camera.

        Args:
            camera_id: Camera identifier

        Returns:
            True if updated, False if not found
        """
        with get_db_session() as session:
            camera = session.query(Camera).filter(
                Camera.id == camera_id,
                Camera.deleted_at.is_(None)
            ).first()

            if not camera:
                return False

            camera.last_seen_at = datetime.utcnow()
            return True

    def count_cameras(
        self,
        scene_type: Optional[str] = None,
        purpose: Optional[str] = None,
    ) -> int:
        """
        Count cameras with optional filters.

        Args:
            scene_type: Filter by scene type
            purpose: Filter by purpose

        Returns:
            Count of matching cameras
        """
        with get_db_session() as session:
            query = session.query(Camera).filter(Camera.deleted_at.is_(None))

            if scene_type:
                query = query.filter(Camera.scene_type == scene_type)
            if purpose:
                query = query.filter(Camera.purpose == purpose)

            return query.count()


# Global service instance
_camera_service: Optional[CameraService] = None


def get_camera_service() -> CameraService:
    """Get or create camera service singleton."""
    global _camera_service
    if _camera_service is None:
        _camera_service = CameraService()
    return _camera_service
