# Deploy to Railway.app - Step by Step Guide

## Why Railway?

- ✅ **Easy deployment** - Just connect GitHub and deploy
- ✅ **Free tier** - $5 free credit per month
- ✅ **Docker support** - Works with our Dockerfile
- ✅ **Persistent storage** - For model caching
- ✅ **Auto-deploys** - Updates automatically on git push

## Prerequisites

1. **GitHub Account** - Your code needs to be on GitHub
2. **Railway Account** - Sign up at https://railway.app (free)

## Step 1: Push Code to GitHub

```bash
# If not already a git repo
cd "d:\Users\Shlok Parekh\Downloads\Real-Time Anomaly Detection App"
git init
git add .
git commit -m "Initial commit with local LLM backend"

# Create a new repo on GitHub, then push
git remote add origin https://github.com/YOUR_USERNAME/fraud-detection.git
git branch -M main
git push -u origin main
```

## Step 2: Deploy to Railway

### Option A: Web Interface (Recommended)

1. **Go to**: https://railway.app
2. **Sign up/Login** with GitHub
3. **Click**: "New Project"
4. **Select**: "Deploy from GitHub repo"
5. **Choose**: Your fraud-detection repository
6. **Railway will auto-detect the Dockerfile!**

### Option B: Railway CLI

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login
railway login

# Navigate to backend
cd "d:\Users\Shlok Parekh\Downloads\Real-Time Anomaly Detection App\fraud_detection_system\backend"

# Initialize Railway project
railway init

# Link to your Railway project
railway link

# Deploy!
railway up
```

## Step 3: Configure Railway Service

After deployment starts:

1. **Go to your project** on Railway dashboard
2. **Click on the service** (should be auto-created)
3. **Go to "Settings"** tab

### Configure Settings:

#### Docker Settings:
- **Dockerfile Path**: `fraud_detection_system/backend/Dockerfile.local-llm`
- **Docker Build Context**: `.` (root of repo)

#### Environment Variables:
Add these in the "Variables" section:

```bash
TRANSFORMERS_CACHE=/app/.cache
PYTHONUNBUFFERED=1
LLM_MODEL=TinyLlama/TinyLlama-1.1B-Chat-v1.0
PORT=8000
```

#### Add Persistent Volume:
1. Click **"Add Volume"**
2. **Mount Path**: `/app/.cache`
3. **Size**: 10 GB (for model storage)

#### Health Check:
1. Go to **"Healthcheck"** section
2. **Path**: `/health`
3. **Timeout**: 300 seconds (5 minutes for first boot)

## Step 4: Monitor Deployment

Watch the build logs:

```bash
# In Railway CLI
railway logs
```

Or view in web dashboard → "Deployments" → Click on latest deployment

**First deployment takes ~10-15 minutes**:
- Installing dependencies: ~3-5 min
- Downloading model (2.2GB): ~5-10 min
- Starting server: ~30 sec

## Step 5: Get Your Backend URL

Once deployed:

```bash
# Railway CLI
railway domain
```

Or in web dashboard → "Settings" → "Public Networking" → Generate Domain

**Your URL will be**: `https://your-service.up.railway.app`

## Step 6: Test Your Backend

```bash
# Test health endpoint
curl https://your-service.up.railway.app/health

# Expected response:
{
  "status": "healthy",
  "forensics_engine": "active",
  "llm_status": "initialized",
  "llm_model": "TinyLlama/TinyLlama-1.1B-Chat-v1.0",
  "supported_formats": ["pdf", "png", "jpg", "jpeg"],
  "message": "All systems operational"
}
```

Test with a PDF:

```bash
curl -X POST https://your-service.up.railway.app/api/v1/analyze \
  -F "file=@test.pdf"
```

## Step 7: Update Frontend

Now update your frontend to use the Railway backend:

```bash
cd "d:\Users\Shlok Parekh\Downloads\Real-Time Anomaly Detection App\fraud_detection_system\frontend"

# Edit .env.production
echo VITE_API_URL=https://your-service.up.railway.app > .env.production
```

Update `UnderwriterDashboard.tsx`:

```typescript
// Change from extract-context to analyze
const response = await axios.post(
  `${API_BASE_URL}/api/v1/analyze`,
  formData,
  {
    timeout: 60000, // 60 seconds
    headers: { 'Content-Type': 'multipart/form-data' }
  }
);

// Use the response directly (no OpenRouter needed)
setResult(response.data);
```

## Step 8: Deploy Frontend

