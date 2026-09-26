# Anobis Investigation Scenarios

This document maps existing files in the reorganized dataset into realistic investigation scenarios for system validation and integration testing.

---

## Scenario 01: Corporate Fraud Verification
* **Documents**:
  * [652591331-Canara-Bank-Statement.pdf](./testing/clean_cases/652591331-Canara-Bank-Statement.pdf)
  * [855219459-canara-bank-statement.pdf](./testing/fraud_cases/855219459-canara-bank-statement.pdf)
* **Purpose**: Mortgage Underwriting & Corporate Due Diligence
* **Expected Outcome**: **HIGH RISK** (Tampered statement detected. The metadata flags LibreOffice export, the balance is grossly inflated, and there is a name mismatch between the address block and internal fields).

---

## Scenario 02: KYC & Signature Discrepancy
* **Documents**:
  * [sxdw2.jpg](./reference/sxdw2.jpg)
  * [xwd.jpg](./testing/fraud_cases/xwd.jpg)
* **Purpose**: KYC Verification
* **Expected Outcome**: **HIGH RISK / MANUAL REVIEW** (Name validation mismatch. The PAN card for Twitterpreet Singh contains a signature reading "Twitherpreet Singh", which must trigger identity mismatch alerts).

---

## Scenario 03: Maharashtra Property Underwriting
* **Documents**:
  * [817414893-6-9.pdf](./testing/clean_cases/817414893-6-9.pdf) (7/12 Land Record)
  * [cidco-naina-s2-wing-a-part-oc-letter-26th-floor-dt.-06.06.2024.jpg](./testing/ocr_cases/cidco-naina-s2-wing-a-part-oc-letter-26th-floor-dt.-06.06.2024.jpg) (Occupancy Certificate)
* **Purpose**: Mortgage Underwriting
* **Expected Outcome**: **Clean Case / AUTO_APPROVE** (All documents are verified property credentials matching the applicant's development details in the Navi Mumbai/Thane area).

---

## Scenario 04: Agricultural Land Verification
* **Documents**:
  * [836160713-७-१२-1.pdf](./testing/clean_cases/836160713-७-१२-1.pdf) (Marathi 7/12 extract)
  * [695e62ce9fcea_1767793358.png](./testing/ocr_cases/695e62ce9fcea_1767793358.png) (Scanned receipt containing matching PAN)
* **Purpose**: Rural Credit Assessment
* **Expected Outcome**: **MANUAL_REVIEW** (Due to the low-quality scanned receipt requiring Marathi OCR translation and validation).

---

## Scenario 05: Multi-State Property Portfolio Tax Audit
* **Documents**:
  * [1.png](./testing/ocr_cases/1.png) (Ulhasnagar tax bill)
  * [fwf.png](./testing/ocr_cases/fwf.png) (GVMC Visakhapatnam tax receipt)
  * [GHMC_Property_Tax_Notice-2.jpg](./testing/ocr_cases/GHMC_Property_Tax_Notice-2.jpg) (GHMC property tax notice)
* **Purpose**: Credit Assessment / HNW Underwriting
* **Expected Outcome**: **MANUAL_REVIEW** (Testing OCR alignment and tax history validations across three municipal databases).

---

## Scenario 06: Template Metadata Forgery Detection
* **Documents**:
  * [Chase bank satement.pdf](./testing/fraud_cases/Chase bank satement.pdf)
  * [Commonwealthbank.pdf](./testing/fraud_cases/Commonwealthbank.pdf)
* **Purpose**: Loan Approval / Risk Verification
* **Expected Outcome**: **HIGH RISK** (Forensic analysis triggers alert because the PDFs were generated via a Word processor from an online template by author 'Shlok Parekh', containing location mismatches).
