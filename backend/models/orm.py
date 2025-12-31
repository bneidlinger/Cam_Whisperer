# backend/models/orm.py
"""
SQLAlchemy ORM models for persistent storage.
These models are for database persistence, separate from Pydantic API models.
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from sqlalchemy import (
    Column,
    Integer,
    BigInteger,
    String,
    Text,
    Float,
    Boolean,
    DateTime,
    JSON,
    Index,
    ForeignKey,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import Base


class User(Base):
    """Application user accounts with preferences."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    full_name = Column(String(255), nullable=True)
    hashed_password = Column(String(255), nullable=False)
    preferences = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, onupdate=func.now())
    last_login_at = Column(DateTime, nullable=True)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "email": self.email,
            "full_name": self.full_name,
            "preferences": self.preferences or {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "last_login_at": self.last_login_at.isoformat() if self.last_login_at else None,
        }


class CameraDatasheet(Base):
    """
    Stores camera datasheet information fetched from manufacturer websites.
    Used to enrich AI optimization context with manufacturer specifications.
    """

    __tablename__ = "camera_datasheets"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Camera identification
    manufacturer = Column(String(255), nullable=False, index=True)
    model = Column(String(255), nullable=False)
    model_normalized = Column(String(255), index=True)  # lowercase, no spaces

    # Source information
    pdf_url = Column(Text, nullable=True)
    pdf_filepath = Column(Text, nullable=True)
    source_type = Column(
        String(50), nullable=True
    )  # 'auto_fetch', 'manual_upload', 'hardcoded'

    # Parsed content
    raw_text = Column(Text, nullable=True)  # Full extracted text for AI
    extracted_specs = Column(JSON, nullable=True)  # Structured specs dict

    # Specific parsed fields for quick queries
    sensor_size = Column(String(50), nullable=True)
    max_resolution = Column(String(50), nullable=True)
    min_illumination = Column(String(100), nullable=True)
    wdr_max_db = Column(Integer, nullable=True)
    supported_codecs = Column(JSON, nullable=True)  # ["H.264", "H.265"]
    max_bitrate_mbps = Column(Float, nullable=True)
    ir_range_meters = Column(Float, nullable=True)
    onvif_profiles = Column(JSON, nullable=True)  # ["S", "G", "T"]

    # Metadata
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
    fetch_attempted_at = Column(DateTime, nullable=True)
    fetch_success = Column(Boolean, default=False)

    # Unique constraint on manufacturer + model
    __table_args__ = (
        Index("idx_manufacturer_model", "manufacturer", "model", unique=True),
    )

    def __repr__(self) -> str:
        return f"<CameraDatasheet({self.manufacturer} {self.model})>"

    @staticmethod
    def normalize_model(model: str) -> str:
        """Normalize model string for consistent matching."""
        if not model:
            return ""
        # Lowercase, remove spaces, dashes, underscores
        return model.lower().replace(" ", "").replace("-", "").replace("_", "")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "id": self.id,
            "manufacturer": self.manufacturer,
            "model": self.model,
            "pdf_url": self.pdf_url,
            "source_type": self.source_type,
            "extracted_specs": self.extracted_specs,
            "sensor_size": self.sensor_size,
            "max_resolution": self.max_resolution,
            "min_illumination": self.min_illumination,
            "wdr_max_db": self.wdr_max_db,
            "supported_codecs": self.supported_codecs,
            "max_bitrate_mbps": self.max_bitrate_mbps,
            "ir_range_meters": self.ir_range_meters,
            "onvif_profiles": self.onvif_profiles,
            "fetch_success": self.fetch_success,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def to_optimization_context(self) -> Optional[Dict[str, Any]]:
        """
        Convert to format suitable for AI optimization context.
        Returns None if no useful specs are available.
        """
        if not self.fetch_success and not self.extracted_specs:
            return None

        specs = {
            "manufacturer": self.manufacturer,
            "model": self.model,
            "source": self.source_type or "unknown",
        }

        # Add structured specs if available
        if self.extracted_specs:
            specs.update(self.extracted_specs)

        # Add individual parsed fields
        if self.sensor_size:
            specs["sensor_size"] = self.sensor_size
        if self.max_resolution:
            specs["max_resolution"] = self.max_resolution
        if self.min_illumination:
            specs["min_illumination"] = self.min_illumination
        if self.wdr_max_db:
            specs["wdr_max_db"] = self.wdr_max_db
        if self.supported_codecs:
            specs["supported_codecs"] = self.supported_codecs
        if self.max_bitrate_mbps:
            specs["max_bitrate_mbps"] = self.max_bitrate_mbps
        if self.ir_range_meters:
            specs["ir_range_meters"] = self.ir_range_meters
        if self.onvif_profiles:
            specs["onvif_profiles"] = self.onvif_profiles

        # Include raw text for Claude's broader understanding
        if self.raw_text:
            # Truncate to reasonable size for prompt
            max_raw_length = 2000
            specs["raw_specs_text"] = (
                self.raw_text[:max_raw_length] + "..."
                if len(self.raw_text) > max_raw_length
                else self.raw_text
            )

        return specs


