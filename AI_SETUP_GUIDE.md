# AI-Powered Analysis Setup Guide

## Overview

The Real-Time Anomaly Detection App uses **AI-powered analysis** to provide intelligent fraud detection. The backend has been enhanced to eliminate hardcoded responses and provide genuine, context-aware analysis using state-of-the-art language models.

## ⚠️ Important: API Key Required

**The application now REQUIRES an OpenRouter API key for AI analysis.** Without it, you'll only get basic forensic signals without intelligent interpretation.

## Why OpenRouter?

OpenRouter provides access to multiple AI models (Claude, GPT-4, Llama, etc.) through a single API, with:
- Pay-per-use pricing (no subscriptions)
- Access to the best models
- Automatic fallback if one model is unavailable
- Transparent pricing and usage tracking

## Setup Instructions

### Step 1: Get an OpenRouter API Key

1. Go to [https://openrouter.ai](https://openrouter.ai)
2. Sign up for a free account
3. Add credits to your account (starts at $5)
4. Go to [https://openrouter.ai/keys](https://openrouter.ai/keys)
5. Create a new API key
6. Copy the key (starts with `sk-or-v1-...`)

### Step 2: Configure the Backend

You have two options to provide the API key:

#### Option A: Environment Variable (Recommended)

**Windows (PowerShell):**
```powershell
$env:OPENROUTER_API_KEY="sk-or-v1-your-key-here"
```

**Windows (CMD):**
```cmd
set OPENROUTER_API_KEY=sk-or-v1-your-key-here
```

**Linux/Mac:**
```bash
export OPENROUTER_API_KEY="sk-or-v1-your-key-here"
```

**Permanent Setup (.env file):**
Create a `.env` file in the `fraud_detection_system/backend/` directory:
```env
OPENROUTER_API_KEY=sk-or-v1-your-key-here
OPENROUTER_MODEL=anthropic/claude-3.5-sonnet
```

Then install python-dotenv and load it in main.py:
```bash
pip install python-dotenv
```

#### Option B: Pass API Key in Request

When uploading a document through the frontend, you can provide the API key in the form:
- The frontend has a field for "Cerebras API Key" (this actually goes to OpenRouter)
- Enter your OpenRouter API key there
- It will be used for that specific analysis

### Step 3: Choose Your AI Model

The default model is `anthropic/claude-3.5-sonnet` (recommended for best quality).

You can change it by setting:
```bash
export OPENROUTER_MODEL="anthropic/claude-3.5-sonnet"
```

**Available Models:**
- `anthropic/claude-3.5-sonnet` - Best quality, most expensive (~$3/1M tokens)
- `anthropic/claude-3-haiku` - Fast and cheap (~$0.25/1M tokens)
- `openai/gpt-4o` - OpenAI's latest (~$2.50/1M tokens)
- `openai/gpt-4o-mini` - Cheaper GPT-4 variant (~$0.15/1M tokens)
- `meta-llama/llama-3.1-70b-instruct` - Open source, good quality (~$0.50/1M tokens)
- `google/gemini-pro-1.5` - Google's model (~$1.25/1M tokens)

See full list at: https://openrouter.ai/models

### Step 4: Start the Backend

```bash
cd fraud_detection_system/backend
uvicorn main:app --reload --port 8000
```

You should see:
```
INFO:     Uvicorn running on http://127.0.0.1:8000
INFO:     Application startup complete.
```

### Step 5: Test the Setup

Upload a document through the frontend. You should see:
- ✅ **With API Key**: Detailed AI analysis with specific findings
- ❌ **Without API Key**: Warning message asking for API key

## What the AI Analysis Provides

### 1. Comprehensive Document Assessment
The AI analyzes:
- All forensic signals detected
- X-ray recovery findings
- Document content patterns
- Risk score context
- Validation results

### 2. Intelligent Signal Descriptions
Each fraud signal gets a detailed explanation:
- What the signal means
- Why it matters for authenticity
- Legitimate scenarios that might cause it
- What to verify further

### 3. Actionable Recommendations
Based on the analysis, you get:
- Specific next steps for underwriters
- Risk-appropriate actions
- Additional verification needed

### 4. Honest Limitations
The AI clearly states:
- What it cannot determine
- Uncertainty in findings
- Need for additional verification

## Cost Estimation

**Typical Analysis Cost:**
- Document analysis: ~2,000-3,000 tokens
- Signal enrichment: ~1,500-2,500 tokens
- **Total per document: ~$0.01-0.03** (with Claude 3.5 Sonnet)

**Budget-Friendly Options:**
- Use `claude-3-haiku`: ~$0.001-0.002 per document
- Use `gpt-4o-mini`: ~$0.0005-0.001 per document

## Troubleshooting

### Error: "AI Analysis Unavailable - API Key Required"
**Solution:** Set the `OPENROUTER_API_KEY` environment variable or provide it in the request.

### Error: "HTTP 401" or "Invalid API Key"
**Solution:** 
- Verify your API key is correct
- Check it hasn't expired
- Ensure you have credits in your OpenRouter account

### Error: "HTTP 429" or "Rate Limit"
**Solution:**
- You've exceeded your rate limit
- Wait a few minutes and try again
- Consider upgrading your OpenRouter plan

### Error: "Network Error"
**Solution:**
- Check your internet connection
- Verify https://openrouter.ai is accessible
- Check firewall settings

### Analysis Takes Too Long
**Solution:**
- Switch to a faster model (claude-3-haiku, gpt-4o-mini)
- Check your internet speed
- Increase timeout in forensics.py if needed

## Advanced Configuration

### Custom Timeout
Edit `forensics.py` and change the timeout values:
```python
with urllib.request.urlopen(request, timeout=30) as response:  # Increase from 30
```

### Custom Temperature
Lower temperature = more focused, higher = more creative:
```python
"temperature": 0.3,  # Range: 0.0 to 1.0
```

### Max Tokens
Control response length:
```python
"max_tokens": 800,  # Increase for longer responses
```

## Security Best Practices

1. **Never commit API keys to git**
   - Add `.env` to `.gitignore`
   - Use environment variables

2. **Rotate keys regularly**
   - Generate new keys every few months
   - Revoke old keys

3. **Monitor usage**
   - Check OpenRouter dashboard regularly
   - Set up usage alerts

4. **Use separate keys for dev/prod**
   - Different keys for testing and production
   - Easier to track and manage

## Comparison: Before vs After

### Before (Hardcoded)
```json
{
  "summary": "OpenRouter API key is missing.",
  "likely_alteration": "AI analysis unavailable.",
  "recommended_action": "Please configure a valid OpenRouter API key...",
  "limitations": "Missing API key."
}
```

### After (AI-Powered)
```json
{
  "summary": "Document shows 3 high-severity fraud indicators including suspicious metadata editing signatures and perfectly rounded deposit amounts that are inconsistent with genuine payroll processing.",
  "likely_alteration": "The PDF metadata reveals use of Adobe Photoshop for document creation, which is highly unusual for bank-generated statements. Additionally, 4 of 5 salary deposits are rounded to exact thousands (£3,000.00), whereas legitimate payroll includes tax calculations resulting in irregular amounts. The X-ray analysis recovered a previous version showing different account holder details, indicating the document was modified after initial creation.",
  "recommended_action": "REJECT this application and request original bank statements directly from the financial institution. Contact the stated employer to verify employment and salary details. Consider flagging this applicant for potential fraud investigation.",
  "limitations": "This analysis is based on document-level forensics and cannot verify the authenticity of the issuing institution's digital signature or confirm employment details. Direct verification with the bank and employer is essential."
}
```

## Support

For issues with:
- **OpenRouter API**: https://openrouter.ai/docs
- **This Application**: Check GitHub issues or documentation
- **Model Selection**: https://openrouter.ai/models

## Summary

✅ **Setup Steps:**
1. Get OpenRouter API key
2. Set environment variable or pass in request
3. Choose AI model (optional)
4. Start backend
5. Upload documents and get intelligent analysis

✅ **Benefits:**
- No hardcoded responses
- Real AI-powered analysis
- Context-aware fraud detection
- Actionable recommendations
- Honest about limitations

✅ **Cost:**
- ~$0.01-0.03 per document (Claude 3.5 Sonnet)
- ~$0.001-0.002 per document (budget models)
- Pay only for what you use

---

**Ready to get started?** Get your API key at [https://openrouter.ai](https://openrouter.ai) and start analyzing documents with real AI intelligence!
