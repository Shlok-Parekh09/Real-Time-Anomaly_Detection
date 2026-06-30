# Anobis

Enterprise Document Fraud and Forensic Investigation Platform

Anobis is a fully offline, AI-assisted investigation workspace for banking compliance, loan underwriting, KYC, tenant screening, insurance review, and audit teams. It analyzes groups of identity, financial, and supporting documents as a single investigation instead of treating each upload as an isolated classifier input.

The platform combines OCR, document classification, entity extraction, metadata forensics, cross-document validation, deterministic trust scoring, dataset similarity, KNN-style case comparison, PDF reporting, and local LLM reasoning through Ollama using `gemma4:e4b`.

---

## 1. Hackathon Judge Summary

### Problem

Banks and financial institutions often receive document bundles that look valid in isolation but contradict each other across names, account details, salary values, addresses, dates, or file metadata. Manual review is slow, inconsistent, and hard to audit. Cloud AI is also difficult to use in sensitive compliance environments because documents may contain private financial and identity data.

### Solution

Anobis provides an offline forensic workspace where an investigator can:

1. Create a case.
2. Upload multiple documents.
3. Run an automated forensic pipeline.
4. Review the Trust Score and forensic findings.
5. Inspect OCR text, extracted entities, metadata, findings, and source documents.
6. Read a local Gemma-generated bilingual explanation.
7. Export a forensic PDF report.
8. Promote approved cases into a trusted reference dataset.

### What Makes It Different

- **Investigation-centric workflow**: Anobis correlates an entire document set, not just one file.
- **Offline by design**: OCR, scoring, KNN comparison, and AI reasoning run locally.
- **Deterministic trust scoring**: Scores are explainable 0-100 values, not opaque model probabilities.
- **Grounded AI summaries**: Gemma receives deterministic findings and is instructed not to invent facts.
- **Dataset intelligence**: Cases are compared against known genuine/fraud templates and approved baselines.
- **Audit-ready output**: Every major action is logged and exportable as a PDF report.

---

## 2. Demo in One Command

After installing dependencies once, start the full stack from the repository root:

```bash
make start
```

This runs:

- Ollama, if it is not already running
- FastAPI backend at `http://127.0.0.1:8001`
- Astro frontend at `http://127.0.0.1:4321`

Open:

```text
http://127.0.0.1:4321/
```

Direct launcher:

```bash
./scripts/start-anobis.sh
```

Optional port overrides:

```bash
BACKEND_PORT=8002 FRONTEND_PORT=4322 make start
```

Logs are written to:

```text
.anobis-logs/
```

Stop the stack with `Ctrl+C`.

---

## 3. Demo Walkthrough for Judges

Use this flow during judging:

1. Open `http://127.0.0.1:4321/`.
2. Go to **New Investigation**.
3. Select a context such as `Loan Approval` or `Mortgage Underwriting`.
4. Upload sample files from:
   ```text
   dataset/testing/clean_cases/
   dataset/testing/fraud_cases/
   dataset/testing/ocr_cases/
   ```
5. Click **Start Forensic Analysis**.
6. Watch the progress stages:
   - Extraction
   - OCR
   - Classification
   - Context validation
   - Cross-document validation
   - Trust scoring
   - Local AI summary generation
7. Review the result page:
   - Trust score
   - Recommendation
   - AI executive summary in English and Hindi
   - Dataset similarity/KNN matches
   - Findings list
   - Evidence/document viewer
   - Raw extracted text and metadata
8. Export the PDF report.
9. Click **Approve Reference** to add the completed investigation to the local trusted baseline repository.

Recommended sample pair:

```text
dataset/testing/clean_cases/461790262-335063360-Hdfc-Bank-Statement-pdf.pdf
dataset/testing/ocr_cases/BankStatementChequing.png
```

---

## 4. Verified Demo Status

The repository was end-to-end verified with:

- Backend startup
- SQLite database access
- Tesseract OCR
- Dataset loading
- KNN/dataset similarity
- Ollama server
- `gemma4:e4b` installation and warmup
- Investigation creation
- Multi-document upload
- Background analysis polling
- Results retrieval
- PDF report export
- Document viewer file serving
- Trusted reference approval
- Frontend build and route serving