class DatasheetFetchLog(Base):
    """
    Log of datasheet fetch attempts for debugging and rate limiting.
    """

    __tablename__ = "datasheet_fetch_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    manufacturer = Column(String(255), nullable=False)
    model = Column(String(255), nullable=False)
    attempted_at = Column(DateTime, default=func.now())
    success = Column(Boolean, default=False)
    error_message = Column(Text, nullable=True)
    search_query = Column(Text, nullable=True)
    result_url = Column(Text, nullable=True)
    duration_ms = Column(Integer, nullable=True)

    def __repr__(self) -> str:
        status = "success" if self.success else "failed"
        return f"<DatasheetFetchLog({self.manufacturer} {self.model} - {status})>"


class Camera(Base):
    """
    Registered camera inventory.
    Stores camera metadata, credentials, and capabilities for persistent tracking.
    """

    __tablename__ = "cameras"

    id = Column(String(64), primary_key=True)  # UUID or user-defined ID
    ip = Column(String(45), nullable=False)  # IPv4 or IPv6
    port = Column(Integer, default=80)
    vendor = Column(String(64), nullable=True)
    model = Column(String(128), nullable=True)
    location = Column(Text, nullable=True)
    scene_type = Column(String(32), nullable=True)  # Maps to SceneType enum
    purpose = Column(String(32), nullable=True)  # Maps to CameraPurpose enum

    # Capabilities as JSON for flexibility
    capabilities = Column(JSON, nullable=True)

    # Credentials (consider encryption in production)
    onvif_username = Column(String(64), nullable=True)
    onvif_password_encrypted = Column(Text, nullable=True)

    # Discovery metadata
    discovery_method = Column(String(32), nullable=True)  # 'onvif', 'wave', 'manual'
    vms_system = Column(String(64), nullable=True)  # 'wave', 'milestone', etc.
    vms_camera_id = Column(String(128), nullable=True)  # ID in the VMS

    # Timestamps
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
    last_seen_at = Column(DateTime, nullable=True)
    deleted_at = Column(DateTime, nullable=True)  # Soft delete

    # Relationships
    optimizations = relationship("Optimization", back_populates="camera")
    applied_configs = relationship("AppliedConfig", back_populates="camera")

    # Indexes
    __table_args__ = (
        Index("idx_cameras_ip", "ip"),
        Index("idx_cameras_scene_purpose", "scene_type", "purpose"),
    )

    def __repr__(self) -> str:
        return f"<Camera({self.id} - {self.vendor} {self.model} @ {self.ip})>"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "id": self.id,
            "ip": self.ip,
            "port": self.port,
            "vendor": self.vendor,
            "model": self.model,
            "location": self.location,
            "scene_type": self.scene_type,
            "purpose": self.purpose,
            "capabilities": self.capabilities,
            "discovery_method": self.discovery_method,
            "vms_system": self.vms_system,
            "vms_camera_id": self.vms_camera_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "last_seen_at": self.last_seen_at.isoformat() if self.last_seen_at else None,
        }

    def to_context(self) -> Dict[str, Any]:
        """Convert to CameraContext-compatible dict."""
        return {
            "id": self.id,
            "ip": self.ip,
            "port": self.port,
            "vendor": self.vendor,
            "model": self.model,
            "location": self.location,
            "scene_type": self.scene_type,
            "purpose": self.purpose,
        }


