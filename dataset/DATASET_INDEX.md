# Anobis Dataset Index

This file lists all reorganized files and their metadata for automated routing.

| Filename | Document Type | Quality | Category | Intended Use |
| :--- | :--- | :--- | :--- | :--- |
| [1.png](./testing/ocr_cases/1.png) | Utility Bill | OCR Required | TESTING_OCR | Validate property tax bill processing (Ulhasnagar) and test handling of WebP format saved as PNG. |
| [437141394-Canara-Bank-Statement-1.pdf](./reference/437141394-Canara-Bank-Statement-1.pdf) | Bank Statement | Clean | TRAINING_REFERENCE | Layout and transaction reference template mapping for Canara Bank. |
| [461790262-335063360-Hdfc-Bank-Statement-pdf.pdf](./testing/clean_cases/461790262-335063360-Hdfc-Bank-Statement-pdf.pdf) | Bank Statement | Clean | TESTING_CLEAN | Pipeline processing check for encrypted-but-readable PDFs (HDFC Bank). |
| [590283501-BANK-OF-INDIA-2.pdf](./testing/clean_cases/590283501-BANK-OF-INDIA-2.pdf) | Bank Statement | Clean | TESTING_CLEAN | Standard pipeline validation for Bank of India digital statements. |
| [623136717-BOB-STATEMENT.pdf](./testing/clean_cases/623136717-BOB-STATEMENT.pdf) | Bank Statement | Clean | TESTING_CLEAN | Performance checking on high-page statements (12 pages, Bank of Baroda). |
| [652591331-Canara-Bank-Statement.pdf](./testing/clean_cases/652591331-Canara-Bank-Statement.pdf) | Bank Statement | Clean | TESTING_CLEAN | Base case for Tollways validation; standard digital statement ingestion. |
| [691027383-7-12.pdf](./reference/691027383-7-12.pdf) | Property Record | Clean | TRAINING_REFERENCE | Reference layout template for Maharashtra land records (7/12 Satbara extract). |
| [695e62ce9fcea_1767793358.png](./testing/ocr_cases/695e62ce9fcea_1767793358.png) | Legal Document | Low Quality | TESTING_OCR | Validate hand-written/scanned receipt OCR mining (PAN validation). |
| [701113325-Union-Bank-1-Dec-Jan.pdf](./testing/forensic_cases/701113325-Union-Bank-1-Dec-Jan.pdf) | Bank Statement | Clean | TESTING_FORENSICS | Detect metadata indicators of forgery (created in MS Word by author 'sajan'). |
| [817414893-6-9.pdf](./testing/clean_cases/817414893-6-9.pdf) | Property Record | Clean | TESTING_CLEAN | Valid digital property record for cross-document consistency checks. |
| [836160713-७-१२-1.pdf](./testing/clean_cases/836160713-७-१२-1.pdf) | Property Record | Clean | TESTING_CLEAN | Test extraction of Marathi land records (7/12 Satbara extract). |
| [855219459-canara-bank-statement.pdf](./testing/fraud_cases/855219459-canara-bank-statement.pdf) | Bank Statement | Clean | TESTING_FRAUD | Validate detection of metadata traces (LibreOffice), modified layout fields, and inflated balance. |
| [99648855650474_100062377600994-scaled.jpg](./testing/ocr_cases/99648855650474_100062377600994-scaled.jpg) | Legal Document | OCR Required | TESTING_OCR | Test OCR processing of high-value Morbi stamp papers and deeds. |
| [BankStatementChequing.png](./testing/ocr_cases/BankStatementChequing.png) | Bank Statement | OCR Required | TESTING_OCR | OCR extraction testing on low-resolution bank screenshots. |
| [Chase bank satement.pdf](./testing/fraud_cases/Chase bank satement.pdf) | Bank Statement | Clean | TESTING_FRAUD | Detect template-generated forgery (created in MS Word by Shlok Parekh with inconsistent US/India locations). |
| [Commonwealthbank.pdf](./testing/fraud_cases/Commonwealthbank.pdf) | Bank Statement | Clean | TESTING_FRAUD | Verify detection of template-generated PDF and spelling typos ('ROBERT DAIEL GEE'). |
| [Copyof_NOC1-e1653737166786.jpg](./testing/ocr_cases/Copyof_NOC1-e1653737166786.jpg) | Legal Document | OCR Required | TESTING_OCR | Validate Tesseract OCR mining on scanned Government education certificates. |
| [GHMC_Property_Tax_Notice-2.jpg](./testing/ocr_cases/GHMC_Property_Tax_Notice-2.jpg) | Property Record | OCR Required | TESTING_OCR | Test extraction on low-contrast municipal tax bill scans. |
| [LD_1.jpg](./testing/ocr_cases/LD_1.jpg) | Legal Document | OCR Required | TESTING_OCR | Test multi-lingual OCR extraction on Hindi contract/stamp papers. |
| [Output.png](./testing/ocr_cases/Output.png) | Bank Statement | OCR Required | TESTING_OCR | Evaluate table boundary detection and OCR alignment on bank card statements. |
| [bank_statement_2.jpg](./testing/ocr_cases/bank_statement_2.jpg) | Bank Statement | Low Quality | TESTING_OCR | Verify pipeline robustness against camera curvature and shadow distortion. |
| [cidco-naina-s2-wing-a-part-oc-letter-26th-floor-dt.-06.06.2024.jpg](./testing/ocr_cases/cidco-naina-s2-wing-a-part-oc-letter-26th-floor-dt.-06.06.2024.jpg) | Property Record | OCR Required | TESTING_OCR | Validate property/occupancy detail matching against identity records. |
| [df.png](./testing/ocr_cases/df.png) | Legal Document | OCR Required | TESTING_OCR | Test OCR processing of Gift Deeds and extension validation (WebP saved as PNG). |
| [fwf.png](./testing/ocr_cases/fwf.png) | Utility Bill | OCR Required | TESTING_OCR | Validate tax receipt processing and extension check (WebP saved as PNG). |
| [image.png](./testing/ocr_cases/image.png) | Property Record | Low Quality | TESTING_OCR | Validate land record data extraction on low-resolution Goa Form I & XIV scans. |
| [sxdw2.jpg](./reference/sxdw2.jpg) | PAN | OCR Required | TRAINING_REFERENCE | KYC reference card template mapping for Permanent Account Number. |
| [vwhufwiu.png](./testing/ocr_cases/vwhufwiu.png) | Property Record | OCR Required | TESTING_OCR | Test parsing of international certificates of occupancy and extension mismatch. |
| [xwd.jpg](./testing/fraud_cases/xwd.jpg) | PAN | OCR Required | TESTING_FRAUD | Verify identity validation warning for spelling discrepancy between name and signature. |