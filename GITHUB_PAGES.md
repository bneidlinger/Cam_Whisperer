# GitHub Pages Deployment

**Live URL:** https://bneidlinger.github.io/cam_whisperer/

**Status:** ✅ Auto-deployed from `main` branch

---

## What's Deployed

### Current Version: v0.2.0-alpha

**Frontend:**
- Retro industrial 80's security UI
- Orange color scheme (#ff6b1a)
- CRT scan line effects
- Terminal green output
- Camera optimization form
- Sample frame upload

**Features:**
- ✅ Form validation
- ✅ UI/UX interactions
- ✅ Retro aesthetic
- ⚠️ Backend API calls (needs local backend)

---

## How It Works

### GitHub Pages Configuration

**Source:**
- Branch: `main`
- Folder: `/` (root)
- File: `index.html`

**Deployment:**
- Automatic on every push to `main`
- Takes 1-5 minutes to update
- No build process needed (static HTML)

**Files Deployed:**
```
/
├── index.html              (Retro UI)
├── index_retro.html        (Source backup)
├── index_old_backup.html   (Original v0.1)
├── .nojekyll               (Disable Jekyll processing)
└── README.md               (Shown on GitHub)
```

---

## User Experience

### What Works on GitHub Pages

✅ **UI Display:**
- Retro industrial design
- All visual effects (CRT, grid, glows)
- Form inputs and validation
- Responsive layout

✅ **Static Features:**
- Read documentation
- View UI design
- See form structure
- Understand workflow

### What Needs Local Backend

❌ **API Features:**
- Camera optimization (needs `/api/optimize`)
- Claude Vision analysis (needs API key)
- ONVIF discovery (needs `/api/discover`)
- Settings apply (needs `/api/apply`)

**Why:**
GitHub Pages only serves static files. The backend API runs separately and requires:
- Python environment
- Anthropic API key
- Local server (uvicorn)

---

## For Visitors

### Demo Mode (GitHub Pages)

**What you can do:**
1. See the retro industrial UI design
2. View the optimization form
3. Read documentation
4. Understand the workflow

**What you can't do:**
- Generate actual recommendations (no API)
- Upload images for analysis (no backend)
- Discover cameras (no ONVIF server)
- Apply settings (no camera connection)

### Full Functionality (Local)

**To run the complete system:**

1. **Clone Repository:**
   ```bash
   git clone https://github.com/bneidlinger/cam_whisperer.git
   cd cam_whisperer
   ```

2. **Start Backend:**
   ```bash
   cd backend
   python -m venv venv
   venv\Scripts\activate
   pip install -r requirements.txt
   cp .env.example .env
   # Add ANTHROPIC_API_KEY to .env
   uvicorn main:app --reload
   ```

3. **Start Frontend:**
   ```bash
   cd ..
   python -m http.server 3000
   ```

4. **Access:**
   - Frontend: http://localhost:3000
   - Backend: http://localhost:8000
   - API Docs: http://localhost:8000/docs

---

## Deployment Process

### Automatic Deployment

Every time you push to `main`:

1. **GitHub detects changes** to `main` branch
2. **GitHub Pages rebuilds** (copies files)
3. **Deployment completes** (1-5 minutes)
4. **Site updates** at https://bneidlinger.github.io/cam_whisperer/

**Trigger:**
```bash
git add .
git commit -m "Update frontend"
git push origin main
# Wait 1-5 minutes for deployment
```

### Manual Deployment

Not needed - GitHub Pages auto-deploys from `main`.

However, you can:
1. Check deployment status at https://github.com/bneidlinger/Cam_Whisperer/deployments
2. View build logs in Settings → Pages
3. Force rebuild by making a commit

---

## Current Deployment Status

### Latest Deployment

**Version:** v0.2.0-alpha
**Deployed:** 2025-12-06 (after push)
**Commit:** e66411a
**Message:** Release v0.2.0-alpha

**What Changed:**
- ✅ Retro industrial UI (index.html)
- ✅ Updated README
- ✅ New documentation files
- ✅ CHANGELOG.md
- ✅ RELEASE_NOTES

**Previous Version:**
- v0.1.0 - Static prototype with basic heuristic UI

---

## API Configuration

### Frontend API Detection

The frontend (`index.html`) has smart API detection:

```javascript
const API_BASE = (window.location.protocol === 'file:' ||
                  window.location.hostname === 'localhost' ||
                  window.location.hostname === '127.0.0.1' ||
                  window.location.hostname === '')
  ? 'http://localhost:8000'
  : 'https://your-backend-url.com';
```

**What this means:**
- On GitHub Pages: Tries to reach `https://your-backend-url.com` (not deployed)
- On localhost: Correctly points to `http://localhost:8000` ✓
- On file://: Correctly points to `http://localhost:8000` ✓

**Result:**
- GitHub Pages: Shows UI, API calls fail (expected)
- Local: Shows UI, API calls work ✓

---

## Future: Full Production Deployment

### Option 1: Backend on Render

**Deploy backend separately:**
1. Deploy FastAPI to Render/Railway
2. Get production URL (e.g., `https://camopt-api.onrender.com`)
3. Update `API_BASE` in `index.html`:
   ```javascript
   const API_BASE = window.location.hostname === 'localhost'
     ? 'http://localhost:8000'
     : 'https://camopt-api.onrender.com';
   ```
4. Push to GitHub (triggers GitHub Pages update)

**Result:**
- Frontend on GitHub Pages: ✅ Free
- Backend on Render: ✅ Free tier available
- Full functionality: ✅ Works for visitors

### Option 2: All-in-One Deployment

**Deploy everything to one service:**
1. Use Render/Railway/Fly.io
2. Serve static files from FastAPI
3. Single URL for everything
4. Keep GitHub Pages as demo/docs only

---

## Monitoring Deployment

### Check Deployment Status

**Via GitHub UI:**
1. Go to https://github.com/bneidlinger/Cam_Whisperer
2. Click "Deployments" (right sidebar)
3. See deployment history

**Via GitHub API:**
```bash
curl https://api.github.com/repos/bneidlinger/Cam_Whisperer/pages
```

**Via Browser:**
1. Visit https://bneidlinger.github.io/cam_whisperer/
2. Check if changes appear (may take 1-5 minutes)

### Deployment Logs

**Settings → Pages:**
https://github.com/bneidlinger/Cam_Whisperer/settings/pages

Shows:
- Deployment status
- Build logs
- Custom domain settings
- Source configuration

---

## Troubleshooting

### Changes Not Showing

**Problem:** Pushed to main but GitHub Pages still shows old version

**Solutions:**
1. **Wait 1-5 minutes** - Deployment takes time
2. **Hard refresh** - Ctrl+Shift+R (clears browser cache)
3. **Check commit** - Verify files pushed: `git log -1`
4. **Check deployment** - GitHub → Deployments
5. **Verify source** - Settings → Pages → Source = main branch

### 404 Not Found

**Problem:** Page shows 404 error

**Solutions:**
1. **Check index.html exists** in root of main branch
2. **Check .nojekyll exists** (disables Jekyll)
3. **Verify Pages enabled** in Settings → Pages
4. **Wait for deployment** to complete

### Old Version Cached

**Problem:** Browser showing old cached version

**Solutions:**
1. **Hard refresh:** Ctrl+Shift+R
2. **Clear cache:** Browser settings
3. **Incognito mode:** Test in private window
4. **Check deployed version:** View source, check commit hash

---

## Best Practices

### When Updating Frontend

1. **Test locally first:**
   ```bash
   python -m http.server 3000
   # Test at http://localhost:3000
   ```

2. **Commit with clear message:**
   ```bash
   git add index.html
   git commit -m "Update: [describe change]"
   ```

3. **Push to main:**
   ```bash
   git push origin main
   ```

4. **Wait for deployment:**
   - 1-5 minutes
   - Check deployments page

5. **Verify live:**
   - Visit GitHub Pages URL
   - Hard refresh (Ctrl+Shift+R)
   - Test in incognito

### Version Tags

**Tag stable versions:**
```bash
git tag -a v0.2.0-alpha -m "Stable release"
git push origin v0.2.0-alpha
```

**Benefits:**
- Easy rollback
- Clear version history
- Release tracking

---

## Summary

✅ **GitHub Pages Active:** https://bneidlinger.github.io/cam_whisperer/
✅ **Auto-Deploy:** Every push to `main`
✅ **Current Version:** v0.2.0-alpha (Retro UI)
✅ **Static Features:** All working
⚠️ **Dynamic Features:** Need local backend

**For full functionality, run locally with backend!**

---

**Last Updated:** 2025-12-06
**Deployment:** Automatic from `main` branch
**Status:** ✅ Active
