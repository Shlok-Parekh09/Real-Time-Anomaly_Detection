# Deploy Backend with Local LLM

## Overview

This backend runs completely **offline** with:
- ✅ **Complete PDF/Image forensics** (local)
- ✅ **Local LLM** for AI analysis (no external APIs)
- ✅ **Rule-based fallback** if LLM unavailable
- ✅ **Works without internet** once deployed

## Models

### Default: TinyLlama (1.1B params)
- **Size**: ~2.2GB
- **Speed**: Fast on CPU
- **Accuracy**: Good for basic fraud detection
- **Best for**: Free tier deployments (Railway, Render)

### Alternative: Phi-3-mini (3.8B params)
- **Size**: ~7.6GB  
- **Speed**: Slower on CPU, fast on GPU
- **Accuracy**: Excellent
- **Best for**: Paid tier with GPU

## Deployment Options

### Option 1: Render.com (Recommended)

**Supports Docker with disk storage for models**

```bash
# From backend directory
cd fraud_detection_system/backend

# Deploy using Render Blueprint
# 1. Go to https://render.com
# 2. Create new Web Service
# 3. Select "Docker"
# 4. Point to this repository
# 5. Set Dockerfile path: ./Dockerfile.local-llm
# 6. Add disk storage: /app/.cache (10GB)
# 7. Deploy!
```

**Render Configuration:**
- **Region**: Oregon (cheaper)
- **Instance Type**: Starter ($7/month) or Free
- **Dockerfile**: `Dockerfile.local-llm`
- **Disk**: 10GB at `/app/.cache`
- **Health Check**: `/health`

### Option 2: Railway.app

**Supports Docker deployments**

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login
railway login

# Initialize
railway init

# Deploy
railway up --dockerfile Dockerfile.local-llm

# Set environment
railway variables set LLM_MODEL=TinyLlama/TinyLlama-1.1B-Chat-v1.0
```

### Option 3: Self-Hosted (VPS)

**Any VPS with Docker (DigitalOcean, Linode, AWS EC2)**

```bash
# Clone repository
git clone <your-repo>
cd fraud_detection_system/backend

# Build Docker image
docker build -f Dockerfile.local-llm -t fraud-detection-llm .

# Run container
docker run -d \
  -p 8000:8000 \
  -v model-cache:/app/.cache \
  --name fraud-detection \
  fraud-detection-llm

# Check logs
docker logs -f fraud-detection
```

### Option 4: Local Development

```bash
# Install dependencies
cd fraud_detection_system/backend
pip install -r requirements.txt

# Run server
python main_local_llm.py

# Or with uvicorn
uvicorn main_local_llm:app --host 0.0.0.0 --port 8000 --reload
```

## Environment Variables

```bash
# Model selection
LLM_MODEL=TinyLlama/TinyLlama-1.1B-Chat-v1.0  # Default (small, fast)
# LLM_MODEL=microsoft/Phi-3-mini-4k-instruct  # Better accuracy, larger

# Cache directory
TRANSFORMERS_CACHE=/app/.cache

# Python
PYTHONUNBUFFERED=1
```

## Testing

### Test Locally

```bash
# Start server
python main_local_llm.py

# Test health endpoint
curl http://localhost:8000/health

# Test with a PDF
curl -X POST http://localhost:8000/api/v1/analyze \
  -F "file=@test.pdf"
```

### Test Deployed

```bash
# Replace with your deployed URL
BACKEND_URL=https://your-app.onrender.com

# Health check
curl $BACKEND_URL/health

# Analyze document
curl -X POST $BACKEND_URL/api/v1/analyze \
  -F "file=@test.pdf"
