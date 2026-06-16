# 🔧 Railway Deployment Fix

Your Railway deployment is **building successfully** but **failing to start**. Here's how to fix it:

---

## Quick Fix Steps

### 1. Check Railway Service Settings

Go to your Railway service → **Settings** tab:

#### **Root Directory** (IMPORTANT!)
- Set to: **Leave empty** or **`.`** (root)
- ❌ Don't set to `fraud_detection_system/backend`

#### **Dockerfile Path**
- Set to: **`Dockerfile`** (use the one in root)
- ❌ Don't use `fraud_detection_system/backend/Dockerfile.local-llm`

#### **Start Command**
- **Leave empty** (use Dockerfile CMD)
- OR set to: `uvicorn main_local_llm:app --host 0.0.0.0 --port $PORT`

### 2. Set Environment Variables

In **Variables** tab, add:

```bash
TRANSFORMERS_CACHE=/app/.cache
PYTHONUNBUFFERED=1
PORT=8000
LLM_MODEL=TinyLlama/TinyLlama-1.1B-Chat-v1.0
```

### 3. Add Persistent Volume

In **Settings** → **Volumes**:

- Click **"+ New Volume"**
- **Mount Path**: `/app/.cache`
- **Size**: 10 GB

### 4. Increase Timeout

In **Settings** → **Health Check**:

- **Path**: `/health`
- **Timeout**: `300` seconds (5 minutes)
- **Start period**: `600` seconds (10 minutes for first boot)

### 5. Redeploy

- Go to **"Deployments"** tab
- Click **"Redeploy"**
- Watch the logs

---

## Check the Logs

After redeploying, click on the latest deployment and watch for:

### ✅ Success Signs:
```
INFO:     Started server process
INFO:     Waiting for application startup.
[STARTUP] Local modules imported successfully
[STARTUP] Forensics engine initialized
[STARTUP] LLM will be initialized on first analysis request
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

### ❌ Error Signs:

**"ModuleNotFoundError":**
- Dependencies not installed
- Check requirements.txt was copied

**"Port already in use":**
- Railway not setting $PORT correctly
- Check environment variables

**"Cannot find main_local_llm":**
- Working directory issue
- Check Dockerfile COPY commands

---

## Alternative: Use Railway CLI

If web interface doesn't work, try CLI:

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login
railway login

# Link to your project
railway link

# Set environment variables
railway variables set TRANSFORMERS_CACHE=/app/.cache
railway variables set PYTHONUNBUFFERED=1
railway variables set LLM_MODEL=TinyLlama/TinyLlama-1.1B-Chat-v1.0

# Deploy
railway up

# View logs
railway logs
```

---

## Test After Deployment

Once logs show "Application startup complete":

```bash
# Test health (should work immediately)
curl https://your-app.up.railway.app/health

# Expected response:
{
  "status": "healthy",
  "forensics_engine": "active",
  "llm_status": "fallback_mode",  # Will change to "initialized" after first request
  "supported_formats": ["pdf", "png", "jpg", "jpeg"],
  "message": "All systems operational"
}
```

---

## Common Issues & Solutions

### Issue 1: "Application failed to respond"

**Cause:** App crashes on startup

**Solution:**
1. Check Railway logs for Python errors
2. Verify all environment variables are set
3. Ensure Dockerfile path is correct (use `Dockerfile` in root)

### Issue 2: Build succeeds but deploy fails

**Cause:** Wrong working directory

**Solution:**
1. Use the `Dockerfile` in root (already created)
2. Set Root Directory to empty or `.`
3. Don't use custom start commands

### Issue 3: "Out of memory"

**Cause:** Free tier RAM limit (512MB-1GB)

**Solutions:**
1. **Wait for first request** - Model downloads on demand, not at startup
2. **Upgrade to Hobby** ($5/month) for 2-4GB RAM
3. **Use smaller model** - Set `LLM_MODEL=distilgpt2` (only 300MB)

### Issue 4: Model download timeout

**Cause:** First request downloads 2GB model

**Solutions:**
1. **Increase health check timeout** to 600 seconds
2. **Use fallback mode** - System works with rule-based analysis while LLM loads
3. **Pre-download in Dockerfile** - Uncomment model download step

---

## Dockerfile Comparison

### ❌ OLD (Doesn't work on Railway):
```dockerfile
# This one is in fraud_detection_system/backend/
COPY requirements.txt .
COPY . .
```

### ✅ NEW (Works on Railway):
```dockerfile
# This one is in root directory
COPY fraud_detection_system/backend/requirements.txt .
COPY fraud_detection_system/backend/ .
```

**Use the new `Dockerfile` in root!**

---

## Quick Checklist

Before redeploying, verify:

- [ ] Using `Dockerfile` in root directory
- [ ] Root Directory setting is empty or `.`
- [ ] Environment variables are set (4 variables)
- [ ] Volume added (10GB at /app/.cache)
- [ ] Health check path is `/health`
- [ ] Health check timeout is 300+ seconds

---

## Still Not Working?

### Check These:

1. **View Logs:**
   - Railway dashboard → Deployment → Logs
   - Look for Python errors or import errors

2. **Test Locally:**
   ```bash
   cd fraud_detection_system/backend
   pip install -r requirements.txt
   python main_local_llm.py
   ```
   If it works locally, issue is Railway config.

3. **Simplify:**
   - Remove volume temporarily
   - Remove environment variables except PORT
   - See if basic startup works

4. **Get Railway Logs:**
   ```bash
   railway logs --deployment latest
   ```
   Share the error message for specific help.

---

## Alternative: Try Render.com

If Railway continues to fail, Render might be easier:

1. Go to https://render.com
2. Create **Web Service**
3. Connect GitHub
4. Select your repo
5. Settings:
   - **Environment**: Docker
   - **Dockerfile Path**: `Dockerfile`
   - **Region**: Oregon
   - **Plan**: Free
6. Add disk: 10GB at `/app/.cache`
7. Deploy!

Render's Docker support is sometimes more straightforward.

---

## Expected Behavior

### First Deployment:
- Build: ~5-10 minutes
- Startup: ~30 seconds
- First request: 2-5 minutes (downloads model)
- Status: "fallback_mode" until model loads

### After First Request:
- Startup: ~30 seconds
- Requests: 15-30 seconds
- Status: "initialized"

---

## Summary

**Main Issue:** Railway needs the Dockerfile in the root directory, not in `fraud_detection_system/backend/`

**Solution:** Use the new `Dockerfile` I created in the root

**Steps:**
1. Settings → Dockerfile Path = `Dockerfile`
2. Settings → Root Directory = empty
3. Set 4 environment variables
4. Add 10GB volume at `/app/.cache`
5. Redeploy

**Once fixed, the health endpoint should work!** 🎉
