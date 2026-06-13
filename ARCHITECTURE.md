# Anobis: Backend System Architecture

## System Philosophy
Anobis is designed as an **Investigation-Centric** platform. In traditional fraud detection, documents are often analyzed in isolation. Anobis acknowledges that fraud in banking and legal contexts is rarely contained in a single file. Instead, it is found in the **contradictions** between documents (e.g., a payslip name that doesn't match an Aadhaar card) or in **contextual anomalies** (e.g., bank statement math failing during a loan application). 

The primary entity in the system is the **Investigation**, which acts as a container for multiple documents, findings, and evidence.

---

## End-to-End Execution Flow
When a user clicks "Start Analysis", the following asynchronous pipeline executes:

1.  **Extraction Layer:** Converts Word to PDF, extracts raw text, metadata, and document layout coordinates.
2.  **Classification Layer:** Auto-identifies document types (Bank Statement, PAN, etc.) using keyword/regex scoring.
3.  **Entity Extraction Layer:** Pulls structured data (Name, DOB, ID numbers, Salary) from the raw text.
4.  **Forensics Layer:** Runs deterministic tampering checks (Metadata editing traces, PDF revision history).
5.  **Context Validation Layer:** Applies business-rule validation based on the investigation context (e.g., Bank Statement math).
6.  **Cross-Document Validation Layer:** Compares entities across all documents to identify inconsistencies.
7.  **Trust Engine:** Aggregates all findings into a final 0-100 Trust Score and Confidence Score.
8.  **AI Summary Layer:** Translates technical forensic findings into plain English and Hindi summaries.
9.  **Reporting Layer:** Synthesizes all data into a unified JSON/PDF audit report.

---

## Layer Breakdown

### Intake & Extraction
*   **Module:** `layers/intake/`, `layers/extraction/`
*   **Responsibility:** Securely stores uploaded files and normalizes them into structured JSON data. It maps every piece of text to its exact X,Y coordinates on the page for visual highlighting.

### Forensics & Context
*   **Module:** `layers/forensics/`, `layers/context/`
*   **Responsibility:** The "Deterministic Engine". It looks for "Smoking Guns" like Canva/Photoshop signatures in metadata or mathematical failures in transaction lists.

### Cross-Document Intelligence
*   **Module:** `layers/cross_document/`
*   **Responsibility:** The "Pattern Matcher". It uses fuzzy matching algorithms (Jaro-Winkler, Levenshtein) to identify if "Rahul Sharma" and "R. Sharma" are likely the same person, or if different PAN numbers are being used across files.

---

## Database Schema
Anobis uses a relational SQLite schema (via SQLAlchemy):

*   **`Investigations`:** Parent record storing status, scores, and recommendations.
*   **`Documents`:** Child records storing raw text, metadata, and extracted entities.
*   **`Findings`:** Forensic flags (e.g., "Income Mismatch") linked to an investigation.
*   **`Evidence`:** Specific pointers (page, coordinates, text) linking a Finding back to one or more Documents.
*   **`InvestigationEvents`:** Chronological audit log of the pipeline lifecycle.

---

## Scoring Methodology

### Trust Score (Risk)
*   **Base:** 100
*   **Deductions:** High (-35), Medium (-18), Low (-8).
*   **Caps:** Max LOW deduction is 25; Max MEDIUM is 50. HIGH is uncapped.
*   **Bonuses:** +5 for complete document sets; +5 for strong cross-doc consistency.

### Confidence Score (Quality)
*   **Formula:** `(OCR_Quality * 0.4) + (Entity_Success * 0.4) + (Evidence_Clarity * 0.2)`
*   **Penalty:** -20 for missing required documents.

### Recommendation Matrix
*   **AUTO_APPROVE:** Trust > 85 AND Confidence > 80.
*   **HIGH_RISK_MANUAL_REVIEW:** Trust < 50.
*   **MANUAL_REVIEW:** All other cases or if Confidence < 60.

---

## API & Frontend Interaction
The frontend interacts with the system via a **Polling Pattern**:
1.  `POST /analyze` starts the background task.
2.  `GET /status` is called every 2s to update the UI progress bar and current stage.
3.  `GET /results` is called once once status reaches `COMPLETED`.

---

## Current MVP Status

| Feature | Status |
| :--- | :--- |
| **Investigation Pipeline** | IMPLEMENTED |
| **PDF Forensics** | IMPLEMENTED |
| **Cross-Doc Validation** | IMPLEMENTED |
| **AI Summaries** | IMPLEMENTED |
| **Hindi Support** | IMPLEMENTED |
| **Image ELA** | PLANNED |
| **KNN Anomalies** | PLANNED |
| **PDF Export** | PLANNED |

---

## Development Guidelines
*   **New Forensic Checks:** Add to `layers/forensics/` and register in `InvestigationManager`.
*   **New Contexts:** Add to `layers/context/context_templates.py`.
*   **Entity Updates:** Modify `layers/extraction/entity_extractor.py`.

**Maintainer Note:** Always ensure any new layer logs its progress to the `InvestigationEvent` table to maintain the UI audit timeline.