```bash
# Deploy frontend to Vercel
npx vercel --prod

# Or push to GitHub and it auto-deploys
git add .
git commit -m "Update backend URL"
git push
```

## Costs

### Railway Free Tier:
- **$5 credit/month** (free)
- **Usage**: ~$0.01-0.02 per hour of uptime
- **~250 hours/month free** (plenty for testing)

### Upgrade to Hobby ($5/month):
- **500 hours** included
- Better performance
- Priority support

## Troubleshooting

### Build Fails

**Error**: Out of memory during build

**Solution**: Reduce model size or use lazy loading:

```dockerfile
# In Dockerfile.local-llm, comment out model pre-download
# RUN python -c "from transformers..."
```

Model will download on first request instead.

### LLM Not Initializing

Check logs:

```bash
railway logs --filter "LLM"
```

**Error**: Model download fails

**Solution**: Increase timeout in Railway settings to 10 minutes

### Slow Performance

**Solution 1**: Upgrade to Hobby plan ($5/month) for better CPU

**Solution 2**: Use smaller model:

```bash
# In Railway variables
LLM_MODEL=distilgpt2  # Only 300MB, much faster
```

**Solution 3**: The system automatically falls back to rule-based analysis if LLM is too slow

### First Request Times Out

**Normal**: First request downloads model (~2-5 minutes)

**Solution**: Run a test request after deployment:

```bash
# After deploy completes, immediately test
curl -X POST https://your-service.up.railway.app/api/v1/analyze \
  -F "file=@test.pdf" \
  --max-time 600  # 10 minute timeout
```

This pre-loads the model. Subsequent requests will be fast (15-30 seconds).

## Performance Expectations

### TinyLlama (Default):
- **First request**: 2-5 minutes (downloads model)
- **Subsequent requests**: 15-30 seconds per PDF
- **Accuracy**: Good for fraud detection

### Free Tier:
- **CPU**: Shared
- **RAM**: 512 MB - 1 GB
- **Speed**: Adequate for testing

### Hobby Tier ($5/mo):
- **CPU**: Better allocation
- **RAM**: 2-4 GB
- **Speed**: 2x faster

## Auto-Scaling

Railway automatically:
- ✅ Restarts on crashes
- ✅ Scales horizontally if needed
- ✅ Keeps model cached between requests
- ✅ Auto-deploys on git push

## Monitoring

### View Metrics:
1. Go to Railway dashboard
2. Click your service
3. View **"Metrics"** tab

Shows:
- CPU usage
- Memory usage
- Network traffic
- Request count

### Set Up Alerts:
1. Go to **"Settings"** → **"Observability"**
2. Add webhook for alerts
3. Get notified on failures

## Complete Deployment Checklist

- [ ] Code pushed to GitHub
- [ ] Railway project created
- [ ] Dockerfile path configured
- [ ] Environment variables set
- [ ] Persistent volume added (10GB at /app/.cache)
- [ ] Health check configured (/health)
- [ ] Build completes successfully
- [ ] Health check passes (llm_status: initialized)
- [ ] Test PDF analysis works
- [ ] Frontend updated with Railway URL
- [ ] Frontend deployed
- [ ] End-to-end test successful

## Success!

Once complete, you have:

✅ **Fully offline fraud detection backend**
✅ **No external API dependencies**
✅ **Local LLM for AI analysis**
✅ **Deployed and accessible via HTTPS**
✅ **Auto-deploys on git push**
✅ **Persistent model caching**

## Alternative: Render.com

If Railway doesn't work, try Render:

1. Go to https://render.com
2. Create new **Web Service**
3. Connect GitHub repo
4. Select **Docker** environment
5. Set Dockerfile path: `fraud_detection_system/backend/Dockerfile.local-llm`
6. Add disk: 10GB at `/app/.cache`
7. Deploy!

## Support

If you encounter issues:

1. **Check Railway logs**: `railway logs`
2. **Test health endpoint**: `curl https://your-service.up.railway.app/health`
3. **Verify model downloaded**: Look for "Model initialized successfully" in logs
4. **Try rule-based fallback**: System automatically uses it if LLM fails

## Next Steps

After deployment:
1. Test with real PDFs from `dataset/real/` folder
2. Test with tampered PDFs from `dataset/tampered documents/` folder
3. Monitor performance and costs
4. Upgrade to Hobby tier if needed
5. Consider adding Sentry for error tracking

Your fraud detection system is now **completely offline** and **fully operational**! 🚀
