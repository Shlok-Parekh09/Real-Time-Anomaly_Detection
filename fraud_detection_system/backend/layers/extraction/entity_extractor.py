import re
from typing import Dict, Any, Optional

class EntityExtractor:
    """
    Extracts key entities (Name, PAN, Aadhaar, etc.) from document text.
    """
    
    def extract(self, text: str, classification: str) -> Dict[str, Any]:
        """
        Extract entities based on document type and text content.
        """
        entities = {
            "name": self._extract_name(text),
            "dob": self._extract_dob(text),
            "pan": self._extract_pan(text),
            "aadhaar": self._extract_aadhaar(text),
            "address": self._extract_address(text),
            "account_number": self._extract_account_number(text),
            "phone": self._extract_phone(text),
            "email": self._extract_email(text)
        }
        
        # Type-specific extraction
        if classification == "Payslip":
            entities.update({
                "salary": self._extract_salary(text),
                "employer": self._extract_employer(text)
            })
        elif classification == "Property Record":
            entities.update({
                "property_id": self._extract_property_id(text),
                "property_owner": self._extract_property_owner(text)
            })
            
        return entities

    def _extract_name(self, text: str) -> Optional[str]:
        # Heuristic: Look for "Name:" or "Employee Name:"
        match = re.search(r"(?i)(?:name|employee\s+name|customer\s+name)[:\s]+([A-Z\s]{3,30})", text)
        if match:
            return match.group(1).strip()
        return None

    def _extract_dob(self, text: str) -> Optional[str]:
        # Pattern: DD/MM/YYYY or similar
        match = re.search(r"(?i)(?:dob|date\s+of\s+birth)[:\s]+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})", text)
        if match:
            return match.group(1).strip()
        return None

    def _extract_pan(self, text: str) -> Optional[str]:
        match = re.search(r"\b[A-Z]{5}[0-9]{4}[A-Z]{1}\b", text)
        return match.group(0) if match else None

    def _extract_aadhaar(self, text: str) -> Optional[str]:
        match = re.search(r"\b\d{4}\s\d{4}\s\d{4}\b", text)
        return match.group(0) if match else None

    def _extract_account_number(self, text: str) -> Optional[str]:
        match = re.search(r"(?i)(?:account\s+number|ac\s+no|a/c\s+no)[:\s]+([0-9-]{9,18})", text)
        if match:
            return match.group(1).strip()
        return None

    def _extract_phone(self, text: str) -> Optional[str]:
        match = re.search(r"\b(?:\+91|0)?[6789]\d{9}\b", text)
        return match.group(0) if match else None

    def _extract_email(self, text: str) -> Optional[str]:
        match = re.search(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", text)
        return match.group(0) if match else None

    def _extract_address(self, text: str) -> Optional[str]:
        # Very basic heuristic for address
        match = re.search(r"(?i)address[:\s]+(.*?)(?:\n\n|\r\n\r\n|\.\s|\n[A-Z])", text, re.DOTALL)
        if match:
            return match.group(1).replace("\n", " ").strip()
        return None

    def _extract_salary(self, text: str) -> Optional[float]:
        # Look for "Net Pay" or similar
        match = re.search(r"(?i)(?:net\s+pay|gross\s+salary|net\s+salary)[:\s]+(?:rs\.?|inr)?\s*([\d,.]+)", text)
        if match:
            try:
                val = match.group(1).replace(",", "")
                return float(val)
            except:
                pass
        return None

    def _extract_employer(self, text: str) -> Optional[str]:
        # Look for "Employer:" or "Company:"
        match = re.search(r"(?i)(?:employer|company|organization)[:\s]+([A-Z\s]{3,40})", text)
        if match:
            return match.group(1).strip()
        return None

    def _extract_property_id(self, text: str) -> Optional[str]:
        match = re.search(r"(?i)(?:property\s+id|survey\s+no|khasra\s+no)[:\s]+([A-Z0-9/-]{3,20})", text)
        return match.group(1).strip() if match else None

    def _extract_property_owner(self, text: str) -> Optional[str]:
        match = re.search(r"(?i)(?:owner|title\s+holder)[:\s]+([A-Z\s]{3,30})", text)
        return match.group(1).strip() if match else None

entity_extractor = EntityExtractor()
