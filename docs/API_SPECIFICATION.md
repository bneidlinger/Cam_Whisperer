# CamOpt AI - API Specification

**Version:** 0.2.0
**Base URL (Production):** `https://api.camopt.ai`
**Base URL (Development):** `http://localhost:8000`

---

## Table of Contents

1. [Authentication](#authentication)
2. [Common Patterns](#common-patterns)
3. [Endpoints](#endpoints)
   - [Discovery & Registration](#discovery--registration)
   - [Optimization](#optimization)
   - [Configuration Application](#configuration-application)
   - [Monitoring](#monitoring)
4. [Data Models](#data-models)
5. [Error Handling](#error-handling)
6. [Rate Limiting](#rate-limiting)

---

## Authentication

**MVP Phase:** No authentication required
**Future:** JWT Bearer token authentication

```http
Authorization: Bearer <jwt_token>
```

---

## Common Patterns

### Request Headers

```http
Content-Type: application/json
Accept: application/json
```

### Response Format

All responses follow this structure:

**Success Response:**
```json
{
  "status": "success",
  "data": { ... },
  "timestamp": "2025-12-05T10:30:00Z"
}
```

**Error Response:**
```json
{
  "status": "error",
  "error": {
    "code": "INVALID_INPUT",
    "message": "Scene type must be one of: hallway, parking, entrance...",
    "details": { "field": "sceneType", "value": "invalid_type" }
  },
  "timestamp": "2025-12-05T10:30:00Z"
}
```

### Pagination

For list endpoints:

```http
GET /api/cameras?page=1&limit=50
```

Response:
```json
{
  "data": [...],
  "pagination": {
    "page": 1,
    "limit": 50,
    "total": 150,
    "totalPages": 3
  }
}
```

---

## Endpoints

### Discovery & Registration

#### **GET** `/api/discover`

Discover cameras on network via ONVIF or VMS enumeration.

**Query Parameters:**
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `subnet` | string | No | `"auto"` | Network subnet to scan (e.g., `"10.10.0.0/24"`) |
| `method` | string | No | `"onvif"` | Discovery method: `"onvif"`, `"vms"`, `"manual"` |
| `vmsSystem` | string | Conditional | - | VMS platform if method=vms: `"genetec"`, `"milestone"`, etc. |

**Example Request:**
```http
GET /api/discover?subnet=192.168.1.0/24&method=onvif
```

**Example Response:**
```json
{
  "status": "success",
  "data": {
    "cameras": [
      {
        "id": "onvif-192.168.1.104",
        "ip": "192.168.1.104",
        "vendor": "Hanwha",
        "model": "QNV-7080R",
        "macAddress": "00:09:18:ab:cd:ef",
        "firmwareVersion": "2.40",
        "discovered": "2025-12-05T10:30:00Z"
      },
      {
        "id": "onvif-192.168.1.105",
        "ip": "192.168.1.105",
        "vendor": "Axis",
        "model": "P3245-LVE",
        "macAddress": "00:40:8c:12:34:56",
        "firmwareVersion": "11.2.67",
        "discovered": "2025-12-05T10:30:05Z"
      }
    ],
    "scanDuration": 12.4,
    "scannedHosts": 254,
    "foundCameras": 2
  },
  "timestamp": "2025-12-05T10:30:17Z"
}
```

---

#### **POST** `/api/cameras`

Register a camera manually.

**Request Body:**
```json
{
  "id": "cam-lobby-01",
  "ip": "192.168.1.110",
  "vendor": "Hikvision",
  "model": "DS-2CD2385G1-I",
  "location": "Main Lobby",
  "sceneType": "entrance",
  "purpose": "overview",
  "vmsSystem": "milestone",
  "vmsCameraId": "milestone-uuid-123",
  "credentials": {
    "username": "admin",
    "password": "encrypted_password"
  }
}
```

**Validation Rules:**
- `id`: 1-64 chars, alphanumeric + dash/underscore
- `ip`: Valid IPv4 address
- `sceneType`: One of: `hallway`, `parking`, `entrance`, `perimeter`, `interior`, `cashwrap`, `warehouse`
- `purpose`: One of: `overview`, `facial`, `plates`, `behavior`, `counting`, `evidence`

**Example Response:**
```json
{
  "status": "success",
  "data": {
    "camera": {
      "id": "cam-lobby-01",
      "ip": "192.168.1.110",
      "vendor": "Hikvision",
      "model": "DS-2CD2385G1-I",
      "location": "Main Lobby",
      "sceneType": "entrance",
      "purpose": "overview",
      "createdAt": "2025-12-05T10:35:00Z"
    }
  },
  "timestamp": "2025-12-05T10:35:00Z"
}
```

---

#### **GET** `/api/cameras/{camera_id}`

Retrieve camera details.

**Example Response:**
```json
{
  "status": "success",
  "data": {
    "camera": {
      "id": "cam-lobby-01",
      "ip": "192.168.1.110",
      "vendor": "Hikvision",
      "model": "DS-2CD2385G1-I",
      "location": "Main Lobby",
      "sceneType": "entrance",
      "purpose": "overview",
      "vmsSystem": "milestone",
      "vmsCameraId": "milestone-uuid-123",
      "createdAt": "2025-12-05T10:35:00Z",
      "updatedAt": "2025-12-05T10:35:00Z",
      "lastOptimized": null,
      "lastSnapshot": null
    }
  },
  "timestamp": "2025-12-05T10:40:00Z"
}
```

---

#### **GET** `/api/cameras/{camera_id}/capabilities`

Query camera hardware capabilities.

**Example Response:**
```json
{
  "status": "success",
  "data": {
    "cameraId": "cam-lobby-01",
    "capabilities": {
      "maxResolution": "3840x2160",
      "supportedCodecs": ["H.264", "H.265", "MJPEG"],
      "maxFps": 30,
      "minFps": 1,
      "wdrLevels": ["Off", "Low", "Medium", "High"],
      "irModes": ["Off", "Auto", "On"],
      "hasLPRMode": false,
      "hasWDR": true,
      "hasIR": true,
      "hasPTZ": false,
      "audioSupport": true,
      "digitalZoomLevels": [1, 2, 4, 8]
    },
    "queriedAt": "2025-12-05T10:42:00Z"
  },
  "timestamp": "2025-12-05T10:42:00Z"
}
```

---

#### **GET** `/api/cameras/{camera_id}/current-settings`

Retrieve current camera configuration.

**Example Response:**
```json
{
  "status": "success",
  "data": {
    "cameraId": "cam-lobby-01",
    "currentSettings": {
      "stream": {
        "resolution": "1920x1080",
        "codec": "H.264",
        "fps": 30,
        "bitrateMbps": 6.0,
        "keyframeInterval": 60,
        "cbr": true
      },
      "exposure": {
        "shutter": "1/30",
        "iris": "Auto",
        "gainLimit": "48dB",
        "wdr": "Off",
        "backlightComp": "Off"
      },
      "lowLight": {
        "irMode": "Auto",
        "irIntensity": "Medium",
        "noiseReduction": "Medium",
        "slowShutter": "Off"
      },
      "image": {
        "sharpening": "Medium",
        "contrast": "50",
        "saturation": "50",
        "dewarp": "Off"
      }
    },
    "queriedAt": "2025-12-05T10:45:00Z"
  },
  "timestamp": "2025-12-05T10:45:00Z"
}
```

---

### Optimization

#### **POST** `/api/optimize`

Generate optimal camera settings using Claude Vision AI.

**Request Body:**
```json
{
  "camera": {
    "id": "cam-lobby-01",
    "ip": "192.168.1.110",
    "vendor": "Hikvision",
    "model": "DS-2CD2385G1-I",
    "vmsSystem": "milestone",
    "vmsCameraId": "milestone-uuid-123",
    "location": "Main Lobby",
    "sceneType": "entrance",
    "purpose": "facial"
  },
  "capabilities": {
    "maxResolution": "3840x2160",
    "supportedCodecs": ["H.264", "H.265"],
    "maxFps": 30,
    "wdrLevels": ["Off", "Low", "Medium", "High"],
    "irModes": ["Off", "Auto", "On"],
    "hasLPRMode": false
  },
  "currentSettings": {
    "stream": {
      "resolution": "1920x1080",
      "codec": "H.264",
      "fps": 30,
      "bitrateMbps": 6.0
    },
    "exposure": {
      "shutter": "1/30",
      "wdr": "Off"
    },
    "lowLight": {
      "irMode": "Auto"
    }
  },
  "context": {
    "bandwidthLimitMbps": 4.0,
    "targetRetentionDays": 30,
    "notes": "High foot traffic during business hours",
    "sampleFrame": "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQEAYABgAAD..."
  }
}
```

**Request Validation:**
- `sampleFrame`: Base64-encoded JPEG/PNG, max 10MB
- `bandwidthLimitMbps`: 0.5 - 50.0
- `targetRetentionDays`: 1 - 365

**Example Response:**
```json
{
  "status": "success",
  "data": {
    "recommendedSettings": {
      "stream": {
        "resolution": "1920x1080",
        "codec": "H.265",
        "fps": 20,
        "bitrateMbps": 3.5,
        "keyframeInterval": 40,
        "cbr": true
      },
      "exposure": {
        "shutter": "1/250",
        "iris": "Auto",
        "gainLimit": "36dB",
        "wdr": "High",
        "backlightComp": "Off"
      },
      "lowLight": {
        "irMode": "Auto",
        "irIntensity": "Medium",
        "noiseReduction": "Low",
        "slowShutter": "Off"
      },
      "image": {
        "sharpening": "High",
        "contrast": "55",
        "saturation": "50",
        "dewarp": "Off"
      }
    },
    "confidence": 0.87,
    "warnings": [
      "Bandwidth limit (4 Mbps) is tight for 1080p at 20 FPS. Consider H.265 to stay within budget.",
      "High WDR enabled due to glass doors visible in sample frame."
    ],
    "explanation": "This entrance camera shows challenging lighting with bright exterior daylight visible through glass doors and a darker interior lobby. To optimize for facial recognition:\n\n1. **WDR set to High** - Essential to handle the 8+ stop dynamic range between interior and exterior visible in the frame.\n\n2. **Shutter increased to 1/250** - Fast enough to freeze facial features of people entering at walking pace (~3 ft/sec). The 1/30 current setting would create motion blur.\n\n3. **FPS reduced to 20** - Sufficient for facial capture (15+ FPS recommended), allows bandwidth budget compliance.\n\n4. **H.265 codec** - Achieves ~40% bitrate savings vs H.264, critical for staying within 4 Mbps limit while maintaining quality.\n\n5. **Gain limit reduced to 36dB** - Prevents excessive noise in shadows while WDR handles the dynamic range.\n\nExpected bandwidth: 3.5 Mbps average. Storage: ~35 GB/day, ~1 TB/30 days retention.",
    "aiProvider": "claude-sonnet-4-5",
    "processingTime": 8.4,
    "generatedAt": "2025-12-05T10:50:00Z"
  },
  "timestamp": "2025-12-05T10:50:00Z"
}
```

**Performance:**
- **Expected Response Time:** 5-15 seconds
- **Timeout:** 30 seconds
- **Fallback:** If Claude API fails, returns heuristic-based recommendations with `aiProvider: "heuristic"`

---

### Configuration Application

#### **POST** `/api/apply`

Apply recommended settings to camera.

**Request Body:**
```json
{
  "camera": {
    "id": "cam-lobby-01",
    "ip": "192.168.1.110",
    "vendor": "Hikvision",
    "model": "DS-2CD2385G1-I",
    "vmsSystem": "milestone",
    "vmsCameraId": "milestone-uuid-123"
  },
  "settings": {
    "stream": {
      "resolution": "1920x1080",
      "codec": "H.265",
      "fps": 20,
      "bitrateMbps": 3.5
    },
    "exposure": {
      "shutter": "1/250",
      "wdr": "High"
    }
  },
  "applyVia": "onvif",
  "applyOptions": {
    "verifyAfterApply": true,
    "rebootIfNeeded": false,
    "credentials": {
      "username": "admin",
      "password": "encrypted_password"
    }
  }
}
```

**Parameters:**
- `applyVia`: `"onvif"`, `"vms"`, `"vendor"` (camera-specific HTTP API)
- `verifyAfterApply`: Query camera after config push to confirm settings applied

**Example Response:**
```json
{
  "status": "success",
  "data": {
    "jobId": "apply-job-a3b2c1d4",
    "status": "in_progress",
    "message": "Configuration apply initiated via ONVIF",
    "estimatedCompletion": "2025-12-05T10:52:00Z"
  },
  "timestamp": "2025-12-05T10:51:00Z"
}
```

---

#### **GET** `/api/apply/status/{job_id}`

Check status of configuration apply job.

**Example Response (In Progress):**
```json
{
  "status": "success",
  "data": {
    "jobId": "apply-job-a3b2c1d4",
    "status": "in_progress",
    "progress": 60,
    "currentStep": "Applying exposure settings",
    "steps": [
      {"name": "Connect to camera", "status": "completed"},
      {"name": "Apply stream settings", "status": "completed"},
      {"name": "Apply exposure settings", "status": "in_progress"},
      {"name": "Apply low-light settings", "status": "pending"},
      {"name": "Verify configuration", "status": "pending"}
    ]
  },
  "timestamp": "2025-12-05T10:51:30Z"
}
```

**Example Response (Completed):**
```json
{
  "status": "success",
  "data": {
    "jobId": "apply-job-a3b2c1d4",
    "status": "completed",
    "progress": 100,
    "result": {
      "appliedSettings": {
        "stream": {"resolution": "1920x1080", "codec": "H.265", "fps": 20},
        "exposure": {"shutter": "1/250", "wdr": "High"}
      },
      "verificationStatus": "success",
      "appliedAt": "2025-12-05T10:52:15Z"
    }
  },
  "timestamp": "2025-12-05T10:52:20Z"
}
```

**Example Response (Failed):**
```json
{
  "status": "success",
  "data": {
    "jobId": "apply-job-a3b2c1d4",
    "status": "failed",
    "progress": 40,
    "error": {
      "code": "ONVIF_AUTH_FAILED",
      "message": "Authentication failed. Check camera credentials.",
      "failedStep": "Connect to camera"
    }
  },
  "timestamp": "2025-12-05T10:51:45Z"
}
```

---

### Monitoring

#### **POST** `/api/monitor/tick`

Trigger monitoring cycle for all registered cameras (typically called by cron).

**Request Body:**
```json
{
  "cameraIds": ["cam-lobby-01", "cam-parking-02"],
  "captureSnapshot": true,
  "computeHealth": true
}
```

**Example Response:**
```json
{
  "status": "success",
  "data": {
    "monitoringJobId": "monitor-2025-12-05-10-55",
    "camerasQueued": 2,
    "estimatedCompletion": "2025-12-05T11:00:00Z"
  },
  "timestamp": "2025-12-05T10:55:00Z"
}
```

---

#### **GET** `/api/cameras/{camera_id}/health`

Get health metrics for a specific camera.

**Example Response:**
```json
{
  "status": "success",
  "data": {
    "cameraId": "cam-lobby-01",
    "healthStatus": "warning",
    "lastChecked": "2025-12-05T10:55:00Z",
    "metrics": {
      "exposure": {
        "status": "ok",
        "meanBrightness": 118,
        "histogram": {
          "shadows": 15,
          "midtones": 70,
          "highlights": 15
        }
      },
      "noise": {
        "status": "warning",
        "noiseLevel": 12.5,
        "threshold": 10.0,
        "message": "Higher than expected noise. Check IR intensity or gain settings."
      },
      "motionBlur": {
        "status": "ok",
        "blurScore": 3.2,
        "threshold": 5.0
      },
      "bandwidth": {
        "status": "ok",
        "currentMbps": 3.6,
        "expectedMbps": 3.5,
        "drift": 2.9
      }
    },
    "anomalies": [
      {
        "type": "high_noise",
        "severity": "medium",
        "message": "Noise level exceeds threshold by 25%",
        "recommendation": "Consider reducing gain limit or IR intensity"
      }
    ],
    "configurationDrift": false,
    "recommendReOptimization": true
  },
  "timestamp": "2025-12-05T10:56:00Z"
}
```

---

#### **GET** `/api/cameras/{camera_id}/snapshots`

Retrieve historical snapshots for a camera.

**Query Parameters:**
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `limit` | integer | No | 10 | Number of snapshots to return |
| `since` | ISO 8601 | No | - | Only snapshots after this timestamp |

**Example Response:**
```json
{
  "status": "success",
  "data": {
    "cameraId": "cam-lobby-01",
    "snapshots": [
      {
        "id": "snapshot-12345",
        "capturedAt": "2025-12-05T10:55:00Z",
        "url": "/api/snapshots/snapshot-12345.jpg",
        "healthMetrics": {
          "exposure": "ok",
          "noise": "warning",
          "motionBlur": "ok"
        }
      },
      {
        "id": "snapshot-12344",
        "capturedAt": "2025-12-05T10:40:00Z",
        "url": "/api/snapshots/snapshot-12344.jpg",
        "healthMetrics": {
          "exposure": "ok",
          "noise": "ok",
          "motionBlur": "ok"
        }
      }
    ]
  },
  "timestamp": "2025-12-05T10:56:00Z"
}
```

---

## Data Models

### CameraRecord

```typescript
{
  id: string;                    // Unique identifier
  ip: string;                    // IPv4 address
  vendor?: string;               // Camera manufacturer
  model?: string;                // Camera model number
  vmsSystem?: string;            // VMS platform name
  vmsCameraId?: string;          // VMS internal ID
  location?: string;             // Physical location description
  sceneType?: SceneType;         // Type of scene being monitored
  purpose?: Purpose;             // Primary operational purpose
  createdAt: ISO8601DateTime;
  updatedAt: ISO8601DateTime;
}
```

**SceneType Enum:**
`hallway`, `parking`, `entrance`, `perimeter`, `interior`, `cashwrap`, `warehouse`, `loading`, `stairwell`

**Purpose Enum:**
`overview`, `facial`, `plates`, `behavior`, `counting`, `evidence`

---

### CameraCapabilities

```typescript
{
  maxResolution: string;         // e.g., "3840x2160"
  supportedCodecs: string[];     // ["H.264", "H.265", "MJPEG"]
  maxFps: number;                // Maximum frame rate
  minFps?: number;               // Minimum frame rate
  wdrLevels: string[];           // ["Off", "Low", "Medium", "High"]
  irModes: string[];             // ["Off", "Auto", "On"]
  hasLPRMode?: boolean;          // License plate recognition mode
  hasWDR?: boolean;
  hasIR?: boolean;
  hasPTZ?: boolean;
}
```

---

### CameraCurrentSettings

```typescript
{
  stream: StreamSettings;
  exposure: ExposureSettings;
  lowLight: LowLightSettings;
  image?: ImageSettings;
}
```

**StreamSettings:**
```typescript
{
  resolution: string;            // "1920x1080"
  codec: string;                 // "H.264" | "H.265" | "MJPEG"
  fps: number;                   // 1-60
  bitrateMbps: number;           // 0.5-50.0
  keyframeInterval?: number;     // Frames between I-frames
  cbr?: boolean;                 // Constant bitrate mode
}
```

**ExposureSettings:**
```typescript
{
  shutter: string;               // "1/30" | "1/60" | "1/125" | "1/250" | "1/500"
  iris?: string;                 // "Auto" | "Manual"
  gainLimit?: string;            // "24dB" | "36dB" | "48dB"
  wdr?: string;                  // "Off" | "Low" | "Medium" | "High"
  backlightComp?: string;        // "Off" | "Low" | "Medium" | "High"
}
```

**LowLightSettings:**
```typescript
{
  irMode: string;                // "Off" | "Auto" | "On"
  irIntensity?: string;          // "Low" | "Medium" | "High"
  noiseReduction?: string;       // "Off" | "Low" | "Medium" | "High"
  slowShutter?: string;          // "Off" | "On"
}
```

**ImageSettings:**
```typescript
{
  sharpening?: string;           // "Low" | "Medium" | "High"
  contrast?: string;             // "0"-"100"
  saturation?: string;           // "0"-"100"
  dewarp?: string;               // "Off" | "On"
}
```

---

### OptimizeRequest

```typescript
{
  camera: CameraRecord;
  capabilities: CameraCapabilities;
  currentSettings: CameraCurrentSettings;
  context: OptimizeContext;
}
```

**OptimizeContext:**
```typescript
{
  bandwidthLimitMbps?: number;   // Max bitrate per camera
  targetRetentionDays?: number;  // Storage retention requirement
  notes?: string;                // Additional context
  sampleFrame?: string;          // Base64-encoded image data URL
}
```

---

### OptimizeResponse

```typescript
{
  recommendedSettings: CameraCurrentSettings;
  confidence: number;            // 0.0-1.0
  warnings: string[];            // Array of warning messages
  explanation: string;           // Human-readable justification
  aiProvider: string;            // "claude-sonnet-4-5" | "heuristic"
  processingTime: number;        // Seconds
  generatedAt: ISO8601DateTime;
}
```

---

## Error Handling

### Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `INVALID_INPUT` | 400 | Request validation failed |
| `CAMERA_NOT_FOUND` | 404 | Camera ID not found in database |
| `CAMERA_UNREACHABLE` | 503 | Cannot connect to camera IP |
| `ONVIF_AUTH_FAILED` | 401 | ONVIF authentication failed |
| `VMS_CONNECTION_FAILED` | 503 | Cannot connect to VMS API |
| `AI_SERVICE_UNAVAILABLE` | 503 | Claude API error (fallback applied) |
| `AI_TIMEOUT` | 504 | AI request exceeded timeout |
| `IMAGE_TOO_LARGE` | 413 | Sample frame exceeds 10MB |
| `UNSUPPORTED_FORMAT` | 415 | Image format not supported |
| `RATE_LIMIT_EXCEEDED` | 429 | Too many requests |
| `INTERNAL_ERROR` | 500 | Unexpected server error |

### Example Error Response

```json
{
  "status": "error",
  "error": {
    "code": "CAMERA_UNREACHABLE",
    "message": "Cannot connect to camera at 192.168.1.110. Timeout after 15 seconds.",
    "details": {
      "cameraId": "cam-lobby-01",
      "ip": "192.168.1.110",
      "attemptedMethod": "onvif",
      "timeout": 15
    },
    "suggestions": [
      "Verify camera is powered on and connected to network",
      "Check firewall rules allow access to camera IP",
      "Confirm camera IP address is correct"
    ]
  },
  "timestamp": "2025-12-05T11:00:00Z"
}
```

---

## Rate Limiting

**MVP Phase:** No rate limiting

**Future:**
- **Per IP:** 100 requests/hour
- **Per User:** 500 requests/hour
- **Optimization Endpoint:** 10 concurrent requests

**Rate Limit Headers:**
```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 87
X-RateLimit-Reset: 1638705600
```

---

## Webhooks (Future)

Allow clients to register webhooks for events:

**Events:**
- `optimization.completed`
- `apply.completed`
- `health.warning`
- `health.critical`

**Webhook Payload:**
```json
{
  "event": "health.warning",
  "cameraId": "cam-lobby-01",
  "data": {
    "healthStatus": "warning",
    "anomalies": [...]
  },
  "timestamp": "2025-12-05T11:05:00Z"
}
```

---

## Changelog

### v0.2.0 (2025-12-05)
- Initial API specification
- Core endpoints: discover, optimize, apply, monitor
- Claude Vision integration
- ONVIF support

---

**Document Status:** Living Document
**Maintained By:** Development Team
**Last Updated:** 2025-12-05