class Optimization(Base):
    """
    Optimization request and result audit trail.
    Stores complete history of all optimization runs for analysis and debugging.
    """

    __tablename__ = "optimizations"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Foreign key to camera (nullable for ad-hoc optimizations)
    camera_id = Column(String(64), ForeignKey("cameras.id", ondelete="SET NULL"), nullable=True)

    # Request data
    request_data = Column(JSON, nullable=False)  # Full optimization request

    # Result data
    recommended_settings = Column(JSON, nullable=False)  # RecommendedSettings as dict
    confidence = Column(Float, nullable=True)
    explanation = Column(Text, nullable=True)
    warnings = Column(JSON, nullable=True)  # List of warning strings

    # Provider info
    ai_provider = Column(String(32), nullable=True)  # 'claude-sonnet-4-5', 'heuristic', etc.
    processing_time_ms = Column(Integer, nullable=True)

    # Sample frame hash for deduplication/debugging
    sample_frame_hash = Column(String(64), nullable=True)

    # Timestamp
    created_at = Column(DateTime, default=func.now())

    # Relationships
    camera = relationship("Camera", back_populates="optimizations")
    applied_configs = relationship("AppliedConfig", back_populates="optimization")

    # Indexes
    __table_args__ = (
        Index("idx_optimizations_camera", "camera_id"),
        Index("idx_optimizations_created", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<Optimization({self.id} - camera={self.camera_id}, provider={self.ai_provider})>"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "id": self.id,
            "camera_id": self.camera_id,
            "recommended_settings": self.recommended_settings,
            "confidence": self.confidence,
            "explanation": self.explanation,
            "warnings": self.warnings,
            "ai_provider": self.ai_provider,
            "processing_time_ms": self.processing_time_ms,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class AppliedConfig(Base):
    """
    Applied configuration job tracking.
    Tracks settings applied to cameras, replacing in-memory job storage.
    """

    __tablename__ = "applied_configs"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Foreign keys
    camera_id = Column(String(64), ForeignKey("cameras.id", ondelete="SET NULL"), nullable=True)
    optimization_id = Column(Integer, ForeignKey("optimizations.id", ondelete="SET NULL"), nullable=True)

    # Settings applied
    settings = Column(JSON, nullable=False)  # The settings that were applied

    # Apply method and status
    apply_method = Column(String(32), nullable=False)  # 'onvif', 'wave', 'manual'
    status = Column(String(32), nullable=False, default="pending")  # pending, applying, success, failed, partial
    error_message = Column(Text, nullable=True)

    # Verification
    verification_result = Column(JSON, nullable=True)  # Result of post-apply verification

    # Audit info
    applied_by = Column(String(128), nullable=True)  # User or system identifier

    # Timestamps
    created_at = Column(DateTime, default=func.now())
    applied_at = Column(DateTime, nullable=True)  # When apply started
    completed_at = Column(DateTime, nullable=True)  # When apply finished

    # Relationships
    camera = relationship("Camera", back_populates="applied_configs")
    optimization = relationship("Optimization", back_populates="applied_configs")

    # Indexes
    __table_args__ = (
        Index("idx_applied_camera", "camera_id"),
        Index("idx_applied_status", "status"),
    )

    def __repr__(self) -> str:
        return f"<AppliedConfig({self.id} - camera={self.camera_id}, status={self.status})>"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "id": self.id,
            "camera_id": self.camera_id,
            "optimization_id": self.optimization_id,
            "settings": self.settings,
            "apply_method": self.apply_method,
            "status": self.status,
            "error_message": self.error_message,
            "verification_result": self.verification_result,
            "applied_by": self.applied_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "applied_at": self.applied_at.isoformat() if self.applied_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


class EmergencyRecordSession(Base):
    """
    Tracks active and historical emergency recording sessions.
    Used for backup snapshot capture when main VMS is down.
    """

    __tablename__ = "emergency_record_sessions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(64), unique=True, nullable=False, index=True)
    site_id = Column(String(64), nullable=False, index=True)

    # Configuration
    interval_seconds = Column(Integer, nullable=False)  # 5, 10, 30, 60, 300
    retention_hours = Column(Integer, default=24)
    storage_path = Column(Text, nullable=False)

    # Camera list as JSON (snapshot of cameras at session start)
    cameras_json = Column(JSON, nullable=False)

    # Status: active, paused, stopped
    status = Column(String(32), default="active", nullable=False)

    # Stats
    total_captures = Column(Integer, default=0)
    failed_captures = Column(Integer, default=0)
    storage_bytes = Column(BigInteger, default=0)

    # Timestamps
    started_at = Column(DateTime, default=func.now())
    paused_at = Column(DateTime, nullable=True)
    stopped_at = Column(DateTime, nullable=True)
    last_capture_at = Column(DateTime, nullable=True)

    # Relationships
    snapshots = relationship(
        "EmergencySnapshot",
        back_populates="session",
        cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_session_site_status", "site_id", "status"),
    )

    def __repr__(self) -> str:
        return f"<EmergencyRecordSession({self.session_id} - site={self.site_id}, status={self.status})>"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "id": self.id,
            "session_id": self.session_id,
            "site_id": self.site_id,
            "interval_seconds": self.interval_seconds,
            "retention_hours": self.retention_hours,
            "storage_path": self.storage_path,
            "cameras": self.cameras_json,
            "status": self.status,
            "total_captures": self.total_captures,
            "failed_captures": self.failed_captures,
            "storage_bytes": self.storage_bytes,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "paused_at": self.paused_at.isoformat() if self.paused_at else None,
            "stopped_at": self.stopped_at.isoformat() if self.stopped_at else None,
            "last_capture_at": self.last_capture_at.isoformat() if self.last_capture_at else None,
        }


class EmergencySnapshot(Base):
    """
    Individual snapshot records for emergency recording.
    References the session and stores file location.
    """

    __tablename__ = "emergency_snapshots"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(
        Integer,
        ForeignKey("emergency_record_sessions.id", ondelete="CASCADE"),
        nullable=False
    )

    # Camera info
    camera_id = Column(String(64), nullable=False)
    camera_ip = Column(String(45), nullable=False)

    # Capture info
    captured_at = Column(DateTime, default=func.now(), index=True)
    file_path = Column(Text, nullable=False)  # Relative to storage_path
    file_size_bytes = Column(Integer, nullable=False)
    media_type = Column(String(32), default="image/jpeg")

    # Status
    success = Column(Boolean, default=True)
    error_message = Column(Text, nullable=True)

    # Relationships
    session = relationship("EmergencyRecordSession", back_populates="snapshots")

    __table_args__ = (
        Index("idx_snapshot_session_time", "session_id", "captured_at"),
        Index("idx_snapshot_camera", "camera_id"),
    )

    def __repr__(self) -> str:
        status = "ok" if self.success else "failed"
        return f"<EmergencySnapshot({self.id} - camera={self.camera_id}, {status})>"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "id": self.id,
            "session_id": self.session_id,
            "camera_id": self.camera_id,
            "camera_ip": self.camera_ip,
            "captured_at": self.captured_at.isoformat() if self.captured_at else None,
            "file_path": self.file_path,
            "file_size_bytes": self.file_size_bytes,
            "media_type": self.media_type,
            "success": self.success,
            "error_message": self.error_message,
        }
