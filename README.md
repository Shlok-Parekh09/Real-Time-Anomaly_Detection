# Real-Time Document Fraud Detection

AI-assisted document forensics for PDFs and images. The repo now runs one Vite/React frontend on port `5173` and one FastAPI backend on port `8000`.

## Features

- Single command from the repo root with `npm run dev` starts both FastAPI and Vite.
- Start button flow that opens the underwriter dashboard on the same port.
- Upload support for PDF and image files.
- X-ray view that renders the real uploaded document in grayscale, fits PDF pages, hides PDF navigation panes where the browser supports it, and marks anomaly regions in red.
- Fraud signals for recovered PDF revisions, masking, suspicious software metadata, date mismatches, annotations, image copy-move indicators, and validation failures.
- Settings panel for X-ray behavior and evidence marker visibility.
- Accept and Reject actions that store the uploaded document in local authorized or private unauthorized SQLite tables.
- Cerebras-generated explanations from the API key entered in the dashboard header, with local fallback text when it is not provided.

## Project Layout

```text
.
|-- src/                              # Active React frontend
|   `-- app/
|       |-- App.tsx                   # Landing page and Start button flow
|       |-- UnderwriterDashboard.tsx  # Active review dashboard
|       `-- sections.tsx              # Landing page sections
|-- fraud_detection_system/
|   `-- backend/
|       |-- main.py                   # FastAPI API
|       |-- forensics.py              # X-ray recovery, fraud signals, Cerebras narrative
|       |-- local_validation.py       # Text extraction and math checks
|       `-- requirements.txt
|-- package.json                      # Root frontend scripts
`-- README.md
```

`fraud_detection_system/frontend` is not the active UI. Use the root frontend only; there is no separate `5174` app required.

## Backend Setup

From the repo root:

```powershell
python -m pip install -r fraud_detection_system\backend\requirements.txt
```

Optional Cerebras configuration. The dashboard also has a top header field for a per-analysis key:

```powershell
$env:CEREBRAS_API_KEY="your_cerebras_key"
$env:CEREBRAS_MODEL="gpt-oss-120b"
```

You can still start only the backend for API work:

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

`npm run dev` checks the backend Python packages, installs `fraud_detection_system\backend\requirements.txt` if needed, and starts the backend at `http://127.0.0.1:8000`. Click `Start` to enter the dashboard.

## Workflow

1. Start both services with `npm run dev`.
2. Upload a PDF or image file.
3. Optionally enter a Cerebras API key in the top header field for generated descriptions.
4. Click `Run Forensics`.
5. Review the trust score, fraud signals, X-ray view, parsed details, and AI explanation.
6. Use `Accept` or `Reject` to save the uploaded document into the authorized or unauthorized local database table.

## API

Main endpoint:

```http
POST /api/v1/analyze
```

Multipart field:

```text
file=<uploaded document>
cerebras_api_key=<optional transient Cerebras key>
```

Review decision endpoint:

```http
POST /api/v1/review-decision
```

Multipart fields:

```text
decision=accepted|rejected
file=<uploaded document>
analysis_json=<analysis response JSON>
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

- CSV, TSV, and Excel uploads are intentionally rejected by the UI and API.
- PDF X-ray recovery depends on the PDF retaining incremental update history in its bytes.
- Image OCR depends on local Tesseract availability. Other backend checks still run if OCR is unavailable.
- Decision storage is local-only at `fraud_detection_system/backend/data/document_forensics.sqlite3`; there is no public endpoint that lists unauthorized documents.
- Enter `CEREBRAS_API_KEY` in the dashboard header or set it before starting the backend to use Cerebras for richer explanations.