Final verified health response should look like:

```json
{
  "backend": "healthy",
  "database": "healthy",
  "ocr": "ready",
  "dataset": "loaded",
  "knn": "ready",
  "ollama": "connected",
  "model": "gemma4:e4b",
  "ai": "ready",
  "warm": true
}
```

Quick health check:

```bash
curl http://127.0.0.1:8001/api/v1/system/health
```

---

## 5. Platform Capabilities

### Investigation Lifecycle

- Create a case with an investigation context.
- Upload multiple PDFs/images.
- Run asynchronous analysis.
- Poll status in real time.
- Review results in an investigation workbench.
- Export report.
- Promote high-trust cases into the reference dataset.

### OCR and Extraction

- Reads native PDF text with PyMuPDF.
- Converts image uploads into searchable PDFs.
- Runs Tesseract OCR on scanned/image-based documents.
- Extracts raw text, document metadata, OCR quality indicators, coordinates, and entities.

### Document Intelligence

- Classifies common banking and identity documents.
- Extracts names, account numbers, salaries, employers, addresses, IDs, and financial values where available.
- Preserves extracted text and metadata for investigator inspection.

### Forensics

- Checks PDF metadata and structure.
- Detects suspicious creator/producer signatures.
- Flags design/editor tools such as Canva, Photoshop, Illustrator, and Acrobat.
- Supports image/OCR quality indicators and low-quality extraction evidence paths.

### Cross-Document Validation

- Compares entities across the document bundle.
- Uses fuzzy matching for identity/name consistency.
- Validates financial and contextual relationships when enough data is present.
- Logs contradictions as findings.

### Trust Scoring

Anobis exposes one judge-facing score:

- **Trust Score**: A normalized 0-100 integrity score calculated from deterministic forensic findings, severity deductions, document completeness, and cross-document consistency.

Internal extraction-quality gates still influence manual-review recommendations, but they are not shown as a separate public score.

### Dataset Intelligence and KNN

The similarity engine compares each completed case against:

- Precompiled genuine reference cases
- Precompiled fraud/tampered examples
- Past completed investigations in the database
- Manually approved trusted baselines in `trusted_repository/data.json`

The result page shows:

- Best similarity score
- Closest genuine matches
- Closest fraud matches
- Explanation of similarity/correlation

### Local AI Reasoning

Anobis uses Ollama with:

```text
gemma4:e4b
```

The AI layer receives deterministic findings, scores, metadata, similarity output, and timeline events. It returns a structured JSON report with:

- English executive summary
- Hindi executive summary
- Risk narrative
- Evidence analysis
- Extraction-quality reasoning
- Missing evidence
- Manual review questions
- Recommended next steps
- Final recommendation

The response includes provenance fields:

```json
{
  "ai_status": "ready",
  "ai_mode": "ollama",
  "ai_model": "gemma4:e4b"
}
```

If the model is unavailable, Anobis falls back to a deterministic offline summary and marks the response offline. For a judged demo, verify that `ai_status` is `ready`.

---

## 6. Architecture

```text
User Browser
    |
    v
Astro + Tailwind Frontend
    |
    v
FastAPI REST API
    |
    v
Investigation Manager
    |
    +--> Intake and Document Storage
    +--> OCR and Extraction
    +--> Classification
    +--> Entity Extraction
    +--> Digital/Metadata Forensics
    +--> Context Validation
    +--> Cross-Document Validation
    +--> Trust Scoring and Quality Gates
    +--> Dataset Similarity / KNN
    +--> Local Gemma AI Summary
    +--> PDF Report Generation
    |
    v
SQLite + Local Uploads + Trusted Repository
```

### Backend Stack

- FastAPI
- SQLAlchemy
- SQLite
- PyMuPDF
- Tesseract/Pytesseract
- ReportLab
- Ollama local inference

### Frontend Stack

- Astro 6.4
- Tailwind CSS v4
- Lucide icons
- Client-side polling/fetching
- High-density investigator dashboard UI

