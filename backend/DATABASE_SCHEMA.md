# CamOpt AI - Database Schema Documentation

**Version:** 0.2.0
**Database Engine:** PostgreSQL 15+ (Production) / SQLite 3 (Development)
**ORM:** SQLAlchemy 2.0+
**Migrations:** Alembic

---

## Table of Contents

1. [Overview](#overview)
2. [Entity Relationship Diagram](#entity-relationship-diagram)
3. [Table Definitions](#table-definitions)
4. [Indexes & Constraints](#indexes--constraints)
5. [SQLAlchemy Models](#sqlalchemy-models)
6. [Migration Strategy](#migration-strategy)
7. [Sample Queries](#sample-queries)

---

## Overview

The CamOpt AI database stores:
- **Camera inventory** - Physical cameras and their metadata
- **Optimization history** - AI recommendations and heuristic outputs
- **Applied configurations** - Settings pushed to cameras/VMS
- **Monitoring data** - Health metrics and snapshots over time
- **User accounts** (future) - Authentication and authorization

**Design Principles:**
- Use JSONB for flexible settings storage (PostgreSQL) or JSON (SQLite)
- Timestamped records for audit trails
- Foreign key constraints for data integrity
- Indexes on frequently queried fields

---

## Entity Relationship Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│  ┌─────────────────┐                                            │
│  │    cameras      │                                            │
│  ├─────────────────┤                                            │
│  │ id (PK)         │                                            │
│  │ ip              │                                            │
│  │ vendor          │                                            │
│  │ model           │                                            │
│  │ vms_system      │                                            │
│  │ scene_type      │                                            │
│  │ purpose         │                                            │
│  │ created_at      │                                            │
│  │ updated_at      │                                            │
│  └────────┬────────┘                                            │
│           │                                                     │
│           │ 1:N                                                 │
│           ├──────────────────┬──────────────────┬───────────┐   │
│           │                  │                  │           │   │
│           ▼                  ▼                  ▼           ▼   │
│  ┌─────────────────┐ ┌──────────────┐ ┌─────────────┐ ┌────────┤
│  │ optimizations   │ │applied_configs│ │ snapshots   │ │ health_│
│  ├─────────────────┤ ├──────────────┤ ├─────────────┤ │metrics │
│  │ id (PK)         │ │ id (PK)      │ │ id (PK)     │ ├────────┤
│  │ camera_id (FK)  │ │ camera_id(FK)│ │ camera_id   │ │ id(PK) │
│  │ request_data    │ │ optimization │ │ file_path   │ │ camera │
│  │ recommended     │ │ _id (FK)     │ │ captured_at │ │ _id(FK)│
│  │ confidence      │ │ settings     │ │ health      │ │ metric │
│  │ warnings        │ │ apply_method │ │ _metrics    │ │ _type  │
│  │ explanation     │ │ status       │ │ anomalies   │ │ value  │
│  │ ai_provider     │ │ applied_at   │ └─────────────┘ │ created│
│  │ created_at      │ │ applied_by   │                 │ _at    │
│  └─────────────────┘ └──────────────┘                 └────────┘
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Table Definitions

### 1. `cameras`

Stores camera inventory and metadata.

```sql
CREATE TABLE cameras (
    id VARCHAR(64) PRIMARY KEY,
    ip VARCHAR(45) NOT NULL,
    vendor VARCHAR(64),
    model VARCHAR(128),
    vms_system VARCHAR(64),
    vms_camera_id VARCHAR(128),
    location TEXT,
    scene_type VARCHAR(32),
    purpose VARCHAR(32),
    capabilities JSONB,
    credentials_encrypted TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT valid_ip CHECK (ip ~ '^[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}$')
);
```

**Fields:**
| Field | Type | Nullable | Description |
|-------|------|----------|-------------|
| `id` | VARCHAR(64) | NO | Unique camera identifier (user-defined or auto-generated) |
| `ip` | VARCHAR(45) | NO | IPv4 or IPv6 address |
| `vendor` | VARCHAR(64) | YES | Manufacturer (Hanwha, Axis, Hikvision, etc.) |
| `model` | VARCHAR(128) | YES | Model number |
| `vms_system` | VARCHAR(64) | YES | VMS platform (genetec, milestone, avigilon, etc.) |
| `vms_camera_id` | VARCHAR(128) | YES | VMS internal UUID or ID |
| `location` | TEXT | YES | Human-readable location (e.g., "L1 North Hallway") |
| `scene_type` | VARCHAR(32) | YES | Scene classification (hallway, parking, entrance, etc.) |
| `purpose` | VARCHAR(32) | YES | Operational purpose (overview, facial, plates, etc.) |
| `capabilities` | JSONB | YES | Hardware capabilities (max resolution, codecs, WDR, etc.) |
| `credentials_encrypted` | TEXT | YES | Encrypted username/password for camera access |
| `created_at` | TIMESTAMP | NO | Record creation timestamp |
| `updated_at` | TIMESTAMP | NO | Last update timestamp |

**Example Row:**
```json
{
  "id": "cam-lobby-01",
  "ip": "192.168.1.110",
  "vendor": "Hanwha",
  "model": "QNV-7080R",
  "vms_system": "genetec",
  "vms_camera_id": "gen-uuid-abc123",
  "location": "Main Lobby",
  "scene_type": "entrance",
  "purpose": "facial",
  "capabilities": {
    "maxResolution": "3840x2160",
    "supportedCodecs": ["H.264", "H.265"],
    "maxFps": 30,
    "wdrLevels": ["Off", "Low", "Medium", "High"]
  },
  "created_at": "2025-12-05T10:30:00Z",
  "updated_at": "2025-12-05T10:30:00Z"
}
```

---

### 2. `optimizations`

Stores AI-generated and heuristic optimization recommendations.

```sql
CREATE TABLE optimizations (
    id SERIAL PRIMARY KEY,
    camera_id VARCHAR(64) NOT NULL REFERENCES cameras(id) ON DELETE CASCADE,
    request_data JSONB NOT NULL,
    recommended_settings JSONB NOT NULL,
    confidence FLOAT CHECK (confidence >= 0 AND confidence <= 1),
    warnings JSONB,
    explanation TEXT,
    ai_provider VARCHAR(32),
    processing_time_ms INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT valid_ai_provider CHECK (ai_provider IN ('claude-sonnet-4-5', 'heuristic'))
);
```

**Fields:**
| Field | Type | Nullable | Description |
|-------|------|----------|-------------|
| `id` | SERIAL | NO | Auto-incrementing primary key |
| `camera_id` | VARCHAR(64) | NO | Foreign key to `cameras.id` |
| `request_data` | JSONB | NO | Full OptimizeRequest payload (for reproducibility) |
| `recommended_settings` | JSONB | NO | Generated settings (stream, exposure, lowLight, image) |
| `confidence` | FLOAT | YES | Confidence score 0.0-1.0 |
| `warnings` | JSONB | YES | Array of warning messages |
| `explanation` | TEXT | YES | Human-readable justification from AI |
| `ai_provider` | VARCHAR(32) | YES | "claude-sonnet-4-5" or "heuristic" |
| `processing_time_ms` | INTEGER | YES | API response time in milliseconds |
| `created_at` | TIMESTAMP | NO | When optimization was generated |

**Example Row:**
```json
{
  "id": 1,
  "camera_id": "cam-lobby-01",
  "request_data": {
    "camera": {...},
    "capabilities": {...},
    "currentSettings": {...},
    "context": {...}
  },
  "recommended_settings": {
    "stream": {"resolution": "1920x1080", "codec": "H.265", "fps": 20},
    "exposure": {"shutter": "1/250", "wdr": "High"}
  },
  "confidence": 0.87,
  "warnings": ["Bandwidth limit tight for 1080p"],
  "explanation": "This entrance camera shows challenging lighting...",
  "ai_provider": "claude-sonnet-4-5",
  "processing_time_ms": 8432,
  "created_at": "2025-12-05T10:50:00Z"
}
```

---

### 3. `applied_configs`

Tracks configuration changes pushed to cameras/VMS.

```sql
CREATE TABLE applied_configs (
    id SERIAL PRIMARY KEY,
    camera_id VARCHAR(64) NOT NULL REFERENCES cameras(id) ON DELETE CASCADE,
    optimization_id INTEGER REFERENCES optimizations(id) ON DELETE SET NULL,
    settings JSONB NOT NULL,
    apply_method VARCHAR(32) NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'pending',
    applied_at TIMESTAMP,
    applied_by VARCHAR(128),
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT valid_apply_method CHECK (apply_method IN ('onvif', 'vms', 'vendor', 'manual')),
    CONSTRAINT valid_status CHECK (status IN ('pending', 'in_progress', 'success', 'failed', 'partial'))
);
```

**Fields:**
| Field | Type | Nullable | Description |
|-------|------|----------|-------------|
| `id` | SERIAL | NO | Auto-incrementing primary key |
| `camera_id` | VARCHAR(64) | NO | Foreign key to `cameras.id` |
| `optimization_id` | INTEGER | YES | Foreign key to `optimizations.id` (null if manual config) |
| `settings` | JSONB | NO | Settings that were applied |
| `apply_method` | VARCHAR(32) | NO | "onvif", "vms", "vendor", or "manual" |
| `status` | VARCHAR(32) | NO | "pending", "in_progress", "success", "failed", "partial" |
| `applied_at` | TIMESTAMP | YES | When configuration was successfully applied |
| `applied_by` | VARCHAR(128) | YES | User ID or system identifier |
| `error_message` | TEXT | YES | Error details if status = "failed" |
| `created_at` | TIMESTAMP | NO | When apply job was created |

**Example Row:**
```json
{
  "id": 1,
  "camera_id": "cam-lobby-01",
  "optimization_id": 1,
  "settings": {
    "stream": {"resolution": "1920x1080", "codec": "H.265", "fps": 20}
  },
  "apply_method": "onvif",
  "status": "success",
  "applied_at": "2025-12-05T10:52:15Z",
  "applied_by": "admin",
  "error_message": null,
  "created_at": "2025-12-05T10:51:00Z"
}
```

---

### 4. `snapshots`

Stores camera snapshot images and associated health metrics.

```sql
CREATE TABLE snapshots (
    id SERIAL PRIMARY KEY,
    camera_id VARCHAR(64) NOT NULL REFERENCES cameras(id) ON DELETE CASCADE,
    file_path VARCHAR(512) NOT NULL,
    captured_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    health_metrics JSONB,
    anomalies JSONB,
    CONSTRAINT unique_snapshot UNIQUE (camera_id, captured_at)
);
```

**Fields:**
| Field | Type | Nullable | Description |
|-------|------|----------|-------------|
| `id` | SERIAL | NO | Auto-incrementing primary key |
| `camera_id` | VARCHAR(64) | NO | Foreign key to `cameras.id` |
| `file_path` | VARCHAR(512) | NO | Relative path to snapshot file |
| `captured_at` | TIMESTAMP | NO | When snapshot was captured |
| `health_metrics` | JSONB | YES | Computed quality metrics (brightness, noise, blur) |
| `anomalies` | JSONB | YES | Detected issues (too dark, high noise, etc.) |

**Example Row:**
```json
{
  "id": 1,
  "camera_id": "cam-lobby-01",
  "file_path": "uploads/cameras/cam-lobby-01/snapshots/2025-12-05T10-55-00.jpg",
  "captured_at": "2025-12-05T10:55:00Z",
  "health_metrics": {
    "exposure": {"status": "ok", "meanBrightness": 118},
    "noise": {"status": "warning", "noiseLevel": 12.5},
    "motionBlur": {"status": "ok", "blurScore": 3.2}
  },
  "anomalies": [
    {"type": "high_noise", "severity": "medium", "message": "Noise exceeds threshold"}
  ]
}
```

---

### 5. `health_metrics`

Time-series health metrics for cameras (denormalized for analytics).

```sql
CREATE TABLE health_metrics (
    id SERIAL PRIMARY KEY,
    camera_id VARCHAR(64) NOT NULL REFERENCES cameras(id) ON DELETE CASCADE,
    metric_type VARCHAR(32) NOT NULL,
    value FLOAT NOT NULL,
    status VARCHAR(16),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT valid_metric_type CHECK (metric_type IN (
        'brightness', 'noise_level', 'blur_score', 'bitrate_mbps',
        'fps_actual', 'frame_drops', 'latency_ms'
    )),
    CONSTRAINT valid_status CHECK (status IN ('ok', 'warning', 'critical'))
);
```

**Fields:**
| Field | Type | Nullable | Description |
|-------|------|----------|-------------|
| `id` | SERIAL | NO | Auto-incrementing primary key |
| `camera_id` | VARCHAR(64) | NO | Foreign key to `cameras.id` |
| `metric_type` | VARCHAR(32) | NO | Type of metric (brightness, noise, bitrate, etc.) |
| `value` | FLOAT | NO | Numeric metric value |
| `status` | VARCHAR(16) | YES | Health status (ok, warning, critical) |
| `created_at` | TIMESTAMP | NO | When metric was recorded |

**Purpose:** Allows for time-series queries like "show me bitrate over the last 24 hours".

---

### 6. `users` (Future)

User accounts for authentication.

```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(64) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role VARCHAR(32) NOT NULL DEFAULT 'operator',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP,
    CONSTRAINT valid_role CHECK (role IN ('admin', 'operator', 'viewer'))
);
```

---

## Indexes & Constraints

### Primary Indexes

```sql
-- Cameras
CREATE INDEX idx_cameras_ip ON cameras(ip);
CREATE INDEX idx_cameras_vms ON cameras(vms_system, vms_camera_id);
CREATE INDEX idx_cameras_scene_purpose ON cameras(scene_type, purpose);

-- Optimizations
CREATE INDEX idx_optimizations_camera ON optimizations(camera_id);
CREATE INDEX idx_optimizations_created ON optimizations(created_at DESC);
CREATE INDEX idx_optimizations_provider ON optimizations(ai_provider);

-- Applied Configs
CREATE INDEX idx_applied_camera ON applied_configs(camera_id);
CREATE INDEX idx_applied_status ON applied_configs(status);
CREATE INDEX idx_applied_created ON applied_configs(created_at DESC);

-- Snapshots
CREATE INDEX idx_snapshots_camera ON snapshots(camera_id);
CREATE INDEX idx_snapshots_captured ON snapshots(captured_at DESC);

-- Health Metrics
CREATE INDEX idx_health_camera_time ON health_metrics(camera_id, created_at DESC);
CREATE INDEX idx_health_metric_type ON health_metrics(metric_type, created_at DESC);
```

### Foreign Key Constraints

```sql
ALTER TABLE optimizations
    ADD CONSTRAINT fk_opt_camera
    FOREIGN KEY (camera_id) REFERENCES cameras(id) ON DELETE CASCADE;

ALTER TABLE applied_configs
    ADD CONSTRAINT fk_apply_camera
    FOREIGN KEY (camera_id) REFERENCES cameras(id) ON DELETE CASCADE;

ALTER TABLE applied_configs
    ADD CONSTRAINT fk_apply_optimization
    FOREIGN KEY (optimization_id) REFERENCES optimizations(id) ON DELETE SET NULL;

ALTER TABLE snapshots
    ADD CONSTRAINT fk_snap_camera
    FOREIGN KEY (camera_id) REFERENCES cameras(id) ON DELETE CASCADE;

ALTER TABLE health_metrics
    ADD CONSTRAINT fk_health_camera
    FOREIGN KEY (camera_id) REFERENCES cameras(id) ON DELETE CASCADE;
```

---

## SQLAlchemy Models

**File:** `backend/models.py`

```python
from sqlalchemy import (
    Column, String, Integer, Float, Text, TIMESTAMP,
    ForeignKey, CheckConstraint, Index
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship, declarative_base
from datetime import datetime

Base = declarative_base()

class Camera(Base):
    __tablename__ = 'cameras'

    id = Column(String(64), primary_key=True)
    ip = Column(String(45), nullable=False)
    vendor = Column(String(64))
    model = Column(String(128))
    vms_system = Column(String(64))
    vms_camera_id = Column(String(128))
    location = Column(Text)
    scene_type = Column(String(32))
    purpose = Column(String(32))
    capabilities = Column(JSONB)
    credentials_encrypted = Column(Text)
    created_at = Column(TIMESTAMP, default=datetime.utcnow, nullable=False)
    updated_at = Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    optimizations = relationship("Optimization", back_populates="camera", cascade="all, delete-orphan")
    applied_configs = relationship("AppliedConfig", back_populates="camera", cascade="all, delete-orphan")
    snapshots = relationship("Snapshot", back_populates="camera", cascade="all, delete-orphan")
    health_metrics = relationship("HealthMetric", back_populates="camera", cascade="all, delete-orphan")

    # Indexes
    __table_args__ = (
        Index('idx_cameras_ip', 'ip'),
        Index('idx_cameras_vms', 'vms_system', 'vms_camera_id'),
        Index('idx_cameras_scene_purpose', 'scene_type', 'purpose'),
    )


class Optimization(Base):
    __tablename__ = 'optimizations'

    id = Column(Integer, primary_key=True, autoincrement=True)
    camera_id = Column(String(64), ForeignKey('cameras.id', ondelete='CASCADE'), nullable=False)
    request_data = Column(JSONB, nullable=False)
    recommended_settings = Column(JSONB, nullable=False)
    confidence = Column(Float)
    warnings = Column(JSONB)
    explanation = Column(Text)
    ai_provider = Column(String(32))
    processing_time_ms = Column(Integer)
    created_at = Column(TIMESTAMP, default=datetime.utcnow, nullable=False)

    # Relationships
    camera = relationship("Camera", back_populates="optimizations")
    applied_configs = relationship("AppliedConfig", back_populates="optimization")

    # Constraints
    __table_args__ = (
        CheckConstraint('confidence >= 0 AND confidence <= 1', name='valid_confidence'),
        CheckConstraint("ai_provider IN ('claude-sonnet-4-5', 'heuristic')", name='valid_ai_provider'),
        Index('idx_optimizations_camera', 'camera_id'),
        Index('idx_optimizations_created', 'created_at'),
    )


class AppliedConfig(Base):
    __tablename__ = 'applied_configs'

    id = Column(Integer, primary_key=True, autoincrement=True)
    camera_id = Column(String(64), ForeignKey('cameras.id', ondelete='CASCADE'), nullable=False)
    optimization_id = Column(Integer, ForeignKey('optimizations.id', ondelete='SET NULL'))
    settings = Column(JSONB, nullable=False)
    apply_method = Column(String(32), nullable=False)
    status = Column(String(32), nullable=False, default='pending')
    applied_at = Column(TIMESTAMP)
    applied_by = Column(String(128))
    error_message = Column(Text)
    created_at = Column(TIMESTAMP, default=datetime.utcnow, nullable=False)

    # Relationships
    camera = relationship("Camera", back_populates="applied_configs")
    optimization = relationship("Optimization", back_populates="applied_configs")

    # Constraints
    __table_args__ = (
        CheckConstraint("apply_method IN ('onvif', 'vms', 'vendor', 'manual')", name='valid_apply_method'),
        CheckConstraint("status IN ('pending', 'in_progress', 'success', 'failed', 'partial')", name='valid_status'),
        Index('idx_applied_camera', 'camera_id'),
        Index('idx_applied_status', 'status'),
    )


class Snapshot(Base):
    __tablename__ = 'snapshots'

    id = Column(Integer, primary_key=True, autoincrement=True)
    camera_id = Column(String(64), ForeignKey('cameras.id', ondelete='CASCADE'), nullable=False)
    file_path = Column(String(512), nullable=False)
    captured_at = Column(TIMESTAMP, default=datetime.utcnow, nullable=False)
    health_metrics = Column(JSONB)
    anomalies = Column(JSONB)

    # Relationships
    camera = relationship("Camera", back_populates="snapshots")

    # Indexes
    __table_args__ = (
        Index('idx_snapshots_camera', 'camera_id'),
        Index('idx_snapshots_captured', 'captured_at'),
    )


class HealthMetric(Base):
    __tablename__ = 'health_metrics'

    id = Column(Integer, primary_key=True, autoincrement=True)
    camera_id = Column(String(64), ForeignKey('cameras.id', ondelete='CASCADE'), nullable=False)
    metric_type = Column(String(32), nullable=False)
    value = Column(Float, nullable=False)
    status = Column(String(16))
    created_at = Column(TIMESTAMP, default=datetime.utcnow, nullable=False)

    # Relationships
    camera = relationship("Camera", back_populates="health_metrics")

    # Constraints
    __table_args__ = (
        CheckConstraint(
            "metric_type IN ('brightness', 'noise_level', 'blur_score', 'bitrate_mbps', 'fps_actual', 'frame_drops', 'latency_ms')",
            name='valid_metric_type'
        ),
        CheckConstraint("status IN ('ok', 'warning', 'critical')", name='valid_status'),
        Index('idx_health_camera_time', 'camera_id', 'created_at'),
        Index('idx_health_metric_type', 'metric_type', 'created_at'),
    )
```

---

## Migration Strategy

### Using Alembic

**Initialize Alembic:**
```bash
cd backend
alembic init alembic
```

**Configure `alembic.ini`:**
```ini
sqlalchemy.url = postgresql://user:password@localhost/camopt
```

**Create Initial Migration:**
```bash
alembic revision --autogenerate -m "Initial schema"
alembic upgrade head
```

**Migration Example:**
```python
# alembic/versions/001_initial_schema.py
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

def upgrade():
    op.create_table(
        'cameras',
        sa.Column('id', sa.String(64), primary_key=True),
        sa.Column('ip', sa.String(45), nullable=False),
        # ... other columns
    )

def downgrade():
    op.drop_table('cameras')
```

---

## Sample Queries

### 1. Get all cameras with recent optimizations

```sql
SELECT
    c.id,
    c.location,
    c.scene_type,
    c.purpose,
    o.confidence,
    o.created_at AS last_optimized
FROM cameras c
LEFT JOIN LATERAL (
    SELECT * FROM optimizations
    WHERE camera_id = c.id
    ORDER BY created_at DESC
    LIMIT 1
) o ON true
ORDER BY o.created_at DESC NULLS LAST;
```

### 2. Find cameras with failed apply jobs

```sql
SELECT
    c.id,
    c.ip,
    ac.apply_method,
    ac.error_message,
    ac.created_at
FROM cameras c
JOIN applied_configs ac ON c.id = ac.camera_id
WHERE ac.status = 'failed'
ORDER BY ac.created_at DESC;
```

### 3. Average confidence score by scene type

```sql
SELECT
    c.scene_type,
    COUNT(*) AS optimization_count,
    AVG(o.confidence) AS avg_confidence,
    COUNT(CASE WHEN o.ai_provider = 'claude-sonnet-4-5' THEN 1 END) AS ai_count,
    COUNT(CASE WHEN o.ai_provider = 'heuristic' THEN 1 END) AS heuristic_count
FROM optimizations o
JOIN cameras c ON o.camera_id = c.id
WHERE o.created_at >= NOW() - INTERVAL '30 days'
GROUP BY c.scene_type
ORDER BY avg_confidence DESC;
```

### 4. Cameras with health warnings in last 24 hours

```sql
SELECT DISTINCT
    c.id,
    c.location,
    s.anomalies
FROM cameras c
JOIN snapshots s ON c.id = s.camera_id
WHERE s.captured_at >= NOW() - INTERVAL '24 hours'
  AND jsonb_array_length(s.anomalies) > 0
ORDER BY c.id;
```

### 5. Time-series bitrate metrics for a camera

```sql
SELECT
    date_trunc('hour', created_at) AS hour,
    AVG(value) AS avg_bitrate,
    MAX(value) AS max_bitrate,
    MIN(value) AS min_bitrate
FROM health_metrics
WHERE camera_id = 'cam-lobby-01'
  AND metric_type = 'bitrate_mbps'
  AND created_at >= NOW() - INTERVAL '7 days'
GROUP BY hour
ORDER BY hour;
```

---

## Data Retention Policy

**Recommendations:**

| Table | Retention | Strategy |
|-------|-----------|----------|
| `cameras` | Permanent | Soft delete (add `deleted_at` column) |
| `optimizations` | 1 year | Archive old records to cold storage |
| `applied_configs` | 1 year | Keep for audit trail |
| `snapshots` | 30 days | Delete file + DB record after 30 days |
| `health_metrics` | 90 days | Aggregate to hourly/daily summaries |

**Cleanup Job (example):**
```sql
-- Delete old snapshots
DELETE FROM snapshots
WHERE captured_at < NOW() - INTERVAL '30 days';

-- Archive old health metrics
INSERT INTO health_metrics_archive
SELECT * FROM health_metrics
WHERE created_at < NOW() - INTERVAL '90 days';

DELETE FROM health_metrics
WHERE created_at < NOW() - INTERVAL '90 days';
```

---

## Backup Strategy

**Production:**
- **Automated daily backups** via Render/Railway/AWS RDS
- **Point-in-time recovery** enabled (7-35 days)
- **Weekly snapshot to S3** for disaster recovery

**Development:**
- SQLite file committed to repo (for sample data)
- Exclude production `.db` files via `.gitignore`

---

**Document Status:** Draft
**Last Updated:** 2025-12-05
**Maintainer:** Development Team
