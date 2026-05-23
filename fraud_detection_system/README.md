# 🔍 AI-Powered Fraud Detection System

A free, web-based document fraud detection system powered by **Gemma AI** via **Puter.js**.

## ✨ Features

- 🤖 **AI-Powered Analysis** - Gemma4 31B model via Puter.js (most accurate)
- 📄 **Multiple Formats** - PDF and image support
- 🎯 **Fraud Detection** - Metadata manipulation, financial inconsistencies, pattern anomalies
- 🖍️ **Smart Highlighting** - Color-coded suspicious areas (red/yellow/gray)
- 💰 **100% Free** - No API keys, no subscriptions
- ⚡ **Fast** - 5-15 second analysis
- 🌐 **Web-Ready** - Deploy to Vercel in 10 minutes

## 🚀 Quick Start

### Local Development

```bash
# Clone repository
git clone https://github.com/YOUR_USERNAME/fraud-detection.git
cd fraud-detection/fraud_detection_system

# Start backend
cd backend
pip install -r requirements.txt
python main.py

# Start frontend (new terminal)
cd frontend
npm install
npm run dev
```

Open http://localhost:5173

### Deploy to Vercel

See [DEPLOY_TO_VERCEL.md](./DEPLOY_TO_VERCEL.md) for step-by-step instructions.

**TL;DR:**
1. Push to GitHub
2. Import to Vercel (backend + frontend)
3. Set environment variables
4. Deploy!

**Cost:** $0/month for unlimited users

## 📖 How It Works

1. **User uploads document** (PDF or image)
2. **Backend extracts text** and metadata
3. **Puter.js AI analyzes** for fraud in browser
4. **Results displayed** with highlighted suspicious areas

```
User → Frontend → Backend (extract) → Puter.js (AI) → Results
```

## 🎯 Fraud Detection

The AI detects:

- **Metadata Manipulation** - Editing software traces, date mismatches
- **Financial Inconsistencies** - Balance errors, identical amounts, round numbers
- **Pattern Anomalies** - Weekend transactions, statistical outliers
- **Document Integrity** - Missing fields, vague descriptions, templates

## 🛠️ Tech Stack

### Frontend
- React + TypeScript
- Vite
- TailwindCSS
- Puter.js (AI)

### Backend
- FastAPI (Python)
- PyMuPDF (PDF processing)
- Tesseract OCR (image text extraction)
- OpenCV (highlighting)

### AI
- Gemma4 31B (via Puter.js)
- Browser-based inference
- Free & unlimited
- Most accurate model

## 📁 Project Structure

```
fraud_detection_system/
├── backend/
│   ├── main.py              # FastAPI server
│   ├── forensics.py         # Document analysis
│   ├── gemma4_integration.py # Local Ollama (optional)
│   ├── pdf_highlighter.py   # PDF highlighting
│   ├── image_highlighter.py # Image highlighting
│   ├── requirements.txt     # Python dependencies
│   └── vercel.json          # Vercel config
├── frontend/
│   ├── src/
│   │   ├── App.tsx          # Main app
│   │   ├── components/      # React components
│   │   └── utils/
│   │       └── puterAI.ts   # Puter.js integration
│   ├── index.html           # HTML + Puter.js script
│   ├── package.json         # Node dependencies
│   └── vercel.json          # Vercel config
└── README.md                # This file
```

## 🔧 Configuration

### Environment Variables

**Frontend** (`.env.production`):
```env
VITE_API_URL=https://your-backend.vercel.app
VITE_USE_PUTER_AI=true
```

**Backend:**
No environment variables needed!

## 📊 Performance

| Metric | Value |
|--------|-------|
| Analysis Speed | 5-15 seconds |
| Accuracy | Highest (Gemma4 31B) |
| Cost | $0/month |
| Scalability | Unlimited users |

## 🔐 Security

- ✅ HTTPS (automatic via Vercel)
- ✅ CORS configured
- ✅ User authentication (Puter OAuth)
- ✅ No data storage
- ✅ Privacy-focused

## 📚 Documentation

- [Deploy to Vercel](./DEPLOY_TO_VERCEL.md) - Step-by-step deployment
- [Web Deployment Guide](./WEB_DEPLOYMENT_GUIDE.md) - Architecture & options
- [Solution Summary](./SOLUTION_SUMMARY.md) - Technical overview
- [Gemma4 Setup](./GEMMA4_SETUP.md) - Local Ollama setup (optional)

## 🤝 Contributing

Contributions welcome! Areas for improvement:

- [ ] Additional document types
- [ ] Multi-language support
- [ ] Batch processing
- [ ] Export reports
- [ ] Custom fraud rules

## 📄 License

MIT License - See LICENSE file

## 🙏 Acknowledgments

- **Google** - Gemma AI model
- **Puter.js** - Free AI infrastructure
- **Vercel** - Hosting platform
- **PyMuPDF** - PDF processing
- **Tesseract** - OCR engine

## 📞 Support

- **Issues:** GitHub Issues
- **Docs:** See documentation files
- **Puter:** https://developer.puter.com

## 🎉 Demo

Try it live: [Your Vercel URL]

---

**Made with ❤️ for free, accessible fraud detection**

**No API keys. No subscriptions. Just AI.**
