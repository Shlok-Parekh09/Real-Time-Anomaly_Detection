# Anobis: Enterprise Document Fraud & Forensic Investigation Platform

Anobis is an enterprise-grade document fraud and forensic investigation platform designed for banking compliance, loan underwriting, and corporate audit teams. Unlike isolated document classifiers, Anobis acts as a central workspace that correlates and validates groups of identity and financial documents to expose tampering and coordinated cross-document fraud.

---

## 1. Key Platform Capabilities

*   **Multi-Document Lifecycle**: Create investigation cases, upload sets of documents (IDs, payslips, bank statements), and analyze them in parallel.
*   **Modular Forensics Engine**: Detects structural tampering, PDF metadata modification, tool signatures (e.g., Canva/Photoshop), and revision discrepancies.
*   **Cross-Document Entity Matching**: Performs fuzzy-text verification for names, ID numbers, values, and addresses across the entire document set.
*   **Dual AI Summary Synthesis**: Generates clear executive summaries in **English and Hindi** with hallucination-protected findings.
*   **Split-Pane Forensic Workbench**: Interactively inspect document previews, extracted raw text, and structured properties side-by-side.
*   **Explainable Trust Engine**: Computes deterministic 0-100 Trust and Confidence scores based on rules-based analysis, avoiding arbitrary "black-box" models.
*   **Audit Timeline Log**: A chronological timeline tracking every forensic, text extraction, and validation event in the pipeline.

---

## 2. Technical Stack

*   **Frontend**: Astro 6.4 (Static/Hybrid), Tailwind CSS v4, Lucide Icons, Nano Stores (for status polling).
*   **Backend**: Python FastAPI, SQLAlchemy ORM (SQLite).
*   **OCR & Extraction**: Tesseract OCR (Pytesseract), PyMuPDF (PDF Parser).
*   **AI Synthesis**: Gemini 2.5 Flash / Local Ollama (Qwen2.5:3b).

---

## 3. Repository Structure

```text
Real-Time-Anomaly_Detection/
├── dataset/                # Benchmarking documents and training references
│   ├── reference/          # Reference documents for KYC/property records
│   └── testing/            # Scenarios (Clean, Forensic, Fraud, OCR)
├── fraud_detection_system/
│   ├── backend/            # Modular FastAPI Backend
│   │   ├── api/            # REST endpoint routes (/api/v1)
│   │   ├── core/           # Database config and app settings
│   │   ├── models/         # SQLAlchemy DB models & Pydantic schemas
│   │   ├── layers/         # Domain engines (Forensics, Extraction, AI, Scoring)
│   │   ├── services/       # Orchestrator layers (InvestigationManager)
│   │   └── main.py         # FastAPI App entrypoint
│   └── frontend/           # Astro Web Application
├── ARCHITECTURE.md         # Technical architecture details
└── README.md               # User & Developer setup guide
```

---

## 4. System Prerequisites & Installation

To run Anobis locally, install the following core system requirements.

### A. Tesseract OCR (OCR Engine)
Tesseract is required to extract text from scanned documents and images.

*   **Linux (Ubuntu/Debian)**:
    ```bash
    sudo apt-get update
    sudo apt-get install tesseract-ocr tesseract-ocr-eng tesseract-ocr-hin
    ```
*   **macOS**:
    ```bash
    brew install tesseract
    ```
*   **Windows**:
    1. Download the installer from the [UB Mannheim Repository](https://github.com/UB-Mannheim/tesseract/wiki).
    2. Add the installation path (typically `C:\Program Files\Tesseract-OCR`) to your system's `PATH` environment variable.

### B. Ollama (Local AI Engine)
Ollama runs LLMs locally on your workstation for offline summarization.

1. Download and install Ollama from [ollama.com](https://ollama.com).
2. Pull the default 3B parameters model:
   ```bash
   ollama pull qwen2.5:3b
   ```
3. Start the Ollama local server:
   ```bash
   ollama serve
   ```

---

## 5. Local Setup Instructions

### A. Backend Setup (FastAPI)

1. Navigate to the backend directory:
   ```bash
   cd fraud_detection_system/backend
   ```
2. Create and activate a Python virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```
3. Install the dependencies:
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```
4. Create a `.env` file in `fraud_detection_system/backend/` and configure:
   ```env
   # Set to True to use Ollama locally (Ensure Ollama is running and qwen2.5:3b is pulled)
   USE_LOCAL_LLM=True
   
   # If USE_LOCAL_LLM=False, provide Gemini API Key
   GEMINI_API_KEY=your_gemini_api_key_here
   ```
5. Start the backend server on port `8080`:
   ```bash
   uvicorn main:app --host 127.0.0.1 --port 8080 --reload
   ```

### B. Frontend Setup (Astro)

1. Navigate to the frontend directory:
   ```bash
   cd fraud_detection_system/frontend
   ```
2. Install package dependencies:
   ```bash
   npm install
   ```
3. Create a `.env` file in `fraud_detection_system/frontend/` and point to the backend API:
   ```env
   PUBLIC_API_URL=http://localhost:8080
   ```
4. Start the frontend developer server:
   ```bash
   npm run dev
   ```
5. Open your browser to `http://localhost:4321` to view the platform workbench.

---

## 6. REST API Endpoint Catalog

All routes are prefixed by `/api/v1` on the backend:

| Endpoint | Method | Input / Body | Description |
| :--- | :--- | :--- | :--- |
| `/investigations` | `GET` | None | Lists all investigations. |
| `/investigations` | `POST` | `{ "context": "Loan Approval", "title": "Case 1" }` | Creates a new investigation. |
| `/investigations/{id}` | `GET` | None | Retrieves high-level details of a case. |
| `/investigations/{id}/documents` | `POST` | `multipart/form-data` (files) | Uploads files to an investigation. |
| `/investigations/{id}/analyze` | `POST` | None | Starts the async analysis pipeline. |
| `/investigations/{id}/status` | `GET` | None | Polls current progress percentage and stage. |
| `/investigations/{id}/results` | `GET` | None | Retrieves findings, trust scores, and summaries. |
| `/investigations/{id}/report` | `GET` | None | Generates and exports a PDF format report. |

---

## 7. Demo Verification Walkthrough

You can verify the entire setup runs correctly using the provided test suite.

### A. Automatic Testing Script
To run an automated E2E analysis pipeline test using the reference dataset:
1. Activate your backend virtual environment:
   ```bash
   cd fraud_detection_system/backend
   source .venv/bin/activate
   ```
2. Execute the verification script:
   ```bash
   python test_offline_pipeline.py
   ```
This will automatically initialize a temporary SQLite database, load testing cases, run them through OCR, digital forensics, cross-document analysis, trust scoring, and local AI synthesis, verifying that the entire stack is operational.

### B. Manual Verification in UI
1. Open the UI homepage at `http://localhost:4321`.
2. Click **Investigate** to go to the Dashboard.
3. Click **New Investigation**. Select a context (e.g. `Mortgage Underwriting`) and give it a title.
4. Drag and drop sample documents from the `dataset/testing/` folder (such as standard HDFC statements or tampered Canara statements) and click **Start Forensic Analysis**.
5. You will see real-time progress updates. Once completed, the workbench will render the trust scores, bilingual findings, and document previews side-by-side.
