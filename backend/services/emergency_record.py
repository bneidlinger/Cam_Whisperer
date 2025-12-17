# backend/services/emergency_record.py
"""
Emergency Record Service

Provides backup snapshot capture when main VMS is down.
Captures periodic snapshots from cameras with configurable intervals.
"""

import asyncio
import logging
import os
import time
import base64
import httpx
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
from uuid import uuid4
from enum import Enum

from config import get_settings
from database import get_db_session
from models.orm import EmergencyRecordSession, EmergencySnapshot

logger = logging.getLogger(__name__)
settings = get_settings()


class RecordingStatus(str, Enum):
    """Status of a recording session"""
    ACTIVE = "active"
    PAUSED = "paused"
    STOPPED = "stopped"


@dataclass
class CameraInfo:
    """Camera information for capture"""
    id: str
    ip: str
    port: int
    username: str
    password: str
    name: Optional[str] = None


@dataclass
class CaptureResult:
    """Result of a single camera capture"""
    camera_id: str
    camera_ip: str
    success: bool
    file_path: Optional[str] = None
    file_size: int = 0
    error: Optional[str] = None
    capture_time: Optional[datetime] = None


@dataclass
class RecordingStats:
    """Statistics for a recording session"""
    total_captures: int = 0
    failed_captures: int = 0
    storage_bytes: int = 0
    last_capture_at: Optional[datetime] = None
    cameras_active: int = 0
    cameras_failed: int = 0


@dataclass
class ActiveSession:
    """In-memory representation of an active recording session"""
    session_id: str
    db_id: int
    site_id: str
    interval_seconds: int
    retention_hours: int
    storage_path: Path
    cameras: List[CameraInfo]
    status: RecordingStatus
    stats: RecordingStats = field(default_factory=RecordingStats)
    started_at: datetime = field(default_factory=datetime.utcnow)
    task: Optional[asyncio.Task] = None


