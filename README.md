# 🔍 Anobis: Banking Document Investigation Platform

An enterprise-grade document fraud and forensics platform designed for banking compliance, loan underwriting, and audit teams.

**Anobis** provides a professional **Banking Investigation Workspace** for high-fidelity forensic analysis of financial and identity documents.

## 🚀 Quick Links

- **Frontend (Astro + Tailwind v4):** [fraud_detection_system/frontend/](./fraud_detection_system/frontend/)
- **Backend (FastAPI):** [fraud_detection_system/backend/](./fraud_detection_system/backend/)
- **Engineering Guide:** [AGENTS.md](./AGENTS.md)
- **Design Guidelines:** [DESIGN.md](./DESIGN.md)

## ✨ Key Features

- **Banking Investigation Workspace**: Professional, high-density UI designed for enterprise auditors.
- **Multi-Document Analysis**: Compare bank statements, payslips, and KYC documents in a single case.
- **Cross-Document Consistency**: Automatically identify mismatches (e.g., income discrepancy) across different files.
- **Forensic PDF Inspection**: Deterministic byte-level analysis for metadata tampering and structural anomalies.
- **Trust Scoring**: Dynamic risk assessment based on forensic findings.
- **Audit Ready**: Comprehensive investigation logs and report export capabilities.

## 🚀 Get Started

### Local Development

1. **Frontend**:
   ```bash
   cd fraud_detection_system/frontend
   npm install
   npm run dev
   ```
   Available at `http://localhost:4321`

2. **Backend**:
   ```bash
   cd fraud_detection_system/backend
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   uvicorn main:app --reload
   ```

## 🏗️ Architecture

```
Banking Auditor
    ↓
Anobis Dashboard (Astro 6.4 + Tailwind v4)
    ↓
Forensic Engine (FastAPI + PyMuPDF)
    ↓
Metadata, Structural, & Consistency Analysis
    ↓
High-Density Investigation Report
```

## 🛠️ Tech Stack

- **Frontend:** Astro 6.4, TypeScript, Tailwind CSS v4, Lucide Astro.
- **Backend:** FastAPI, PyMuPDF (fitz), Tesseract OCR, OpenCV.
- **Design:** Enterprise Banking Investigation aesthetic (Anobis Branding).

## 🎯 What It Investigates

Anobis analyzes documents for critical fraud indicators:
- **Metadata Manipulation**: Software traces (e.g., Photoshop, PDF Editors), creation/modification date mismatches.
- **Cross-Doc Inconsistencies**: Income mismatch between payslips and statements, name spelling variations.
- **Structural Integrity**: PDF revision counts, incremental update anomalies, font inconsistencies.
- **Content Validation**: Anomalous transaction patterns, suspected PDF layering.

## 🔐 Security & Compliance

- **Privacy First**: Designed for local/private deployment within banking infrastructure.
- **Deterministic**: Findings are grounded in forensic evidence, not probabilistic AI hallucinations.
- **Audit Trail**: Every finding is backed by specific evidence and confidence assessments.

---

**Anobis | Professional Banking Forensics**
*Built for the Canara Bank Hackathon*