---

## 7. Repository Structure

```text
Real-Time-Anomaly_Detection/
├── dataset/
│   ├── reference/
│   ├── testing/
│   │   ├── clean_cases/
│   │   ├── forensic_cases/
│   │   ├── fraud_cases/
│   │   └── ocr_cases/
│   └── tampered documents/
├── fraud_detection_system/
│   ├── backend/
│   │   ├── api/
│   │   ├── core/
│   │   ├── layers/
│   │   │   ├── ai/
│   │   │   ├── anomaly/
│   │   │   ├── classification/
│   │   │   ├── context/
│   │   │   ├── cross_document/
│   │   │   ├── extraction/
│   │   │   ├── forensics/
│   │   │   └── scoring/
│   │   ├── models/
│   │   ├── services/
│   │   ├── trusted_repository/
│   │   └── main.py
│   └── frontend/
│       ├── src/
│       │   ├── layouts/
│       │   ├── pages/
│       │   ├── services/
│       │   └── styles/
│       └── package.json
├── scripts/
│   └── start-anobis.sh
├── Makefile
├── ARCHITECTURE.md
└── README.md
```

---

## 8. Installation Prerequisites

### System Tools

- Python 3.10+
- Node.js 22.12+
- npm
- Tesseract OCR
- Ollama
- `make`
- `curl`

### Tesseract OCR

Ubuntu/Debian:

```bash
sudo apt-get update
sudo apt-get install tesseract-ocr tesseract-ocr-eng tesseract-ocr-hin
```

macOS:

```bash
brew install tesseract
```

Windows:

Install from the UB Mannheim build and add Tesseract to `PATH`:

```text
https://github.com/UB-Mannheim/tesseract/wiki
```

### Ollama

Install Ollama:

```text
https://ollama.com
```

Pull the required model:

```bash
ollama pull gemma4:e4b
```

---

## 9. First-Time Setup

### Backend

```bash
cd fraud_detection_system/backend
python -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.txt
```

Optional backend `.env`:

```env
USE_LOCAL_LLM=True
OLLAMA_MODEL=gemma4:e4b
OLLAMA_BASE_URL=http://localhost:11434
```

### Frontend

```bash
cd fraud_detection_system/frontend
npm install
```

Optional frontend `.env`:

```env
PUBLIC_API_URL=http://localhost:8001
```

### Start the App

From the repo root:

```bash
make start
```

---

## 10. Manual Startup Commands

If you do not want to use the launcher, run these in separate terminals.

Terminal 1:

```bash
ollama serve
```

Terminal 2:

```bash
cd fraud_detection_system/backend
.venv/bin/python -m uvicorn main:app --host 127.0.0.1 --port 8001
```

Terminal 3:

```bash
cd fraud_detection_system/frontend
PUBLIC_API_URL=http://localhost:8001 npm run dev -- --host 127.0.0.1 --port 4321
```

Open:

```text
http://127.0.0.1:4321/
```

---

## 11. REST API Endpoint Catalog

Backend base URL:

```text
http://127.0.0.1:8001/api/v1
```

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `GET` | `/health` | Basic API health and forensic layer availability. |
| `GET` | `/system/health` | Full system health: database, OCR, dataset, KNN, Ollama, model warmup. |
| `POST` | `/system/warmup` | Explicit Ollama/Gemma warmup request. |
| `GET` | `/investigations` | List investigations. |
| `POST` | `/investigations` | Create a new investigation. |
| `GET` | `/investigations/{id}` | Get full investigation object. |
| `POST` | `/investigations/{id}/documents` | Upload one or more documents. |
| `POST` | `/investigations/{id}/analyze` | Start background analysis. |
| `GET` | `/investigations/{id}/status` | Poll analysis progress and stage. |
| `GET` | `/investigations/{id}/results` | Retrieve scores, findings, AI summary, documents, timeline, similarity. |
| `GET` | `/investigations/{id}/events` | Retrieve audit timeline. |
| `GET` | `/investigations/{id}/report` | Download PDF report. |
| `GET` | `/investigations/{id}/documents/{doc_id}/file` | Serve uploaded/converted document for viewer. |
| `POST` | `/investigations/{id}/approve-reference` | Persist completed case as a trusted local baseline. |
| `POST` | `/investigate` | Legacy single-document quick analysis endpoint. |

