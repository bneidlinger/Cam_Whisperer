# CamOpt AI - Backend

Fast API backend for camera optimization with Claude Vision AI integration.

---

## Quick Start

### Prerequisites

- Python 3.10 or higher
- Anthropic API key ([get one here](https://console.anthropic.com/))
- PostgreSQL 15+ (production) or SQLite (development)

### Installation

```bash
# Navigate to backend directory
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env

# Edit .env and add your Anthropic API key
# ANTHROPIC_API_KEY=your_api_key_here
```

### Database Setup

**Development (SQLite):**
```bash
# Database will be created automatically on first run
# Located at: ./camopt.db
```

**Production (PostgreSQL):**
```bash
# Update DATABASE_URL in .env:
# DATABASE_URL=postgresql://user:password@host:port/dbname

# Run migrations
alembic upgrade head
```

### Run Server

```bash
# Development mode (with auto-reload)
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Production mode
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

**Server will start at:** `http://localhost:8000`
**API docs (Swagger UI):** `http://localhost:8000/docs`
**Alternative docs (ReDoc):** `http://localhost:8000/redoc`

---

## Project Structure

```
backend/
├── main.py                    # FastAPI application entry point
├── requirements.txt           # Python dependencies
├── .env.example              # Environment variables template
├── .gitignore                # Git ignore rules
│
├── models.py                 # SQLAlchemy database models (TODO)
├── database.py               # Database connection & session (TODO)
├── config.py                 # Configuration management (TODO)
│
├── services/                 # Business logic (TODO)
│   ├── discovery.py          # Camera discovery service
│   ├── optimization.py       # AI optimization service
│   ├── apply.py              # Configuration apply service
│   └── monitoring.py         # Health monitoring service
│
├── integrations/             # External API clients (TODO)
│   ├── claude_client.py      # Anthropic Claude API
│   ├── onvif_client.py       # ONVIF camera integration
│   └── vms/                  # VMS-specific adapters
│       ├── genetec.py
│       └── milestone.py
│
├── utils/                    # Utilities (TODO)
│   ├── image_processing.py   # Image manipulation
│   ├── encryption.py         # Credential encryption
│   └── validation.py         # Input validation
│
├── alembic/                  # Database migrations (TODO)
│   ├── versions/
│   └── env.py
│
├── tests/                    # Test suite (TODO)
│   ├── test_optimization.py
│   └── test_api.py
│
└── docs/                     # Documentation
    ├── ARCHITECTURE.md       # System architecture
    ├── API_SPECIFICATION.md  # API reference
    └── DATABASE_SCHEMA.md    # Database schema
```

---

## API Endpoints

### Current Status (v0.1)

| Endpoint | Method | Status | Description |
|----------|--------|--------|-------------|
| `/api/discover` | GET | ⚠️ Stub | Discover cameras on network |
| `/api/camera/{id}/snapshot` | POST | ⚠️ Stub | Capture camera snapshot |
| `/api/optimize` | POST | ⚠️ Partial | Generate optimal settings (heuristic only) |
| `/api/apply` | POST | ⚠️ Stub | Apply settings to camera |
| `/api/monitor/tick` | POST | ⚠️ Stub | Run monitoring cycle |

**Legend:**
- ✅ Implemented - ⚠️ Stub/Partial - ❌ Not started

### Planned Endpoints (v0.2)

- `POST /api/cameras` - Register camera manually
- `GET /api/cameras` - List all cameras
- `GET /api/cameras/{id}` - Get camera details
- `GET /api/cameras/{id}/capabilities` - Query capabilities
- `GET /api/cameras/{id}/current-settings` - Get current config
- `GET /api/cameras/{id}/health` - Get health metrics
- `GET /api/cameras/{id}/snapshots` - List snapshots
- `GET /api/apply/status/{job_id}` - Check apply job status

---

## Development Roadmap

### Phase 1: Core Infrastructure ⏳

- [ ] Set up database connection (SQLAlchemy)
- [ ] Create database models
- [ ] Implement Alembic migrations
- [ ] Add environment config management
- [ ] Set up logging

### Phase 2: AI Integration 🎯

- [x] Add Anthropic SDK to requirements
- [ ] Implement Claude Vision client
- [ ] Create optimization service
- [ ] Design AI prompt templates
- [ ] Add heuristic fallback logic
- [ ] Test with sample images

### Phase 3: Camera Integration

- [ ] Implement ONVIF discovery
- [ ] Add ONVIF configuration apply
- [ ] Create VMS adapter interface
- [ ] Test with physical camera

### Phase 4: API Implementation

- [ ] Implement all endpoints from API spec
- [ ] Add request validation
- [ ] Add error handling
- [ ] Write API tests

### Phase 5: Deployment

- [ ] Deploy to Render/Railway
- [ ] Set up production database
- [ ] Configure CORS for frontend
- [ ] Set up monitoring

---

## Testing

### Run Tests

```bash
# Install test dependencies (already in requirements.txt)
pip install pytest pytest-asyncio

# Run all tests
pytest

# Run with coverage
pytest --cov=. --cov-report=html

# Run specific test file
pytest tests/test_optimization.py
```

### Manual API Testing

**Using cURL:**
```bash
# Test optimization endpoint
curl -X POST http://localhost:8000/api/optimize \
  -H "Content-Type: application/json" \
  -d '{
    "camera": {
      "id": "test-cam-01",
      "ip": "192.168.1.100",
      "sceneType": "entrance",
      "purpose": "facial"
    },
    "capabilities": {
      "maxResolution": "1920x1080",
      "supportedCodecs": ["H.264", "H.265"],
      "maxFps": 30
    },
    "currentSettings": {
      "stream": {"resolution": "1920x1080", "codec": "H.264", "fps": 30},
      "exposure": {"shutter": "1/30", "wdr": "Off"},
      "lowLight": {"irMode": "Auto"}
    },
    "context": {
      "bandwidthLimitMbps": 4.0,
      "targetRetentionDays": 30
    }
  }'
```

**Using Swagger UI:**
1. Open http://localhost:8000/docs
2. Click "Try it out" on any endpoint
3. Fill in request body
4. Click "Execute"

---

## Environment Variables

See `.env.example` for all available configuration options.

**Required:**
- `ANTHROPIC_API_KEY` - Your Claude API key

**Optional (with defaults):**
- `APP_ENV` - Environment (development/staging/production)
- `APP_PORT` - Server port (default: 8000)
- `DATABASE_URL` - Database connection string
- `LOG_LEVEL` - Logging verbosity (INFO/DEBUG/WARNING)
- `CORS_ORIGINS` - Allowed CORS origins

---

## Common Issues

### Issue: `ModuleNotFoundError: No module named 'anthropic'`
**Solution:** Activate virtual environment and install dependencies
```bash
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
```

### Issue: `anthropic.AuthenticationError`
**Solution:** Add valid Anthropic API key to `.env`
```bash
# Get API key from: https://console.anthropic.com/
ANTHROPIC_API_KEY=sk-ant-api03-...
```

### Issue: `sqlalchemy.exc.OperationalError: unable to open database file`
**Solution:** Ensure database directory exists and is writable
```bash
mkdir -p ./data
chmod 755 ./data
```

### Issue: CORS errors in browser
**Solution:** Add frontend URL to CORS_ORIGINS in `.env`
```bash
CORS_ORIGINS=http://localhost:3000,https://bneidlinger.github.io
```

---

## Performance Tuning

### Production Deployment

**Uvicorn Workers:**
```bash
# Use multiple workers for better concurrency
uvicorn main:app --workers 4 --host 0.0.0.0 --port 8000
```

**Gunicorn (alternative):**
```bash
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

### Database Connection Pooling

```python
# In database.py
engine = create_engine(
    DATABASE_URL,
    pool_size=20,
    max_overflow=40,
    pool_pre_ping=True
)
```

### Redis Caching (future)

```python
# Cache camera capabilities for 24 hours
@cache(ttl=86400)
async def get_camera_capabilities(camera_id: str):
    # ...
```

---

## Contributing

### Code Style

```bash
# Format code with black
black .

# Lint with ruff
ruff check .

# Type checking (future)
mypy .
```

### Pre-commit Hooks

```bash
# Install pre-commit
pip install pre-commit

# Set up hooks
pre-commit install

# Hooks will run on git commit
```

---

## Security

### Credential Encryption

Camera credentials should be encrypted before storing in database:

```python
from utils.encryption import encrypt_credentials, decrypt_credentials

# Encrypt
encrypted = encrypt_credentials({"username": "admin", "password": "pass123"})

# Store in database
camera.credentials_encrypted = encrypted

# Decrypt when needed
credentials = decrypt_credentials(camera.credentials_encrypted)
```

### API Key Management

- **Never commit** `.env` file to git
- Use environment variables in production (Render/Railway/Docker)
- Rotate API keys periodically
- Use different keys for dev/staging/production

---

## Resources

**Documentation:**
- [FastAPI Docs](https://fastapi.tiangolo.com/)
- [Anthropic API Reference](https://docs.anthropic.com/claude/reference)
- [SQLAlchemy 2.0 Docs](https://docs.sqlalchemy.org/en/20/)
- [ONVIF Specification](https://www.onvif.org/specs/)

**Related Files:**
- [Architecture Diagram](./ARCHITECTURE.md)
- [API Specification](./API_SPECIFICATION.md)
- [Database Schema](./DATABASE_SCHEMA.md)

---

## License

[Specify license]

---

## Support

**Issues:** https://github.com/bneidlinger/cam_whisperer/issues
**Documentation:** See `docs/` directory
**Questions:** File an issue or contact maintainers

---

**Last Updated:** 2025-12-05
**Version:** 0.1.0 (Pre-alpha)
