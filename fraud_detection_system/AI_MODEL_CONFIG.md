# AI Model Configuration

## ⚠️ IMPORTANT: Best Output Priority

This fraud detection system prioritizes **ACCURACY over SPEED** in both web and local deployments.

## Web Deployment (Puter.js)

### Current Configuration

**Model:** `google/gemma-4-31b-it` (Gemma4 31B)
**Location:** `frontend/src/utils/puterAI.ts`
**Temperature:** `0.3`
**Priority:** Accuracy

### Why Gemma4 31B?

✅ **Most Accurate** - 31 billion parameters
✅ **Best for Fraud Detection** - Catches subtle patterns
✅ **Detailed Analysis** - Thorough evidence extraction
✅ **Reliable** - Consistent, deterministic results

## Local Deployment (Ollama)

### Current Configuration

**Model:** `gemma4:latest`
**Location:** `backend/gemma4_integration.py`
**Temperature:** `0.2` (even lower for more accuracy)
**Context:** `4096 tokens` (full analysis, not reduced)
**Timeout:** `600 seconds` (10 minutes - no rushing)

### Recommended Local Models

**Best (Highest Accuracy):**
```bash
ollama pull gemma4:latest  # Use largest available variant
```

**Alternative (Still Good):**
```bash
ollama pull gemma2:27b  # 27B parameters - very accurate
```

**NOT Recommended for Fraud Detection:**
```bash
# DO NOT use these - too small, less accurate
ollama pull gemma2:9b   # Only 9B parameters
ollama pull gemma2:2b   # Only 2B parameters
```

### Local Configuration Philosophy

1. **Accuracy First** - Use largest model your system can handle
2. **Full Context** - 4096 tokens (not reduced for "performance")
3. **Low Temperature** - 0.2 for deterministic, accurate results
4. **Long Timeout** - 10 minutes to avoid rushing analysis
5. **Thorough Prompts** - Detailed system instructions
6. **More Text** - 2000 chars context (not reduced)

### Performance vs Accuracy

| Setting | Fast (❌) | Accurate (✅) |
|---------|-----------|---------------|
| Model | gemma2:2b | gemma4:latest |
| Temperature | 0.7 | 0.2 |
| Context | 1024 | 4096 |
| Timeout | 60s | 600s |
| Text Sample | 500 chars | 2000 chars |
| Signals | 3-5 | 5-10 |

**We use the Accurate column for fraud detection.**

## Configuration Files

### Web (Puter.js)

**File:** `frontend/src/utils/puterAI.ts`

```typescript
const response = await window.puter.ai.chat(
  `${systemPrompt}\n\n${userPrompt}`,
  {
    model: 'google/gemma-4-31b-it', // Gemma4 31B - Most accurate
    temperature: 0.3, // Lower = more accurate
  }
);
```

### Local (Ollama)

**File:** `backend/gemma4_integration.py`

```python
payload = {
    "model": "gemma4:latest",  # Best available
    "messages": [...],
    "stream": False,
    "options": {
        "temperature": 0.2,  # Lower for accuracy
        "num_predict": 4096,  # Full context
        "top_p": 0.9,
        "top_k": 40,
    }
}
```

## System Prompts

Both web and local use detailed system prompts that emphasize:

- ✅ **Thoroughness** - "Take your time to analyze carefully"
- ✅ **Detail** - "Provide detailed explanations with specific evidence"
- ✅ **Accuracy** - "Be thorough and accurate - not a speed test"
- ✅ **Evidence** - "Each signal must have detailed, specific evidence"
- ✅ **Completeness** - "Include 5-10 fraud signals (be thorough, not rushed)"

## ⚠️ DO NOT Optimize for Speed

**DO NOT:**
- ❌ Reduce context length
- ❌ Use smaller models
- ❌ Increase temperature
- ❌ Reduce timeout
- ❌ Simplify prompts
- ❌ Request fewer signals

**Fraud detection requires accuracy. Speed is secondary.**

## Testing for Quality

When testing, verify:

✅ **Fraud signals are detailed** - Not generic
✅ **Evidence is specific** - Actual values, not placeholders
✅ **Scores are consistent** - Same document = same score
✅ **Highlighting is accurate** - Specific suspicious values
✅ **Explanations are thorough** - Not rushed or vague

If results seem rushed or incomplete:
1. Check model is correct (Gemma4 31B or gemma4:latest)
2. Check temperature is low (0.2-0.3)
3. Check timeout is sufficient (600s local)
4. Check context is full (4096 tokens, 2000 chars)

## Deployment Checklist

### Web Deployment
- [ ] Model: `google/gemma-4-31b-it` ✅
- [ ] Temperature: `0.3` ✅
- [ ] System prompt emphasizes accuracy ✅
- [ ] No fast model variants ✅

### Local Deployment
- [ ] Model: `gemma4:latest` (largest available) ✅
- [ ] Temperature: `0.2` ✅
- [ ] Context: `4096 tokens` ✅
- [ ] Timeout: `600 seconds` ✅
- [ ] Text sample: `2000 chars` ✅
- [ ] System prompt emphasizes thoroughness ✅

## Support

If you need faster results:
- ✅ Optimize backend text extraction
- ✅ Use CDN for frontend
- ✅ Enable caching
- ✅ Use GPU for local Ollama
- ❌ **DO NOT** change to smaller/faster AI model

## Summary

### Web (Puter.js)
✅ **Model:** Gemma4 31B (`google/gemma-4-31b-it`)
✅ **Temperature:** 0.3
✅ **Speed:** 5-15 seconds
✅ **Accuracy:** Highest

### Local (Ollama)
✅ **Model:** gemma4:latest (largest available)
✅ **Temperature:** 0.2
✅ **Timeout:** 10 minutes
✅ **Context:** Full (4096 tokens)
✅ **Accuracy:** Highest possible

---

**Fraud detection requires accuracy. Do not compromise for speed.**

**Best output = Thorough analysis + Detailed evidence + Accurate scoring**