Example create case:

```bash
curl -X POST http://127.0.0.1:8001/api/v1/investigations \
  -H "Content-Type: application/json" \
  -d '{"context":"Loan Approval","title":"Judge Demo Case"}'
```

---

## 12. How the Pipeline Works

1. **Create case**: Stores investigation metadata in SQLite.
2. **Upload files**: Saves documents under backend uploads.
3. **Extraction**: Reads PDF text or runs OCR for images/scans.
4. **Classification**: Identifies document type.
5. **Entity extraction**: Extracts names, IDs, accounts, salary, employer, etc.
6. **Forensics**: Inspects metadata, structure, creators, suspicious editing traces.
7. **Context validation**: Applies domain-specific banking/financial checks.
8. **Cross-document validation**: Finds contradictions across the document bundle.
9. **Scoring**: Computes a normalized 0-100 Trust Score plus internal quality gates.
10. **Similarity**: Compares against genuine/fraud/reference datasets.
11. **AI synthesis**: Gemma generates grounded bilingual reasoning from deterministic outputs.
12. **Reporting**: JSON results and PDF report are produced.
13. **Reference approval**: Completed cases can become trusted future baselines.

---

## 13. Validation Commands

Backend syntax check:

```bash
python -m compileall fraud_detection_system/backend/api fraud_detection_system/backend/core fraud_detection_system/backend/layers/ai fraud_detection_system/backend/layers/scoring fraud_detection_system/backend/services fraud_detection_system/backend/trusted_repository
```

Frontend build:

```bash
cd fraud_detection_system/frontend
npm run build
```

Health check:

```bash
curl http://127.0.0.1:8001/api/v1/system/health
```

---

## 14. Troubleshooting

### Port 8000 is already in use

The verified local setup uses backend port `8001`. If needed:

```bash
BACKEND_PORT=8002 FRONTEND_PORT=4322 make start
```

### Ollama is not running

Start it manually:

```bash
ollama serve
```

Then verify:

```bash
curl http://127.0.0.1:11434/api/tags
```

### `gemma4:e4b` is missing

Install it:

```bash
ollama pull gemma4:e4b
```

### AI says offline or deterministic fallback

Check:

```bash
curl http://127.0.0.1:8001/api/v1/system/health
```

You want:

```json
{
  "ai": "ready",
  "model": "gemma4:e4b",
  "warm": true
}
```

### Tesseract OSD warning

If logs mention missing `osd.traineddata`, OCR can still work. It only affects automatic orientation detection. Install additional Tesseract data if rotation detection is required.

### First AI run is slow

`gemma4:e4b` is large and may take 40-90 seconds to warm on CPU-only machines. The launcher waits for backend readiness before opening the app.

---

## 15. Judge Evaluation Checklist

Use this checklist to evaluate the project quickly:

- Does it run offline after dependencies are installed?
- Does `/api/v1/system/health` show database, OCR, dataset, KNN, and AI ready?
- Can a user create an investigation?
- Can multiple documents be uploaded?
- Does status polling update during analysis?
- Is the Trust Score normalized from 0 to 100?
- Does the result page show OCR text, metadata, findings, and document preview?
- Does the AI summary show `ai_mode: ollama` and `ai_model: gemma4:e4b`?
- Does PDF export work?
- Does approving a reference update the trusted local repository?

---

## 16. Project Status

MVP is complete and demo-ready:

- Investigation lifecycle: complete
- Multi-document upload: complete
- OCR/extraction: complete
- Forensics: complete
- Cross-document validation: complete
- Trust scoring and internal quality gates: complete
- Dataset/KNN similarity: complete
- Local Gemma reasoning: complete
- PDF export: complete
- Trusted reference approval: complete
- One-command launcher: complete

Known practical constraint:

- Local Gemma inference speed depends on machine CPU/GPU resources.