```

## Frontend Configuration

Update frontend to use new backend:

```typescript
// fraud_detection_system/frontend/.env.production
VITE_API_URL=https://your-app.onrender.com
```

Or keep both options:

```typescript
// In UnderwriterDashboard.tsx
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// Try local LLM first, fallback to OpenRouter
try {
  const response = await axios.post(`${API_BASE_URL}/api/v1/analyze`, formData);
  // Use local LLM response
} catch (error) {
  // Fallback to OpenRouter
  const { analyzeDocumentWithAI } = await import('../utils/openrouterAI');
  // ...
}
```

## Performance

### TinyLlama (1.1B)
- **CPU (Free tier)**: ~30-60 seconds per analysis
- **CPU (Paid)**: ~15-30 seconds
- **GPU**: ~5-10 seconds

### Phi-3-mini (3.8B)
- **CPU (Free tier)**: ~2-5 minutes per analysis
- **CPU (Paid)**: ~1-2 minutes
- **GPU**: ~10-20 seconds

## Cost Comparison

| Platform | Plan | Cost | Performance |
|----------|------|------|-------------|
| **Render** | Free | $0 | Slow (CPU) |
| **Render** | Starter | $7/mo | Medium (CPU) |
| **Railway** | Free | $0 | Slow (CPU) |
| **Railway** | Starter | $5/mo | Medium (CPU) |
| **DigitalOcean** | Basic | $6/mo | Medium (CPU) |
| **Render** | Standard + GPU | $50/mo | Fast (GPU) |

## Troubleshooting

### Model Download Fails

```bash
# Pre-download model locally
python -c "from transformers import AutoTokenizer, AutoModelForCausalLM; \
AutoTokenizer.from_pretrained('TinyLlama/TinyLlama-1.1B-Chat-v1.0'); \
AutoModelForCausalLM.from_pretrained('TinyLlama/TinyLlama-1.1B-Chat-v1.0')"

# Then deploy
```

### Out of Memory

**Solution 1**: Use smaller model
```bash
LLM_MODEL=TinyLlama/TinyLlama-1.1B-Chat-v1.0
```

**Solution 2**: Upgrade instance
- Render: Starter → Standard
- Railway: Hobby → Pro

**Solution 3**: Use rule-based fallback
- The system automatically falls back to rule-based analysis if LLM fails

### Slow Performance

**Solution 1**: Upgrade to GPU instance
```bash
# Render: Select GPU instance type
# Cost: ~$50/month
```

**Solution 2**: Use quantized model
```python
# In local_llm.py, use 8-bit quantization
self.model = AutoModelForCausalLM.from_pretrained(
    self.model_name,
    load_in_8bit=True,  # Reduces memory, speeds up CPU
    device_map="auto",
)
```

## Architecture

```
User uploads file
    ↓
Backend receives file
    ↓
Forensics Engine analyzes
    ├─ PDF: Extract text, metadata, check dates, amounts
    ├─ Image: Check quality, compression, dimensions
    └─ Returns: Anomalies list + forensic score
    ↓
Local LLM analyzes
    ├─ Input: Forensic anomalies + document context
    ├─ Process: Generate fraud signals
    └─ Returns: Risk score, fraud signals, recommendation
    ↓
Response sent to frontend
    ├─ Risk score
    ├─ Trust score
    ├─ Fraud signals (3-7)
    ├─ AI explanation
    └─ Recommended action
```

## Security

- ✅ **No external APIs** - Everything runs locally
- ✅ **No data leaves server** - Complete privacy
- ✅ **Offline capable** - Works without internet
- ✅ **Open source** - Audit all code
- ✅ **No API keys required** - No secrets to manage

## Monitoring

### Check LLM Status

```bash
curl https://your-app.onrender.com/health
```

Response:
```json
{
  "status": "healthy",
  "forensics_engine": "active",
  "llm_status": "initialized",
  "llm_model": "TinyLlama/TinyLlama-1.1B-Chat-v1.0",
  "supported_formats": ["pdf", "png", "jpg", "jpeg"],
  "message": "All systems operational"
}
```

### Check Logs

**Render:**
```bash
# View logs in dashboard
https://dashboard.render.com
```

**Railway:**
```bash
railway logs
```

**Docker:**
```bash
docker logs -f fraud-detection
```

## Success Criteria

- ✅ `/health` returns `llm_status: "initialized"`
- ✅ PDF upload returns fraud analysis
- ✅ Image upload returns fraud analysis
- ✅ Analysis takes < 60 seconds
- ✅ Response includes 3-7 fraud signals
- ✅ Works without internet connection

## Next Steps

1. **Deploy backend** to Render/Railway
2. **Test endpoints** with sample files
3. **Update frontend** with backend URL
4. **Deploy frontend** to Vercel
5. **Test end-to-end** workflow

## Support

For issues:
1. Check `/health` endpoint status
2. Review logs for errors
3. Verify model downloaded successfully
4. Try rule-based fallback (automatically happens if LLM fails)
