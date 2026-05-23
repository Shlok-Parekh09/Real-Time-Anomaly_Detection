# 🔍 AI-Powered Fraud Detection System

A free, web-based document fraud detection system powered by **Gemma AI** via **Puter.js**.

## 🚀 Quick Links

- **Main Project:** [fraud_detection_system/](./fraud_detection_system/)
- **Deploy Guide:** [DEPLOY_TO_VERCEL.md](./fraud_detection_system/DEPLOY_TO_VERCEL.md)
- **Documentation:** [fraud_detection_system/README.md](./fraud_detection_system/README.md)

## ✨ Features

- 🤖 AI-powered fraud detection (Gemma 2 27B)
- 📄 PDF and image support
- 🎯 Real-time analysis (5-15 seconds)
- 💰 100% free (no API keys)
- 🌐 Deploy to Vercel in 10 minutes
- 🖍️ Smart highlighting of suspicious areas

## 🚀 Get Started

```bash
cd fraud_detection_system

# Local development
cd backend && python main.py
cd frontend && npm run dev

# Or deploy to Vercel (see DEPLOY_TO_VERCEL.md)
```

## 📖 Documentation

All documentation is in the `fraud_detection_system/` directory:

- [README.md](./fraud_detection_system/README.md) - Main documentation
- [DEPLOY_TO_VERCEL.md](./fraud_detection_system/DEPLOY_TO_VERCEL.md) - Step-by-step deployment
- [WEB_DEPLOYMENT_GUIDE.md](./fraud_detection_system/WEB_DEPLOYMENT_GUIDE.md) - Architecture details
- [SOLUTION_SUMMARY.md](./fraud_detection_system/SOLUTION_SUMMARY.md) - Technical overview

## 🎯 What It Does

Analyzes documents for fraud indicators:
- **Metadata manipulation** - Editing software traces, date mismatches
- **Financial inconsistencies** - Balance errors, identical amounts
- **Pattern anomalies** - Weekend transactions, statistical outliers
- **Document integrity** - Missing fields, vague descriptions

## 💰 Cost

**$0/month** for unlimited users when deployed to Vercel!

- Frontend: Vercel (free)
- Backend: Vercel (free)
- AI: Puter.js (free, unlimited)

## 🏗️ Architecture

```
User Browser
    ↓
Frontend (React + Vite)
    ↓
Backend (FastAPI)
    ↓
Puter.js → Gemma AI (cloud)
    ↓
Results with highlighting
```

## 🛠️ Tech Stack

- **Frontend:** React, TypeScript, Vite, TailwindCSS, Puter.js
- **Backend:** FastAPI, PyMuPDF, Tesseract OCR, OpenCV
- **AI:** Gemma4 31B (via Puter.js) - Most accurate model
- **Hosting:** Vercel (serverless)

## 📊 Performance

- **Analysis:** 5-15 seconds per document
- **Accuracy:** Highest (Gemma4 31B model)
- **Scale:** Unlimited concurrent users
- **Cost:** $0/month

## 🔐 Security

- ✅ HTTPS (automatic)
- ✅ User authentication (Puter OAuth)
- ✅ No data storage
- ✅ Privacy-focused

## 🚀 Deploy Now

1. Push to GitHub
2. Import to Vercel
3. Deploy backend + frontend
4. Done!

See [DEPLOY_TO_VERCEL.md](./fraud_detection_system/DEPLOY_TO_VERCEL.md) for detailed instructions.

---

**Made with ❤️ for free, accessible fraud detection**

**No API keys. No subscriptions. Just AI.**