class EmergencyRecordService:
    """
    Service for managing emergency snapshot recording.

    Features:
    - One active session per site (enforced)
    - Background asyncio task for capture loop
    - Graceful handling of camera failures
    - Auto-resume on server restart
    - Storage cleanup based on retention
    """

    def __init__(self):
        self._sessions: Dict[str, ActiveSession] = {}  # site_id -> session
        self._cleanup_task: Optional[asyncio.Task] = None
        self._shutdown = False
        self._http_client: Optional[httpx.AsyncClient] = None

    @property
    def http_client(self) -> httpx.AsyncClient:
        """Lazy-initialized HTTP client for snapshot fetches"""
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(
                timeout=httpx.Timeout(settings.camera_snapshot_timeout_seconds),
                verify=False  # Many cameras use self-signed certs
            )
        return self._http_client

    async def start_recording(
        self,
        site_id: str,
        cameras: List[Dict[str, Any]],
        interval_seconds: int = 30,
        retention_hours: int = 24,
    ) -> Dict[str, Any]:
        """
        Start emergency recording for a site.

        Args:
            site_id: Site identifier
            cameras: List of camera dicts with id, ip, port, username, password
            interval_seconds: Capture interval (5, 10, 30, 60, 300)
            retention_hours: How long to keep snapshots

        Returns:
            Session info dict
        """
        if not settings.emergency_record_enabled:
            raise ValueError("Emergency recording is disabled in configuration")

        # Check for existing active session
        if site_id in self._sessions:
            existing = self._sessions[site_id]
            if existing.status == RecordingStatus.ACTIVE:
                raise ValueError(f"Recording already active for site {site_id}")
            elif existing.status == RecordingStatus.PAUSED:
                # Resume instead
                return await self.resume_recording(site_id)

        if not cameras:
            raise ValueError("No cameras provided for recording")

        # Validate interval
        valid_intervals = [5, 10, 30, 60, 300]
        if interval_seconds not in valid_intervals:
            interval_seconds = 30

        # Create storage directory
        storage_base = Path(settings.emergency_record_storage_path)
        storage_path = storage_base / site_id
        storage_path.mkdir(parents=True, exist_ok=True)

        # Parse camera info
        camera_list = [
            CameraInfo(
                id=cam.get("id", f"CAM-{cam.get('ip', 'unknown')}"),
                ip=cam.get("ip"),
                port=cam.get("port", 80),
                username=cam.get("username", "admin"),
                password=cam.get("password", ""),
                name=cam.get("name"),
            )
            for cam in cameras
            if cam.get("ip")
        ]

        if not camera_list:
            raise ValueError("No valid cameras with IP addresses provided")

        # Create session in database
        session_id = str(uuid4())
        cameras_json = [
            {"id": c.id, "ip": c.ip, "port": c.port, "name": c.name}
            for c in camera_list
        ]

        with get_db_session() as db:
            db_session = EmergencyRecordSession(
                session_id=session_id,
                site_id=site_id,
                interval_seconds=interval_seconds,
                retention_hours=retention_hours,
                storage_path=str(storage_path),
                cameras_json=cameras_json,
                status=RecordingStatus.ACTIVE.value,
            )
            db.add(db_session)
            db.flush()
            db_id = db_session.id

        # Create in-memory session
        session = ActiveSession(
            session_id=session_id,
            db_id=db_id,
            site_id=site_id,
            interval_seconds=interval_seconds,
            retention_hours=retention_hours,
            storage_path=storage_path,
            cameras=camera_list,
            status=RecordingStatus.ACTIVE,
        )
        session.stats.cameras_active = len(camera_list)

        # Store and start capture task
        self._sessions[site_id] = session
        session.task = asyncio.create_task(self._capture_loop(session))

        logger.info(
            f"Started emergency recording for site {site_id}: "
            f"{len(camera_list)} cameras, {interval_seconds}s interval"
        )

        return self._session_to_dict(session)

    async def stop_recording(self, site_id: str) -> bool:
        """Stop recording for a site and mark session as stopped."""
        session = self._sessions.get(site_id)
        if not session:
            return False

        # Cancel the capture task
        if session.task and not session.task.done():
            session.task.cancel()
            try:
                await session.task
            except asyncio.CancelledError:
                pass

        # Update database
        with get_db_session() as db:
            db_session = db.query(EmergencyRecordSession).filter(
                EmergencyRecordSession.id == session.db_id
            ).first()
            if db_session:
                db_session.status = RecordingStatus.STOPPED.value
                db_session.stopped_at = datetime.utcnow()
                db_session.total_captures = session.stats.total_captures
                db_session.failed_captures = session.stats.failed_captures
                db_session.storage_bytes = session.stats.storage_bytes

        # Remove from active sessions
        del self._sessions[site_id]

        logger.info(f"Stopped emergency recording for site {site_id}")
        return True

    async def pause_recording(self, site_id: str) -> bool:
        """Pause recording for a site (keeps session alive)."""
        session = self._sessions.get(site_id)
        if not session or session.status != RecordingStatus.ACTIVE:
            return False

        session.status = RecordingStatus.PAUSED

        # Update database
        with get_db_session() as db:
            db_session = db.query(EmergencyRecordSession).filter(
                EmergencyRecordSession.id == session.db_id
            ).first()
            if db_session:
                db_session.status = RecordingStatus.PAUSED.value
                db_session.paused_at = datetime.utcnow()

        logger.info(f"Paused emergency recording for site {site_id}")
        return True

    async def resume_recording(self, site_id: str) -> Dict[str, Any]:
        """Resume a paused recording session."""
        session = self._sessions.get(site_id)
        if not session:
            raise ValueError(f"No session found for site {site_id}")

        if session.status != RecordingStatus.PAUSED:
            raise ValueError(f"Session is not paused (status: {session.status})")

        session.status = RecordingStatus.ACTIVE

        # Update database
        with get_db_session() as db:
            db_session = db.query(EmergencyRecordSession).filter(
                EmergencyRecordSession.id == session.db_id
            ).first()
            if db_session:
                db_session.status = RecordingStatus.ACTIVE.value
                db_session.paused_at = None

        # Restart capture task if needed
        if session.task is None or session.task.done():
            session.task = asyncio.create_task(self._capture_loop(session))

        logger.info(f"Resumed emergency recording for site {site_id}")
        return self._session_to_dict(session)

    def get_session_status(self, site_id: str) -> Optional[Dict[str, Any]]:
        """Get status of recording session for a site."""
        session = self._sessions.get(site_id)
        if not session:
            # Check database for stopped sessions
            with get_db_session() as db:
                db_session = db.query(EmergencyRecordSession).filter(
                    EmergencyRecordSession.site_id == site_id
                ).order_by(EmergencyRecordSession.started_at.desc()).first()
                if db_session:
                    return db_session.to_dict()
            return None
        return self._session_to_dict(session)

    def get_all_sessions(self) -> List[Dict[str, Any]]:
        """Get status of all active recording sessions."""
        return [self._session_to_dict(s) for s in self._sessions.values()]

    async def _capture_loop(self, session: ActiveSession):
        """
        Main capture loop - runs until stopped or paused.
        Captures from all cameras concurrently with semaphore limiting.
        """
        semaphore = asyncio.Semaphore(settings.emergency_record_max_concurrent_captures)
        sequence = 0

        logger.info(f"Capture loop started for session {session.session_id}")

        while not self._shutdown:
            if session.status != RecordingStatus.ACTIVE:
                # Paused - wait and check again
                await asyncio.sleep(1)
                continue

            capture_start = time.time()
            now = datetime.utcnow()

            # Create date/hour folder structure
            date_folder = session.storage_path / now.strftime("%Y-%m-%d") / now.strftime("%H")
            date_folder.mkdir(parents=True, exist_ok=True)

            # Capture from all cameras concurrently
            tasks = [
                self._capture_camera(cam, session, date_folder, sequence, semaphore)
                for cam in session.cameras
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Process results
            successful = 0
            failed = 0
            total_size = 0

            for result in results:
                if isinstance(result, Exception):
                    failed += 1
                    logger.warning(f"Capture exception: {result}")
                elif isinstance(result, CaptureResult):
                    if result.success:
                        successful += 1
                        total_size += result.file_size
                        # Save to database
                        self._save_snapshot_record(session, result)
                    else:
                        failed += 1

            # Update stats
            session.stats.total_captures += successful
            session.stats.failed_captures += failed
            session.stats.storage_bytes += total_size
            session.stats.last_capture_at = now
            session.stats.cameras_active = successful
            session.stats.cameras_failed = failed

            # Periodically update database
            if sequence % 10 == 0:
                self._update_session_stats(session)

            sequence += 1

            # Calculate sleep time
            elapsed = time.time() - capture_start
            sleep_time = max(0.1, session.interval_seconds - elapsed)

            try:
                await asyncio.sleep(sleep_time)
            except asyncio.CancelledError:
                logger.info(f"Capture loop cancelled for session {session.session_id}")
                break

        logger.info(f"Capture loop ended for session {session.session_id}")

    async def _capture_camera(
        self,
        camera: CameraInfo,
        session: ActiveSession,
        folder: Path,
        sequence: int,
        semaphore: asyncio.Semaphore,
    ) -> CaptureResult:
        """Capture snapshot from a single camera."""
        async with semaphore:
            try:
                # Get snapshot via ONVIF
                snapshot_data, media_type = await self._fetch_snapshot_onvif(camera)

                if not snapshot_data:
                    return CaptureResult(
                        camera_id=camera.id,
                        camera_ip=camera.ip,
                        success=False,
                        error="No snapshot data received",
                    )

                # Determine file extension
                ext = "jpg" if "jpeg" in media_type else media_type.split("/")[-1]

                # Generate filename
                now = datetime.utcnow()
                filename = f"{camera.id}_{now.strftime('%H%M%S')}_{sequence:04d}.{ext}"
                file_path = folder / filename

                # Save file
                with open(file_path, "wb") as f:
                    f.write(snapshot_data)

                file_size = len(snapshot_data)

                # Return relative path from storage root
                relative_path = str(file_path.relative_to(session.storage_path))

                return CaptureResult(
                    camera_id=camera.id,
                    camera_ip=camera.ip,
                    success=True,
                    file_path=relative_path,
                    file_size=file_size,
                    capture_time=now,
                )

            except Exception as e:
                logger.debug(f"Failed to capture from {camera.id}: {e}")
                return CaptureResult(
                    camera_id=camera.id,
                    camera_ip=camera.ip,
                    success=False,
                    error=str(e),
                )

    async def _fetch_snapshot_onvif(self, camera: CameraInfo) -> tuple:
        """
        Fetch snapshot from camera via ONVIF.
        Returns (image_bytes, media_type) or (None, None) on failure.
        """
        try:
            # Import here to avoid circular imports
            from integrations.onvif_client import ONVIFClient

            client = ONVIFClient()

            # Connect and get snapshot URI
            onvif_camera = await client.connect_camera(
                camera.ip,
                camera.port,
                camera.username,
                camera.password,
            )

            # Get media profiles
            profiles = await client.get_media_profiles(onvif_camera)
            if not profiles:
                return None, None

            # Get snapshot URI from first profile
            profile_token = profiles[0].get("token")
            snapshot_uri = await client.get_snapshot_uri(onvif_camera, profile_token)

            if not snapshot_uri:
                return None, None

            # Fetch the actual image
            auth = httpx.DigestAuth(camera.username, camera.password)
            response = await self.http_client.get(snapshot_uri, auth=auth)

            if response.status_code == 200:
                media_type = response.headers.get("content-type", "image/jpeg")
                return response.content, media_type

            return None, None

        except Exception as e:
            logger.debug(f"ONVIF snapshot fetch failed for {camera.ip}: {e}")
            return None, None

    def _save_snapshot_record(self, session: ActiveSession, result: CaptureResult):
        """Save snapshot record to database."""
        try:
            with get_db_session() as db:
                snapshot = EmergencySnapshot(
                    session_id=session.db_id,
                    camera_id=result.camera_id,
                    camera_ip=result.camera_ip,
                    captured_at=result.capture_time or datetime.utcnow(),
                    file_path=result.file_path or "",
                    file_size_bytes=result.file_size,
                    success=result.success,
                    error_message=result.error,
                )
                db.add(snapshot)
        except Exception as e:
            logger.warning(f"Failed to save snapshot record: {e}")

    def _update_session_stats(self, session: ActiveSession):
        """Update session statistics in database."""
        try:
            with get_db_session() as db:
                db_session = db.query(EmergencyRecordSession).filter(
                    EmergencyRecordSession.id == session.db_id
                ).first()
                if db_session:
                    db_session.total_captures = session.stats.total_captures
                    db_session.failed_captures = session.stats.failed_captures
                    db_session.storage_bytes = session.stats.storage_bytes
                    db_session.last_capture_at = session.stats.last_capture_at
        except Exception as e:
            logger.warning(f"Failed to update session stats: {e}")

    def _session_to_dict(self, session: ActiveSession) -> Dict[str, Any]:
        """Convert ActiveSession to dict for API response."""
        return {
            "session_id": session.session_id,
            "site_id": session.site_id,
            "interval_seconds": session.interval_seconds,
            "retention_hours": session.retention_hours,
            "status": session.status.value,
            "cameras": [
                {"id": c.id, "ip": c.ip, "port": c.port, "name": c.name}
                for c in session.cameras
            ],
            "camera_count": len(session.cameras),
            "stats": {
                "total_captures": session.stats.total_captures,
                "failed_captures": session.stats.failed_captures,
                "storage_bytes": session.stats.storage_bytes,
                "storage_mb": round(session.stats.storage_bytes / (1024 * 1024), 2),
                "last_capture_at": session.stats.last_capture_at.isoformat() if session.stats.last_capture_at else None,
                "cameras_active": session.stats.cameras_active,
                "cameras_failed": session.stats.cameras_failed,
            },
            "started_at": session.started_at.isoformat() if session.started_at else None,
            "active": session.status == RecordingStatus.ACTIVE,
        }

    async def restore_sessions(self):
        """
        Restore active/paused sessions from database on startup.
        Called during application startup for auto-resume.
        """
        try:
            with get_db_session() as db:
                # Find sessions that were active or paused when server stopped
                sessions = db.query(EmergencyRecordSession).filter(
                    EmergencyRecordSession.status.in_([
                        RecordingStatus.ACTIVE.value,
                        RecordingStatus.PAUSED.value
                    ])
                ).all()

                for db_session in sessions:
                    logger.info(
                        f"Restoring emergency record session {db_session.session_id} "
                        f"for site {db_session.site_id}"
                    )

                    # Parse cameras from JSON - but we need credentials
                    # Since credentials aren't stored in DB, mark as paused
                    # User will need to resume with credentials
                    db_session.status = RecordingStatus.PAUSED.value
                    db_session.paused_at = datetime.utcnow()

                    logger.warning(
                        f"Session {db_session.session_id} marked as paused - "
                        "credentials required to resume"
                    )

        except Exception as e:
            logger.error(f"Failed to restore emergency record sessions: {e}")

    async def cleanup_old_snapshots(self, site_id: Optional[str] = None, older_than_hours: Optional[int] = None):
        """
        Clean up snapshots older than retention period.

        Args:
            site_id: Optional site to clean (all sites if None)
            older_than_hours: Override retention hours
        """
        try:
            with get_db_session() as db:
                query = db.query(EmergencySnapshot).join(EmergencyRecordSession)

                if site_id:
                    query = query.filter(EmergencyRecordSession.site_id == site_id)

                # Get sessions to determine retention
                if older_than_hours:
                    cutoff = datetime.utcnow() - timedelta(hours=older_than_hours)
                else:
                    # Use default retention
                    cutoff = datetime.utcnow() - timedelta(
                        hours=settings.emergency_record_default_retention_hours
                    )

                old_snapshots = query.filter(
                    EmergencySnapshot.captured_at < cutoff
                ).all()

                deleted_count = 0
                freed_bytes = 0

                for snapshot in old_snapshots:
                    # Delete file
                    try:
                        session = snapshot.session
                        if session:
                            file_path = Path(session.storage_path) / snapshot.file_path
                            if file_path.exists():
                                freed_bytes += file_path.stat().st_size
                                file_path.unlink()
                    except Exception as e:
                        logger.debug(f"Failed to delete snapshot file: {e}")

                    db.delete(snapshot)
                    deleted_count += 1

                logger.info(
                    f"Cleaned up {deleted_count} old snapshots, "
                    f"freed {freed_bytes / (1024*1024):.2f} MB"
                )

                return {
                    "deleted_count": deleted_count,
                    "freed_bytes": freed_bytes,
                    "freed_mb": round(freed_bytes / (1024 * 1024), 2),
                }

        except Exception as e:
            logger.error(f"Failed to cleanup snapshots: {e}")
            return {"deleted_count": 0, "freed_bytes": 0, "error": str(e)}

    def get_storage_stats(self) -> Dict[str, Any]:
        """Get storage usage statistics."""
        storage_path = Path(settings.emergency_record_storage_path)

        if not storage_path.exists():
            return {
                "total_bytes": 0,
                "total_mb": 0,
                "max_gb": settings.emergency_record_max_storage_gb,
                "usage_percent": 0,
                "sites": [],
            }

        total_bytes = 0
        sites = []

        for site_dir in storage_path.iterdir():
            if site_dir.is_dir():
                site_bytes = sum(
                    f.stat().st_size
                    for f in site_dir.rglob("*")
                    if f.is_file()
                )
                total_bytes += site_bytes
                sites.append({
                    "site_id": site_dir.name,
                    "bytes": site_bytes,
                    "mb": round(site_bytes / (1024 * 1024), 2),
                })

        max_bytes = settings.emergency_record_max_storage_gb * 1024 * 1024 * 1024
        usage_percent = (total_bytes / max_bytes * 100) if max_bytes > 0 else 0

        return {
            "total_bytes": total_bytes,
            "total_mb": round(total_bytes / (1024 * 1024), 2),
            "total_gb": round(total_bytes / (1024 * 1024 * 1024), 3),
            "max_gb": settings.emergency_record_max_storage_gb,
            "usage_percent": round(usage_percent, 1),
            "sites": sites,
        }

    async def shutdown(self):
        """Graceful shutdown - stop all capture tasks."""
        self._shutdown = True

        for site_id, session in list(self._sessions.items()):
            logger.info(f"Stopping emergency record session for site {site_id}")

            if session.task and not session.task.done():
                session.task.cancel()
                try:
                    await session.task
                except asyncio.CancelledError:
                    pass

            # Mark as paused in database (not stopped, for auto-resume)
            with get_db_session() as db:
                db_session = db.query(EmergencyRecordSession).filter(
                    EmergencyRecordSession.id == session.db_id
                ).first()
                if db_session:
                    db_session.status = RecordingStatus.PAUSED.value
                    db_session.paused_at = datetime.utcnow()
                    db_session.total_captures = session.stats.total_captures
                    db_session.failed_captures = session.stats.failed_captures
                    db_session.storage_bytes = session.stats.storage_bytes

        # Close HTTP client
        if self._http_client:
            await self._http_client.aclose()

        self._sessions.clear()
        logger.info("Emergency record service shutdown complete")


# Global service instance
_emergency_record_service: Optional[EmergencyRecordService] = None


def get_emergency_record_service() -> EmergencyRecordService:
    """Get or create emergency record service singleton."""
    global _emergency_record_service
    if _emergency_record_service is None:
        _emergency_record_service = EmergencyRecordService()
    return _emergency_record_service
