# Real-Time Document Fraud Detection

AI-assisted document forensics for bank statements, financial documents, images, and spreadsheets. The app uses a FastAPI backend for file analysis and a single Vite/React frontend for the landing page and underwriter dashboard.

## What It Does

- Opens one frontend from the repo root with `npm run dev`.
- Shows an intro page with a top `Start` button.
- Opens the full underwriter dashboard on the same frontend when `Start` is clicked.
- Accepts PDF, image, Excel workbook, CSV, and TSV uploads.
- Detects fraud signals such as X-ray revision recovery, masking, suspicious software metadata, date mismatch, annotations, hidden workbook content, external links, and validation failures.
- Shows an X-ray comparison view inspired by the reference video: recovered previous content, submitted content, a reveal slider, and extracted alteration details.
- Uses `CEREBRAS_API_KEY` for AI-generated explanations, with a local fallback when no key is configured.

## Project Layout

```text
.
├── src/                              # Single active React frontend
│   └── app/
│       ├── App.tsx                   # Landing page + Start button flow
│       ├── UnderwriterDashboard.tsx  # Active document review UI
│       └── sections.tsx              # Landing page sections
├── fraud_detection_system/
│   └── backend/
│       ├── main.py                   # FastAPI API
│       ├── forensics.py              # X-ray recovery, fraud signals, Cerebras narrative
│       ├── local_validation.py       # Text extraction and math checks
│       └── requirements.txt
├── package.json                      # Root frontend scripts
└── README.md
```

`fraud_detection_system/frontend` is no longer the app you need to run for the UI. The root frontend owns the dashboard now, so there is no separate `5174` frontend.

## Backend Setup

From the repo root:

```powershell
python -m pip install -r fraud_detection_system\backend\requirements.txt
```

Optional Cerebras configuration:

```powershell
$env:CEREBRAS_API_KEY="your_cerebras_key"
$env:CEREBRAS_MODEL="gpt-oss-120b"
```

Start the backend:

```powershell
cd fraud_detection_system\backend
python -m uvicorn main:app --host 127.0.0.1 --port 8000
```

Health check:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
```

## Frontend Setup

From the repo root:

```powershell
npm install
npm run dev
```

Open:

```text
http://127.0.0.1:5173
```

Click `Start` in the top navigation to open the document forensics dashboard on the same port.

## How To Use

1. Start the backend on `127.0.0.1:8000`.
2. Start the root frontend with `npm run dev`.
3. Open `http://127.0.0.1:5173`.
4. Click `Start`.
5. Upload a PDF, image, Excel workbook, CSV, or TSV.
6. Click `Run Forensics`.
7. Review the trust score, fraud signals, X-ray recovered version, parsed details, and AI explanation.

## API

Main endpoint:

```http
POST /api/v1/analyze
```

Multipart field:

```text
file=<uploaded document>
```

The response includes:

- `file_type`
- `risk_score`
- `trust_score`
- `fraud_signals`
- `recovered_version`
- `ai_explanation`
- `metadata`
- `extracted_text`
- `validation_status`
- `validation_checks`

## Notes

- The X-ray feature can recover prior PDF incremental revisions when the PDF still contains previous bodies.
- For `.xlsx/.xlsm`, it scans workbook internals for hidden sheets, formulas, external links, comments, and unreferenced shared strings that can reveal overwritten values.
- Legacy `.xls` files are accepted, but deep workbook recovery is limited because the format is binary OLE.
- Image OCR depends on local Tesseract availability. The rest of the backend still runs if OCR is unavailable.
- The UI falls back to local explanation text unless `CEREBRAS_API_KEY` is set before starting the backend.
