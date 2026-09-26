# Anobis Missing Document Gaps

To achieve production-grade testing coverage across all operational layers of our fraud detection platform, the following target documents must be acquired or synthetically generated:

---

## 1. Loan Approval
* **Standard Salary Slips/Payslips**:
  * *Status*: **Missing** (We have zero payslips in the dataset). We need payslips from common corporations (TCS, Infosys, etc.) in clean PDF and scanned image formats.
  * *Purpose*: To test net pay extraction, employee detail alignment, and salary credits comparison.
* **Form 16 / Income Tax Returns (ITR-V)**:
  * *Status*: **Missing**.
  * *Purpose*: To verify annual salary matching against bank statement credits.

---

## 2. Mortgage Underwriting
* **Registered Sale Deeds**:
  * *Status*: **Missing** (The Morbi Deed is an old, generic ownership deed; we need modern multi-page sale deeds).
  * *Purpose*: To test legal contract text extraction, buyer/seller name validation, and property boundary matching.
* **Non-Encumbrance Certificates (EC)**:
  * *Status*: **Missing**.
  * *Purpose*: Validate that there are no active liens or mortgages registered on the asset.
* **Approved Building Layout Blueprints**:
  * *Status*: **Missing**.
  * *Purpose*: To test structural fraud and map verification.

---

## 3. KYC
* **Aadhaar Cards**:
  * *Status*: **Missing** (We have zero Aadhaar scans).
  * *Purpose*: Aadhaar is the primary identity document in India. We need front/back card scans, masked templates, and tampered cards (e.g. mismatched photo or invalid digits) to test core KYC validation.
* **Passports & Voter ID Cards**:
  * *Status*: **Missing**.
  * *Purpose*: Broaden national identity parsing checks.

---

## 4. Insurance Claims
* **Medical Discharge Summaries**:
  * *Status*: **Missing**.
  * *Purpose*: Test health insurance claim validation and check for doctor credentials and billing anomalies.
* **FIR / Police Reports**:
  * *Status*: **Missing**.
  * *Purpose*: Audit motor insurance accident theft claims.

---

## 5. Credit Assessment
* **CIBIL / Experian Credit Reports**:
  * *Status*: **Missing**.
  * *Purpose*: Test parsing of monthly payment histories, outstanding balances, and credit scores.
* **Audited Corporate Financials (P&L, Balance Sheets)**:
  * *Status*: **Missing**.
  * *Purpose*: Parse business revenue and debt levels.
