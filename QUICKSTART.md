# CamOpt AI - Quick Start Guide

**Get from zero to working prototype in 15 minutes**

This guide will get you up and running with CamOpt AI for local development and testing.

---

## Prerequisites Checklist

Before starting, ensure you have:

- [ ] **Python 3.10+** installed ([Download](https://www.python.org/downloads/))
- [ ] **Git** installed ([Download](https://git-scm.com/downloads))
- [ ] **Anthropic API key** ([Sign up](https://console.anthropic.com/))
- [ ] **Text editor** (VS Code, Sublime, etc.)
- [ ] **Terminal** access (Command Prompt, PowerShell, Terminal, etc.)

---

## Step 1: Clone Repository

```bash
# Clone the repository
git clone https://github.com/bneidlinger/cam_whisperer.git

# Navigate to project directory
cd cam_whisperer
```

**Verify:**
```bash
# You should see these files:
ls
# Expected: index.html, README.md, backend/, whitepaper.html
```

---

## Step 2: Backend Setup

### 2.1 Create Virtual Environment

```bash
# Navigate to backend folder
cd backend

# Create virtual environment
python -m venv venv

# Activate it
# On Windows:
venv\Scripts\activate

# On macOS/Linux:
source venv/bin/activate

# You should see (venv) in your terminal prompt
```

### 2.2 Install Dependencies

```bash
# Install all required packages
pip install -r requirements.txt

# This will install:
# - FastAPI (web framework)
# - Anthropic SDK (Claude Vision)
# - SQLAlchemy (database)
# - ONVIF support
# - Image processing tools
# - And more...

# Wait 1-2 minutes for installation to complete
```

**Verify installation:**
```bash
pip list | grep fastapi
# Should show: fastapi 0.109.0 or similar
```

### 2.3 Configure Environment

```bash
# Copy environment template
cp .env.example .env

# On Windows (if cp doesn't work):
copy .env.example .env

# Edit .env file with your API key
# On Windows:
notepad .env

# On macOS:
open -e .env

# On Linux:
nano .env
```

**Add your Anthropic API key:**
```bash
# In .env file, replace this line:
ANTHROPIC_API_KEY=your_anthropic_api_key_here

# With your actual key:
ANTHROPIC_API_KEY=sk-ant-api03-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

**Get an API key:**
1. Go to https://console.anthropic.com/
2. Sign up or log in
3. Navigate to "API Keys"
4. Click "Create Key"
5. Copy the key (starts with `sk-ant-api03-`)

**Save and close** the `.env` file.

### 2.4 Start Backend Server

```bash
# Make sure you're in the backend/ directory
# and virtual environment is activated (you should see "(venv)")

# Start the server
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Expected output:
# INFO:     Uvicorn running on http://0.0.0.0:8000
# INFO:     Application startup complete
```

**Test it's working:**

Open your browser and visit:
- **API Docs:** http://localhost:8000/docs
- **Health Check:** http://localhost:8000/api/discover

You should see the FastAPI interactive documentation page at `/docs`.

**Leave this terminal running!** Open a new terminal for the next steps.

---

## Step 3: Frontend Setup

### 3.1 Update Frontend to Use Local Backend

Open `index.html` in your text editor.

Find this section (around line 838-840):

```javascript
// TODO: Replace with actual backend call
// const response = await fetch("/api/optimize", {
//   method: "POST",
```

**Replace the placeholder optimization logic** with actual API calls:

```javascript
// Update the buildOutputPayload function to call backend
async function generateRecommendations() {
  setStatus("loading", "Generating recommendations...");

  const input = buildInputFromForm();

  try {
    // Call backend API instead of heuristic
    const response = await fetch('http://localhost:8000/api/optimize', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(input)
    });

    if (!response.ok) {
      throw new Error(`API error: ${response.status}`);
    }

    const result = await response.json();
    displayResults(result);
    setStatus("success", "Recommendations generated!");

  } catch (error) {
    console.error('Optimization failed:', error);
    setStatus("error", "Failed to generate recommendations. Using fallback...");

    // Fallback to local heuristic
    const settings = basicHeuristicEngine(input);
    const output = buildOutputPayload(input, settings);
    displayResults(output);
  }
}
```

**Note:** For MVP, you can skip this step and use the existing heuristic engine. The backend integration can be done later.

### 3.2 Open Frontend

**Option A: Direct File Access**
```bash
# On Windows:
start index.html

# On macOS:
open index.html

# On Linux:
xdg-open index.html
```

**Option B: Simple HTTP Server (recommended for CORS)**
```bash
# In the project root directory (not backend/)
cd ..  # if you're still in backend/

# Python 3:
python -m http.server 3000

# Python 2:
python -m SimpleHTTPServer 3000

# Open browser to:
# http://localhost:3000
```

---

## Step 4: Test the Application

### Test Scenario 1: Basic Optimization (No Image)

1. Open the web UI (http://localhost:3000 or file://...)
2. Fill in the form:
   - **Site Name:** "Test Site"
   - **Camera ID:** "cam-test-01"
   - **Scene Type:** "Entrance"
   - **Purpose:** "Facial Recognition"
   - **Lighting:** "Variable (WDR needed)"
   - **Motion Level:** "Medium"
   - **Bandwidth Limit:** 4 Mbps
   - **Retention Days:** 30
3. Click **"Generate Recommendations"**
4. Review the JSON output on the right panel

**Expected Result:**
- Settings optimized for entrance + facial recognition
- WDR enabled (High)
- Shutter speed increased (1/250 or faster)
- H.265 codec recommended
- Bitrate within 4 Mbps limit

### Test Scenario 2: With Sample Image (Future)

**Once Claude Vision integration is complete:**

1. Take a screenshot of a camera view or use a test image
2. Upload via the "Sample Frame" field
3. Click "Generate Recommendations"
4. See AI analysis based on actual image content

---

## Step 5: Verify Backend API

### Test via Swagger UI

1. Open http://localhost:8000/docs
2. Click on **POST /api/optimize**
3. Click **"Try it out"**
4. Paste this sample request:

```json
{
  "camera": {
    "id": "test-cam-01",
    "ip": "192.168.1.100",
    "vendor": "Hanwha",
    "model": "QNV-7080R",
    "sceneType": "entrance",
    "purpose": "facial"
  },
  "capabilities": {
    "maxResolution": "1920x1080",
    "supportedCodecs": ["H.264", "H.265"],
    "maxFps": 30,
    "wdrLevels": ["Off", "Low", "Medium", "High"]
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
    "targetRetentionDays": 30
  }
}
```

5. Click **"Execute"**
6. Check the response (should return optimized settings)

**Expected Response:**
```json
{
  "recommendedSettings": {
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
  "confidence": 0.5,
  "warnings": [],
  "explanation": "Heuristic prototype: adjusted settings...",
  "generatedAt": "2025-12-05T..."
}
```

### Test via cURL (Command Line)

```bash
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

---

## Step 6: Next Steps

### Immediate Tasks (Week 1)

**Option A: Implement Claude Vision Integration**
1. Update `backend/main.py` optimize endpoint
2. Add Anthropic API client code
3. Create prompt template for camera optimization
4. Test with sample camera images
5. Handle errors and fallback to heuristic

**Option B: Implement Database Layer**
1. Create `backend/models.py` with SQLAlchemy models
2. Set up database connection in `backend/database.py`
3. Initialize SQLite database
4. Add CRUD operations for cameras
5. Store optimization history

**Option C: Implement ONVIF Discovery**
1. Create `backend/integrations/onvif_client.py`
2. Implement camera discovery function
3. Query camera capabilities via ONVIF
4. Test with physical IP camera

### Week 2-4 Tasks

See the [Development Plan](backend/README.md#development-roadmap) for full roadmap.

---

## Common Issues & Solutions

### Issue: "Command 'uvicorn' not found"

**Cause:** Virtual environment not activated

**Solution:**
```bash
cd backend
source venv/bin/activate  # or venv\Scripts\activate on Windows
uvicorn main:app --reload
```

---

### Issue: "ModuleNotFoundError: No module named 'anthropic'"

**Cause:** Dependencies not installed

**Solution:**
```bash
cd backend
source venv/bin/activate
pip install -r requirements.txt
```

---

### Issue: "anthropic.AuthenticationError: 401 Unauthorized"

**Cause:** Invalid or missing API key

**Solution:**
1. Check `.env` file exists in `backend/` folder
2. Verify `ANTHROPIC_API_KEY` is set correctly
3. Get a new key from https://console.anthropic.com/
4. Restart the uvicorn server

---

### Issue: Frontend shows CORS error

**Cause:** Browser blocking cross-origin requests

**Solution:**

**Option 1:** Use same-origin (recommended)
```bash
# Serve frontend via HTTP server instead of file://
python -m http.server 3000
# Open http://localhost:3000
```

**Option 2:** Update CORS settings in backend
```bash
# In .env:
CORS_ORIGINS=http://localhost:3000,file://
```

---

### Issue: Port 8000 already in use

**Cause:** Another process using port 8000

**Solution:**
```bash
# Use different port
uvicorn main:app --reload --port 8001

# Or find and kill process on port 8000
# Windows:
netstat -ano | findstr :8000
taskkill /PID <PID> /F

# macOS/Linux:
lsof -ti:8000 | xargs kill -9
```

---

## Project Status Checklist

Track your progress:

### Backend
- [x] Requirements.txt created
- [x] Environment config template
- [ ] Database models implemented
- [ ] Claude Vision integration
- [ ] ONVIF discovery
- [ ] Apply settings endpoint
- [ ] Health monitoring

### Frontend
- [x] Basic UI functional
- [x] Heuristic engine working
- [ ] Connected to backend API
- [ ] Sample frame upload
- [ ] Results comparison view
- [ ] Export functionality

### Deployment
- [ ] Backend deployed to Render/Railway
- [ ] Frontend updated with production API URL
- [ ] Environment variables configured
- [ ] Database migrations run
- [ ] HTTPS enabled

---

## Getting Help

**Documentation:**
- [Architecture Overview](backend/ARCHITECTURE.md)
- [API Reference](backend/API_SPECIFICATION.md)
- [Database Schema](backend/DATABASE_SCHEMA.md)
- [Backend README](backend/README.md)

**Support:**
- GitHub Issues: https://github.com/bneidlinger/cam_whisperer/issues
- Anthropic Docs: https://docs.anthropic.com/claude/
- FastAPI Docs: https://fastapi.tiangolo.com/

---

## Congratulations!

You now have a working CamOpt AI development environment!

**Next steps:**
1. Read the [Development Plan](backend/README.md#development-roadmap)
2. Pick a feature to implement (AI integration recommended)
3. Test with real camera images
4. Deploy to production when ready

---

**Document Version:** 1.0
**Last Updated:** 2025-12-05
**Tested On:** Windows 11, macOS 14, Ubuntu 22.04
