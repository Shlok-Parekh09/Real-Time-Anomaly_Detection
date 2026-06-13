# Anobis: Banking Document Fraud & Anomaly Detection

## Project Overview

### Problem Statement
In modern banking, mortgage underwriting, and KYC processes, document fraud has become increasingly sophisticated. Single-document classification is no longer enough to detect coordinated forgery attempts. Underwriters are overwhelmed by manual verification, leading to slow processing times and increased risk exposure.

### The Solution: Anobis
Anobis is an **investigation-centric** document fraud detection platform. Instead of analyzing documents in isolation, it treats multiple documents as part of a single **Investigation**. By correlating data across IDs, payslips, and bank statements, Anobis identifies contradictions and tampering that traditional systems miss.

### Why it Matters
*   **Prevent Financial Loss:** Catch sophisticated forgery before credit is extended.
*   **Operational Efficiency:** Reduce manual review time by 60% with evidence-based findings.
*   **Explainable AI:** Move beyond "Black Box" scores. Every flag is backed by physical evidence and deterministic math.

---

## Key Features

*   **Multi-Document Investigations:** Analyze a complete case (ID + Payslip + Bank Statement) as a single entity.
*   **Automated Classification:** Automatically detects document types (e.g., PAN, Aadhaar, Bank Statement) to apply correct validation rules.
*   **Digital Forensics:** Detects metadata manipulation, software signatures (Photoshop/Canva), and PDF revision history.
*   **Context-Aware Validation:** Validates bank statement math and payslip consistency based on the investigation goal (e.g., Loan Approval).
*   **Cross-Document Intelligence:** Matches names, IDs, and financial values across different files to detect identity or income mismatches.
*   **Deterministic Scoring:** Transparent 0-100 Trust and Confidence scores.
*   **Multilingual AI Summaries:** Generates plain-language summaries in **English and Hindi** for regional investigators.
*   **Audit Timeline:** A complete chronological log of every forensic step taken during the investigation.

---

## Architecture Overview

Anobis uses a modular, asynchronous pipeline architecture:

**Investigation** $\rightarrow$ **Upload** $\rightarrow$ **Extraction** $\rightarrow$ **Entity Extraction** $\rightarrow$ **Forensics** $\rightarrow$ **Context Validation** $\rightarrow$ **Cross-Doc Validation** $\rightarrow$ **Trust Engine** $\rightarrow$ **AI Summary** $\rightarrow$ **Report**

---

## Technology Stack

*   **Frontend:** Astro, TypeScript, Tailwind CSS, Nano Stores.
*   **Backend:** FastAPI (Python), SQLAlchemy ORM.
*   **Database:** SQLite (SQLAlchemy for easy PostgreSQL migration).
*   **AI:** Gemini 2.5 Flash (Technical Translation & Summarization).
*   **Forensics:** PyMuPDF (PDF Structure), OpenCV (Image Metadata), Levenshtein/Jaro-Winkler (Fuzzy Matching).

---

## Repository Structure

```text
Real-Time-Anomaly_Detection/
├── dataset/                # Sample data for demo and testing
├── fraud_detection_system/
│   ├── backend/            # Modular FastAPI application
│   │   ├── api/            # REST Endpoints & Dependencies
│   │   ├── core/           # Config & DB Initialization
│   │   ├── models/         # SQLAlchemy & Pydantic Schemas
│   │   ├── layers/         # Domain Logic (Forensics, Extraction, etc.)
│   │   ├── services/       # Orchestrators (InvestigationManager)
│   │   ├── legacy/         # Archived legacy scripts
│   │   └── main.py         # Entry Point
│   └── frontend/           # Astro Web Application
└── README.md
```

---

## API Overview

| Endpoint | Method | Description |
| :--- | :--- | :--- |
| `/investigations` | `GET` | List all investigations (Dashboard) |
| `/investigations` | `POST` | Create a new investigation case |
| `/investigations/{id}/documents` | `POST` | Upload documents to a case |
| `/investigations/{id}/analyze` | `POST` | Trigger async forensic pipeline |
| `/investigations/{id}/status` | `GET` | Real-time progress and stage tracking |
| `/investigations/{id}/results` | `GET` | Full investigation findings and report data |
| `/investigations/{id}/events` | `GET` | Complete audit timeline |

---

## Local Setup

### Backend Setup
1. `cd fraud_detection_system/backend`
2. `python -m venv .venv && source .venv/bin/activate`
3. `pip install -r requirements.txt`
4. Create a `.env` file with your `GEMINI_API_KEY`.
5. `uvicorn main:app --reload`

### Frontend Setup
1. `cd fraud_detection_system/frontend`
2. `npm install`
3. `npm run dev`

---

## Future Enhancements
*   **KNN Anomaly Detection:** Statistical outlier detection against a trusted document repository.
*   **Similarity Engine:** Identifying known fraudulent templates across different investigations.
*   **Advanced Image Forensics:** Deep Error Level Analysis (ELA) for image-based uploads.
*   **PDF Export:** Generating immutable forensic audit reports in PDF format.
