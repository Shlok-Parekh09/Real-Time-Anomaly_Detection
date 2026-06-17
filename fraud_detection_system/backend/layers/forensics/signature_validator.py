"""
Digital Signature Validator
Checks PDF documents for digital signatures and their validity markers.
Genuine bank PDFs often carry digital signatures proving authenticity.
"""

import fitz  # PyMuPDF
import re
from typing import List
from models.domain import AnomalyFeature


def validate_digital_signatures(file_path: str) -> List[AnomalyFeature]:
    """
    Inspects the PDF for digital signature dictionaries.
    Reports missing, present, or potentially invalid signatures.
    """
    anomalies = []

    try:
        doc = fitz.open(file_path)
        pdf_bytes = open(file_path, "rb").read()

        # --- Check 1: Look for /Sig type entries in the raw PDF ---
        has_sig_field = bool(re.search(rb"/Type\s*/Sig", pdf_bytes))
        has_acroform = bool(re.search(rb"/AcroForm", pdf_bytes))
        has_sigflags = bool(re.search(rb"/SigFlags", pdf_bytes))
        has_byterange = bool(re.search(rb"/ByteRange", pdf_bytes))
        has_cert = bool(re.search(rb"/Cert", pdf_bytes)) or bool(re.search(rb"/PKCS", pdf_bytes))

        # Count signature fields
        sig_count = len(re.findall(rb"/Type\s*/Sig", pdf_bytes))

        # --- Check 2: Look for keywords in metadata that indicate it should be signed ---
        metadata = doc.metadata or {}
        text_sample = ""
        for page_num in range(min(3, len(doc))):
            text_sample += doc[page_num].get_text()

        text_lower = text_sample.lower()

        # Heuristic: does this look like an official bank document?
        is_likely_official = any(keyword in text_lower for keyword in [
            "bank statement", "account statement", "transaction history",
            "certificate", "digitally signed", "authorized signatory",
            "official document", "verified", "authenticated"
        ])

        doc.close()

        # --- Reporting ---
        if has_sig_field and has_byterange:
            # Signature exists — this is good
            if has_cert:
                # Has certificate data too — strong signature
                pass  # No anomaly — signed and certified
            else:
                anomalies.append(AnomalyFeature(
                    type="Incomplete Digital Signature",
                    description=(
                        "A digital signature field exists in this PDF, but no embedded certificate "
                        "data was found. The signature may be a visual-only stamp without cryptographic "
                        "backing, which does not prove authenticity."
                    ),
                    risk_level="Medium"
                ))
        elif is_likely_official and not has_sig_field:
            # Looks like an official doc but has no signature at all
            anomalies.append(AnomalyFeature(
                type="Missing Digital Signature",
                description=(
                    "This document appears to be an official bank/financial statement but contains "
                    "no digital signature. Genuine bank-generated PDFs typically include a "
                    "cryptographic digital signature for authenticity verification. "
                    "Its absence is a red flag for potential forgery."
                ),
                risk_level="Medium"
            ))

        # --- Check 3: Multiple %%EOF markers (incremental updates that may strip signatures) ---
        eof_count = pdf_bytes.count(b"%%EOF")
        if eof_count > 2 and has_sig_field:
            anomalies.append(AnomalyFeature(
                type="Signature Integrity Concern",
                description=(
                    f"This PDF has {eof_count} revision layers (%%EOF markers) alongside a digital "
                    "signature. Multiple revisions after signing can indicate the document was modified "
                    "post-signature, potentially invalidating the signature's guarantee."
                ),
                risk_level="High"
            ))

    except Exception as e:
        anomalies.append(AnomalyFeature(
            type="Signature Validation Error",
            description=f"Could not validate digital signatures: {str(e)}",
            risk_level="Low"
        ))

    return anomalies
