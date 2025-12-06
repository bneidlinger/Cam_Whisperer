# CamOpt AI - System Architecture

**Version:** 0.2 (MVP Testing Phase)
**Date:** 2025-12-05
**Status:** Design Document

---

## Table of Contents

1. [High-Level Architecture](#high-level-architecture)
2. [Component Details](#component-details)
3. [Data Flow Diagrams](#data-flow-diagrams)
4. [Technology Stack](#technology-stack)
5. [Deployment Architecture](#deployment-architecture)
6. [Security Considerations](#security-considerations)

---

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         USER INTERFACE LAYER                         │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  Web UI (index.html)                                          │  │
│  │  - Camera input form                                          │  │
│  │  - Sample frame upload                                        │  │
│  │  - Results display                                            │  │
│  │  - Settings comparison view                                   │  │
│  └──────────────────────────────────────────────────────────────┘  │
└────────────────────────────────┬────────────────────────────────────┘
                                 │ HTTPS/REST API
                                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      APPLICATION LAYER (FastAPI)                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐             │
│  │   Discovery  │  │ Optimization │  │    Apply     │             │
│  │   Service    │  │   Service    │  │   Service    │             │
│  └──────────────┘  └──────────────┘  └──────────────┘             │
│                                                                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐             │
│  │  Monitoring  │  │    Image     │  │     Auth     │             │
│  │   Service    │  │  Processing  │  │   Service    │             │
│  └──────────────┘  └──────────────┘  └──────────────┘             │
└────────────┬───────────────────┬──────────────────────┬─────────────┘
             │                   │                      │
             ▼                   ▼                      ▼
┌─────────────────────┐ ┌─────────────────┐ ┌─────────────────────┐
│  Database Layer     │ │  AI Layer       │ │  Integration Layer  │
│  ┌───────────────┐  │ │  ┌───────────┐  │ │  ┌───────────────┐  │
│  │  PostgreSQL/  │  │ │  │  Claude   │  │ │  │    ONVIF      │  │
│  │   SQLite      │  │ │  │  Vision   │  │ │  │   Protocol    │  │
│  └───────────────┘  │ │  └───────────┘  │ │  └───────────────┘  │
│  ┌───────────────┐  │ │  ┌───────────┐  │ │  ┌───────────────┐  │
│  │ File Storage  │  │ │  │ Heuristic │  │ │  │  VMS SDKs     │  │
│  │  (Snapshots)  │  │ │  │  Fallback │  │ │  │ (Genetec etc) │  │
│  └───────────────┘  │ │  └───────────┘  │ │  └───────────────┘  │
└─────────────────────┘ └─────────────────┘ └─────────────────────┘
                                                      │
                                                      ▼
                                          ┌─────────────────────┐
                                          │  Physical Cameras   │
                                          │  - IP Cameras       │
                                          │  - NVRs             │
                                          │  - VMS Platforms    │
                                          └─────────────────────┘
```

---

## Component Details

### 1. Web UI Layer (Frontend)

**File:** `index.html`
**Technology:** Vanilla JavaScript, HTML5, CSS3
**Deployment:** GitHub Pages (static hosting)

**Responsibilities:**
- Collect camera deployment context from user
- Upload sample frame images
- Display AI-generated recommendations
- Show before/after settings comparison
- Export settings to JSON/text format

**API Communication:**
```javascript
// Example API call
const response = await fetch('https://api.camopt.ai/api/optimize', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(optimizeRequest)
});
```

---

### 2. Application Layer (Backend Services)

**Framework:** FastAPI (Python 3.10+)
**File:** `backend/main.py` + modular service files

#### 2.1 Discovery Service

**Purpose:** Identify cameras on network and map to VMS systems

**Key Functions:**
- ONVIF device discovery
- VMS API camera enumeration
- Camera capability querying
- Manual camera registration

**Endpoints:**
- `GET /api/discover?subnet=10.10.0.0/24`
- `POST /api/cameras` (manual registration)
- `GET /api/cameras/{camera_id}/capabilities`

#### 2.2 Optimization Service

**Purpose:** Generate optimal camera settings using AI

**Key Functions:**
- Parse optimization request
- Analyze sample frame with Claude Vision
- Apply business rules and constraints
- Generate human-readable explanations
- Fallback to heuristic engine on failure

**Core Algorithm:**
```python
async def optimize_camera(request: OptimizeRequest) -> OptimizeResponse:
    # 1. Validate input and constraints
    # 2. Prepare prompt for Claude Vision
    # 3. Send sample frame + context to Claude API
    # 4. Parse structured JSON response
    # 5. Validate recommendations against hardware capabilities
    # 6. Generate confidence score
    # 7. Return OptimizeResponse
```

**Endpoints:**
- `POST /api/optimize`

#### 2.3 Apply Service

**Purpose:** Push configuration to cameras/VMS

**Key Functions:**
- Route to appropriate integration adapter
- Translate settings to vendor/VMS format
- Execute configuration changes
- Verify applied settings
- Log changes for audit trail

**Endpoints:**
- `POST /api/apply`
- `GET /api/apply/status/{job_id}`

#### 2.4 Monitoring Service

**Purpose:** Continuous quality assessment

**Key Functions:**
- Periodic snapshot capture
- Compute health metrics (exposure, noise, blur)
- Detect configuration drift
- Generate re-optimization alerts

**Endpoints:**
- `POST /api/monitor/tick` (cron-triggered)
- `GET /api/cameras/{camera_id}/health`

#### 2.5 Image Processing Service

**Purpose:** Handle uploaded images and frame analysis

**Key Functions:**
- Accept multipart file uploads
- Resize/compress images
- Convert to base64 for Claude API
- Extract EXIF metadata
- Generate thumbnails

**Utilities:**
- `process_upload()` - Save and validate image
- `prepare_for_ai()` - Convert to Claude-compatible format
- `analyze_histogram()` - Basic quality metrics

---

### 3. AI Layer

#### 3.1 Claude Vision Integration

**Model:** `claude-sonnet-4-5-20250929`
**Provider:** Anthropic

**Input Format:**
```python
{
  "model": "claude-sonnet-4-5-20250929",
  "max_tokens": 4096,
  "messages": [
    {
      "role": "user",
      "content": [
        {
          "type": "image",
          "source": {
            "type": "base64",
            "media_type": "image/jpeg",
            "data": "<base64_encoded_image>"
          }
        },
        {
          "type": "text",
          "text": "<optimization_prompt_with_context>"
        }
      ]
    }
  ]
}
```

**Prompt Structure:**
```
You are an expert surveillance camera optimization engineer.

CAMERA CONTEXT:
- Scene Type: {sceneType}
- Purpose: {purpose}
- Current Settings: {currentSettings}
- Constraints: {bandwidthLimit}, {retentionDays}

SAMPLE FRAME: [image attached]

Analyze the sample frame and generate optimal camera settings.
Consider: lighting variance, motion levels, areas of interest.

Return settings in this JSON structure:
{
  "stream": {...},
  "exposure": {...},
  "lowLight": {...},
  "explanation": "...",
  "warnings": [...]
}
```

**Response Parsing:**
- Extract JSON from Claude response
- Validate schema against Pydantic models
- Compute confidence score based on constraint satisfaction
- Handle errors gracefully (fallback to heuristic)

#### 3.2 Heuristic Fallback Engine

**Purpose:** Backup when AI API is unavailable or fails

**Logic:** Port existing JavaScript heuristic engine from `index.html` to Python

**Triggers:**
- API timeout
- API error response
- Rate limit exceeded
- User preference override

---

### 4. Data Layer

#### 4.1 Database Schema

**Engine:** SQLite (dev) / PostgreSQL (production)
**ORM:** SQLAlchemy 2.0

**Core Tables:**

```sql
-- Camera inventory
CREATE TABLE cameras (
    id VARCHAR(64) PRIMARY KEY,
    ip_address VARCHAR(45) NOT NULL,
    vendor VARCHAR(64),
    model VARCHAR(128),
    vms_system VARCHAR(64),
    vms_camera_id VARCHAR(128),
    location TEXT,
    scene_type VARCHAR(32),
    purpose VARCHAR(32),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Optimization history
CREATE TABLE optimizations (
    id SERIAL PRIMARY KEY,
    camera_id VARCHAR(64) REFERENCES cameras(id),
    request_data JSONB NOT NULL,
    recommended_settings JSONB NOT NULL,
    confidence FLOAT,
    warnings JSONB,
    explanation TEXT,
    ai_provider VARCHAR(32),  -- 'claude', 'heuristic'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Applied configurations
CREATE TABLE applied_configs (
    id SERIAL PRIMARY KEY,
    camera_id VARCHAR(64) REFERENCES cameras(id),
    optimization_id INTEGER REFERENCES optimizations(id),
    settings JSONB NOT NULL,
    apply_method VARCHAR(32),  -- 'onvif', 'vms', 'manual'
    status VARCHAR(32),  -- 'pending', 'success', 'failed'
    applied_at TIMESTAMP,
    applied_by VARCHAR(128),
    error_message TEXT
);

-- Monitoring snapshots
CREATE TABLE snapshots (
    id SERIAL PRIMARY KEY,
    camera_id VARCHAR(64) REFERENCES cameras(id),
    file_path VARCHAR(512) NOT NULL,
    captured_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    health_metrics JSONB,
    anomalies JSONB
);
```

#### 4.2 File Storage

**Structure:**
```
uploads/
├── cameras/
│   ├── {camera_id}/
│   │   ├── samples/
│   │   │   └── {timestamp}.jpg
│   │   └── snapshots/
│   │       └── {timestamp}.jpg
└── temp/
    └── {uuid}.jpg  # Auto-cleanup after 24h
```

**Storage Options:**
- **Local Filesystem:** MVP phase
- **S3/Object Storage:** Production scaling

---

### 5. Integration Layer

#### 5.1 ONVIF Integration

**Library:** `onvif-zeep`

**Capabilities:**
- Device discovery via WS-Discovery
- GetCapabilities
- GetVideoEncoderConfigurations
- SetVideoEncoderConfiguration
- GetSnapshotUri

**Example:**
```python
from onvif import ONVIFCamera

camera = ONVIFCamera('10.10.0.104', 80, 'admin', 'password')
media = camera.create_media_service()
profiles = media.GetProfiles()

# Apply settings
encoder_config = profiles[0].VideoEncoderConfiguration
encoder_config.Resolution.Width = 1920
encoder_config.Resolution.Height = 1080
encoder_config.RateControl.BitrateLimit = 4000

media.SetVideoEncoderConfiguration({
    'Configuration': encoder_config,
    'ForcePersistence': True
})
```

#### 5.2 VMS SDK Integration (Future)

**Supported Platforms:**
- Genetec SDK (C# interop via pythonnet)
- Milestone MIP SDK
- Avigilon ACC API

**Abstraction Layer:**
```python
class VMSAdapter(ABC):
    @abstractmethod
    async def list_cameras(self) -> List[CameraRecord]:
        pass

    @abstractmethod
    async def apply_settings(self, camera_id: str, settings: dict):
        pass
```

---

## Data Flow Diagrams

### Optimization Flow

```
┌─────────┐
│  User   │
└────┬────┘
     │ 1. Fills form + uploads sample frame
     ▼
┌─────────────────┐
│  Web UI         │
│  (index.html)   │
└────┬────────────┘
     │ 2. POST /api/optimize
     │    {camera, context, sampleFrame}
     ▼
┌─────────────────────────────────────────┐
│  FastAPI Backend                        │
│  ┌───────────────────────────────────┐  │
│  │  Optimization Service             │  │
│  │  - Validate input                 │  │
│  │  - Process sample frame           │  │
│  └────┬──────────────────────────────┘  │
│       │ 3. Prepare prompt + image       │
│       ▼                                  │
│  ┌───────────────────────────────────┐  │
│  │  Claude Vision API Client         │  │
│  │  - Send vision request            │  │
│  │  - Parse response                 │  │
│  └────┬──────────────────────────────┘  │
└───────┼──────────────────────────────────┘
        │ 4. Claude API call
        ▼
┌─────────────────────────┐
│  Anthropic Claude API   │
│  - Analyze image        │
│  - Apply domain logic   │
│  - Generate JSON output │
└────┬────────────────────┘
     │ 5. Structured settings response
     ▼
┌─────────────────────────────────────────┐
│  FastAPI Backend                        │
│  ┌───────────────────────────────────┐  │
│  │  Optimization Service             │  │
│  │  - Validate settings              │  │
│  │  - Calculate confidence           │  │
│  │  - Store in database              │  │
│  └────┬──────────────────────────────┘  │
└───────┼──────────────────────────────────┘
        │ 6. OptimizeResponse JSON
        ▼
┌─────────────────┐
│  Web UI         │
│  - Display recs │
│  - Show warnings│
│  - Allow review │
└─────────────────┘
```

### Apply Configuration Flow

```
┌─────────┐
│  User   │ Reviews and approves settings
└────┬────┘
     │ 1. Clicks "Apply Settings"
     ▼
┌─────────────────┐
│  Web UI         │
└────┬────────────┘
     │ 2. POST /api/apply
     │    {camera, settings, applyVia: "onvif"}
     ▼
┌──────────────────────────────────────────┐
│  Apply Service                           │
│  - Create apply job                      │
│  - Route to adapter                      │
│  └────┬─────────────────────────────────┘│
└───────┼───────────────────────────────────┘
        │ 3. Call ONVIF adapter
        ▼
┌─────────────────────────────────────────┐
│  ONVIF Adapter                          │
│  - Connect to camera                    │
│  - Map settings to ONVIF structure      │
│  - SetVideoEncoderConfiguration         │
│  - Verify applied                       │
└────┬────────────────────────────────────┘
     │ 4. ONVIF SOAP calls
     ▼
┌─────────────────┐
│  IP Camera      │
│  - Apply config │
│  - Return status│
└────┬────────────┘
     │ 5. Success/error
     ▼
┌─────────────────────────────────────────┐
│  Apply Service                          │
│  - Update job status                    │
│  - Store applied_configs record         │
│  - Return result to client              │
└─────────────────────────────────────────┘
```

---

## Technology Stack

### Backend
| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| Framework | FastAPI | 0.109+ | REST API server |
| Language | Python | 3.10+ | Application logic |
| AI Provider | Anthropic Claude | 4.5 Sonnet | Vision + optimization |
| Database | PostgreSQL | 15+ | Persistent storage |
| ORM | SQLAlchemy | 2.0+ | Database abstraction |
| Camera Protocol | ONVIF | 2.x | Camera integration |
| Image Processing | Pillow | 10.2+ | Image manipulation |

### Frontend
| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| UI | HTML5/CSS3/JS | ES6+ | User interface |
| Deployment | GitHub Pages | - | Static hosting |

### Infrastructure
| Component | Technology | Purpose |
|-----------|-----------|---------|
| Backend Hosting | Render/Railway | API server |
| Database | Render PostgreSQL | Production DB |
| File Storage | Local/S3 | Image uploads |
| Monitoring | LogTail/Sentry | Error tracking |

---

## Deployment Architecture

### Development Environment

```
┌──────────────────────────────────────┐
│  Developer Machine                    │
│                                       │
│  ┌────────────┐    ┌──────────────┐  │
│  │ Frontend   │    │   Backend    │  │
│  │ (file://)  │───→│ localhost:   │  │
│  │            │    │     8000     │  │
│  └────────────┘    └──────┬───────┘  │
│                           │           │
│                    ┌──────▼───────┐   │
│                    │   SQLite     │   │
│                    │   camopt.db  │   │
│                    └──────────────┘   │
└──────────────────────────────────────┘
```

### Production Environment

```
┌─────────────────────────────────────────────────────────────┐
│  GitHub Pages (Frontend)                                     │
│  https://bneidlinger.github.io/cam_whisperer/               │
└────────────────────┬────────────────────────────────────────┘
                     │ HTTPS
                     ▼
┌─────────────────────────────────────────────────────────────┐
│  Render/Railway (Backend)                                    │
│  https://api.camopt.ai                                       │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  FastAPI App (Uvicorn)                                 │ │
│  └────┬───────────────────────────────────┬───────────────┘ │
│       │                                   │                  │
│  ┌────▼──────────┐              ┌────────▼────────┐         │
│  │  PostgreSQL   │              │  File Storage   │         │
│  │  (Managed)    │              │  (Volume)       │         │
│  └───────────────┘              └─────────────────┘         │
└─────────────────────────────────────────────────────────────┘
                     │ HTTPS
                     ▼
           ┌──────────────────────┐
           │  Anthropic API       │
           │  Claude Vision       │
           └──────────────────────┘
```

---

## Security Considerations

### Authentication & Authorization

**MVP Phase:**
- No user authentication (single-user prototype)
- API key protection via environment variables

**Future:**
- JWT-based authentication
- Role-based access control (admin, operator, viewer)
- API rate limiting

### Data Protection

**In Transit:**
- HTTPS/TLS for all API communication
- Encrypted Claude API calls

**At Rest:**
- Database encryption (PostgreSQL native)
- Secure API key storage (environment variables, never in code)

### Input Validation

- Pydantic model validation on all endpoints
- File upload size limits (10MB max)
- Image format validation
- SQL injection protection (ORM parameterization)

### Camera Access

- Credentials encrypted in database
- ONVIF authentication
- VMS SDK token management

---

## Performance Considerations

### Scalability Targets (MVP)

- **Concurrent optimizations:** 10 simultaneous
- **Response time:** < 15 seconds per optimization
- **Database:** Up to 1,000 cameras
- **Snapshot storage:** 100MB per camera per month

### Optimization Strategies

1. **Async Operations:** FastAPI async handlers for I/O
2. **Image Compression:** Reduce sample frame size before AI call
3. **Caching:** Cache camera capabilities (24h TTL)
4. **Database Indexes:** On camera_id, created_at fields
5. **Connection Pooling:** Database connection pool

---

## Error Handling

### AI Fallback Chain

```
Claude Vision API
    │
    ├─ Success → Return AI recommendations
    │
    ├─ Timeout → Retry once → Heuristic fallback
    │
    ├─ Rate Limit → Heuristic fallback
    │
    └─ Invalid Response → Heuristic fallback
```

### User-Facing Errors

- **400 Bad Request:** Invalid input data
- **500 Internal Error:** AI failure (with fallback applied)
- **503 Service Unavailable:** External service down
- **504 Timeout:** Camera unreachable

---

## Monitoring & Observability

### Logging Strategy

```python
{
  "timestamp": "2025-12-05T10:30:00Z",
  "level": "INFO",
  "service": "optimization",
  "camera_id": "cam-l1-104",
  "event": "ai_optimization_complete",
  "duration_ms": 8432,
  "ai_provider": "claude",
  "confidence": 0.87
}
```

### Key Metrics

- **API Response Times:** p50, p95, p99
- **AI Success Rate:** % successful vs fallback
- **Optimization Acceptance Rate:** % applied vs rejected
- **Camera Apply Success Rate:** % successful configuration pushes

---

**Document Status:** Draft
**Next Update:** After Phase 1 implementation
**Maintainer:** Development Team
