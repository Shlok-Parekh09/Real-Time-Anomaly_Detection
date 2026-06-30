import re
import json
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# Verhoeff algorithm tables for Aadhaar checksum validation
VERHOEFF_D = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
    [1, 2, 3, 4, 0, 6, 7, 8, 9, 5],
    [2, 3, 4, 0, 1, 7, 8, 9, 5, 6],
    [3, 4, 0, 1, 2, 8, 9, 5, 6, 7],
    [4, 0, 1, 2, 3, 9, 5, 6, 7, 8],
    [5, 9, 8, 7, 6, 0, 4, 3, 2, 1],
    [6, 5, 9, 8, 7, 1, 0, 4, 3, 2],
    [7, 6, 5, 9, 8, 2, 1, 0, 4, 3],
    [8, 7, 6, 5, 9, 3, 2, 1, 0, 4],
    [9, 8, 7, 6, 5, 4, 3, 2, 1, 0]
]

VERHOEFF_P = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
    [1, 5, 7, 6, 2, 8, 3, 0, 9, 4],
    [5, 8, 0, 3, 7, 9, 6, 1, 4, 2],
    [8, 9, 1, 6, 0, 4, 3, 5, 2, 7],
    [9, 4, 5, 3, 1, 2, 6, 8, 7, 0],
    [4, 2, 8, 6, 5, 7, 3, 9, 0, 1],
    [2, 7, 9, 3, 8, 0, 6, 4, 1, 5],
    [7, 0, 4, 6, 9, 1, 3, 2, 5, 8]
]

def validate_verhoeff(num_str: str) -> bool:
    """Validate Verhoeff checksum (used for Aadhaar)"""
    try:
        digits = [int(c) for c in num_str if c.isdigit()]
        if len(digits) != 12:
            return False
        c = 0
        for i, item in enumerate(reversed(digits)):
            c = VERHOEFF_D[c][VERHOEFF_P[i % 8][item]]
        return c == 0
    except Exception:
        return False

class EntityExtractor:
    """
    Extracts key entities (Name, PAN, Aadhaar, DOB, Gender, Address, Father's Name, etc.)
    from raw document OCR text using high-accuracy regex heuristics, validation rules,
    and Gemma 4 LLM synthesis. Prioritizes correctness over completeness.
    """
    
    def extract(self, text: str, classification: str) -> Dict[str, Any]:
        """
        Runs the extraction pipeline: Heuristic regex parsing combined with LLM extraction,
        followed by strict validation and reconciliation.
        """
        # 1. Base regex heuristics
        heuristics = {
            "name": None,
            "dob": self._extract_dob(text),
            "pan": self._extract_pan(text),
            "aadhaar": self._extract_aadhaar(text),
            "address": self._extract_address(text),
            "gender": self._extract_gender(text),
            "father_name": None,
            "account_number": self._extract_account_number(text),
            "phone": self._extract_phone(text),
            "email": self._extract_email(text),
            "salary": None,
            "employer": None,
            "property_id": None,
            "property_owner": None
        }
        
        # Classification-specific heuristics
        if classification == "PAN":
            pan_details = self._extract_pan_details(text)
            heuristics["name"] = pan_details["name"]
            heuristics["father_name"] = pan_details["father_name"]
        elif classification == "Aadhaar":
            heuristics["name"] = self._extract_aadhaar_name(text)
            heuristics["father_name"] = self._extract_father_name(text)
        else:
            heuristics["name"] = self._extract_name(text, classification)
            heuristics["father_name"] = self._extract_father_name(text)
            
        if classification == "Payslip":
            heuristics["salary"] = self._extract_salary(text)
            heuristics["employer"] = self._extract_employer(text)
        elif classification == "Property Record":
            heuristics["property_id"] = self._extract_property_id(text)
            heuristics["property_owner"] = self._extract_property_owner(text)
            
        # 2. Query AI parser (local Gemma or Gemini enhanced mode) for structured extraction
        ai_extracted = self._call_ai(text, classification)
        
        # 3. Reconcile and Validate
        reconciled = self._reconcile_and_validate(heuristics, ai_extracted, classification)
        
        # Ensure all None values default to "-" for clean UI rendering
        for k, v in list(reconciled.items()):
            if v is None:
                reconciled[k] = "-"
                
        return reconciled

    def _reconcile_and_validate(self, heur: Dict[str, Any], ai: Dict[str, Any], classification: str) -> Dict[str, Any]:
        """
        Reconciles heuristics and AI extracted fields. Validates each field strictly.
        Prioritizes correctness over completeness: returns None if values are incorrect/invalid.
        """
        result = {}
        
        # Validate PAN
        pan_candidate = self._validate_and_correct_pan(ai.get("pan") or heur.get("pan"))
        result["pan"] = pan_candidate
        
        # Validate Aadhaar
        aadhaar_candidate = self._validate_and_correct_aadhaar(ai.get("aadhaar") or heur.get("aadhaar"))
        result["aadhaar"] = aadhaar_candidate
        
        # Validate DOB / Date
        dob_candidate = self._validate_date(ai.get("dob") or heur.get("dob"))
        result["dob"] = dob_candidate
        
        # Validate Gender
        gender_candidate = self._validate_gender(ai.get("gender") or heur.get("gender"))
        result["gender"] = gender_candidate
        
        # Validate Name
        ai_name = self._validate_name(ai.get("name"))
        heur_name = self._validate_name(heur.get("name"))
        if ai_name and heur_name:
            if len(ai_name.split()) >= len(heur_name.split()):
                result["name"] = ai_name
            else:
                result["name"] = heur_name
        else:
            result["name"] = ai_name or heur_name
            
        # Validate Father's Name
        ai_father = self._validate_name(ai.get("father_name"))
        heur_father = self._validate_name(heur.get("father_name"))
        if ai_father and heur_father:
            if len(ai_father.split()) >= len(heur_father.split()):
                result["father_name"] = ai_father
            else:
                result["father_name"] = heur_father
        else:
            result["father_name"] = ai_father or heur_father
            
        # Validate Address
        ai_addr = ai.get("address")
        heur_addr = heur.get("address")
        if ai_addr and len(str(ai_addr).strip()) > 10:
            result["address"] = str(ai_addr).strip()
        elif heur_addr and len(str(heur_addr).strip()) > 10:
            result["address"] = str(heur_addr).strip()
        else:
            result["address"] = None

        # Validate Account Number
        acc_cand = ai.get("account_number") or heur.get("account_number")
        if acc_cand:
            acc_clean = re.sub(r'[^0-9-]', '', str(acc_cand)).strip()
            if 9 <= len(acc_clean) <= 18:
                result["account_number"] = acc_clean
            else:
                result["account_number"] = None
        else:
            result["account_number"] = None

        # Validate Phone
        phone_cand = ai.get("phone") or heur.get("phone")
        if phone_cand:
            phone_clean = re.sub(r'\D', '', str(phone_cand))
            if len(phone_clean) >= 10:
                last_10 = phone_clean[-10:]
                if last_10[0] in "6789":
                    result["phone"] = f"+91 {last_10}"
                else:
                    result["phone"] = None
            else:
                result["phone"] = None
        else:
            result["phone"] = None

        # Validate Email
        email_cand = ai.get("email") or heur.get("email")
        if email_cand and re.match(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$", str(email_cand).strip()):
            result["email"] = str(email_cand).strip().lower()
        else:
            result["email"] = None

        # Classification specific validations
        if classification == "Payslip":
            sal_cand = ai.get("salary") or heur.get("salary")
            if sal_cand:
                try:
                    val = float(str(sal_cand).replace(",", "").replace("Rs.", "").replace("INR", "").strip())
                    if val > 0:
                        result["salary"] = val
                    else:
                        result["salary"] = None
                except:
                    result["salary"] = None
            else:
                result["salary"] = None
                
            emp_cand = ai.get("employer") or heur.get("employer")
            result["employer"] = self._validate_name(emp_cand, is_employer=True)
            
        elif classification == "Property Record":
            prop_id = ai.get("property_id") or heur.get("property_id")
            if prop_id and len(str(prop_id).strip()) >= 3:
                result["property_id"] = str(prop_id).strip().upper()
            else:
                result["property_id"] = None
                
            prop_owner = ai.get("property_owner") or heur.get("property_owner")
            result["property_owner"] = self._validate_name(prop_owner)
            
        return result

    def _validate_and_correct_pan(self, pan: Optional[str]) -> Optional[str]:
        if not pan or str(pan).strip() in ["", "-", "None", "null"]:
            return None
        cleaned = re.sub(r'[^A-Za-z0-9]', '', str(pan)).upper().strip()
        
        if len(cleaned) != 10:
            match = re.search(r'[A-Z0-9]{10}', cleaned)
            if match:
                cleaned = match.group(0)
            else:
                return None
                
        chars = list(cleaned)
        letter_corrections = {'0': 'O', '1': 'I', '5': 'S', '8': 'B', '2': 'Z'}
        digit_corrections = {'O': '0', 'I': '1', 'S': '5', 'B': '8', 'Z': '2', 'G': '6', 'T': '7'}
        
        for i in range(5):
            if chars[i].isdigit():
                chars[i] = letter_corrections.get(chars[i], chars[i])
        for i in range(5, 9):
            if chars[i].isalpha():
                chars[i] = digit_corrections.get(chars[i], chars[i])
        if chars[9].isdigit():
            chars[9] = letter_corrections.get(chars[9], chars[9])
            
        corrected = "".join(chars)
        if re.match(r'^[A-Z]{5}[0-9]{4}[A-Z]$', corrected):
            return corrected
        return None

    def _validate_and_correct_aadhaar(self, aadhaar: Optional[str]) -> Optional[str]:
        if not aadhaar or str(aadhaar).strip() in ["", "-", "None", "null"]:
            return None
        cleaned = re.sub(r'\D', '', str(aadhaar)).strip()
        if len(cleaned) != 12:
            return None
        if validate_verhoeff(cleaned):
            return f"{cleaned[:4]} {cleaned[4:8]} {cleaned[8:]}"
        return None

    def _validate_date(self, date_val: Optional[str]) -> Optional[str]:
        if not date_val or str(date_val).strip() in ["", "-", "None", "null"]:
            return None
        match = re.match(r"^(\d{1,2})[/.-](\d{1,2})[/.-](\d{4})$", str(date_val).strip())
        if match:
            d, m, y = int(match.group(1)), int(match.group(2)), int(match.group(3))
            if 1 <= m <= 12 and 1900 <= y <= 2028:
                days_in_month = [0, 31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
                if (y % 4 == 0 and y % 100 != 0) or (y % 400 == 0):
                    days_in_month[2] = 29
                if 1 <= d <= days_in_month[m]:
                    return f"{d:02d}/{m:02d}/{y:04d}"
        return None

    def _validate_gender(self, gender: Optional[str]) -> Optional[str]:
        if not gender:
            return None
        g_clean = str(gender).strip().lower()
        if "female" in g_clean or g_clean == "f":
            return "Female"
        elif "male" in g_clean or g_clean == "m":
            return "Male"
        elif "trans" in g_clean or "tg" in g_clean:
            return "Transgender"
        return None

    def _validate_name(self, name: Optional[str], is_employer: bool = False) -> Optional[str]:
        if not name or str(name).strip() in ["", "-", "None", "null"]:
            return None
        allowed_pattern = r'[^A-Za-z\s\.\&]' if is_employer else r'[^A-Za-z\s\.]'
        cleaned = re.sub(allowed_pattern, '', str(name)).strip()
        cleaned = re.sub(r'\s+', ' ', cleaned)
        
        forbidden = {
            "INCOME", "TAX", "DEPARTMENT", "GOVT", "INDIA", "CARD", "SIGNATURE", 
            "ACCOUNT", "PERMANENT", "NUMBER", "PHOTO", "FATHER", "MOTHER", 
            "INCOMETAX", "DEPT", "PRINT", "DIGITAL", "SECURITY", "AUTHENTIC", 
            "VERIFIED", "ANOBIS", "GOVERNMENT", "UNIQUE", "AUTHORITY", "UNION", 
            "REGISTRATION", "MALE", "FEMALE", "SIGN", "HOLDER", "DEPARTMENTOF", "OF",
            "GOVERNMENTOFINDIA", "भारत", "सरकार", "आयकर", "विभाग", "जन्म तिथि", "जन्म"
        }
        
        words = cleaned.split()
        filtered_words = [w for w in words if w.upper() not in forbidden]
        
        if len(filtered_words) >= 1:
            reconstructed = " ".join(filtered_words)
            if len(reconstructed.replace(" ", "")) >= 3:
                return reconstructed.upper()
        return None

    def _extract_pan_details(self, text: str) -> Dict[str, Optional[str]]:
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        
        ignore_keywords = {
            "INCOME", "TAX", "DEPARTMENT", "GOVT", "INDIA", "CARD", "SIGNATURE", 
            "ACCOUNT", "PERMANENT", "NUMBER", "UTY", "PHOTO", "FATHER", "MOTHER", 
            "NAME", "INCOMETAX", "DEPT", "PRINT", "GANDHI", "ROAD", "NEW", "DELHI", 
            "DIGITAL", "SECURITY", "AUTHENTIC", "VERIFIED", "ANOBIS", "OF", "AND", 
            "भारत", "सरकार", "आयकर", "विभाग", "MALE", "FEMALE", "SIGN", "HOLDER", "DEPARTMENTOF"
        }
        
        stop_idx = len(lines)
        for i, line in enumerate(lines):
            if re.search(r"\b\d{2}[/.-]\d{2}[/.-]\d{4}\b", line) or re.search(r"\b[A-Z]{5}[0-9]{4}[A-Z]\b", line.upper()):
                stop_idx = i
                break
                
        lines_before_stop = lines[:stop_idx]
        
        name_groups = []
        current_group = []
        for line in lines_before_stop:
            cleaned = re.sub(r'[^A-Z\s]', '', line.upper()).strip()
            words = [w for w in cleaned.split() if w not in ignore_keywords and len(w) >= 3]
            if words:
                current_group.append(" ".join(words))
            else:
                if current_group:
                    name_groups.append(" ".join(current_group))
                    current_group = []
        if current_group:
            name_groups.append(" ".join(current_group))
            
        valid_groups = []
        for g in name_groups:
            g_clean = " ".join([w for w in g.split() if w not in ignore_keywords]).strip()
            if len(g_clean.replace(" ", "")) >= 3:
                valid_groups.append(g_clean)
                
        return {
            "name": valid_groups[0] if len(valid_groups) > 0 else None,
            "father_name": valid_groups[1] if len(valid_groups) > 1 else None
        }

    def _extract_aadhaar_name(self, text: str) -> Optional[str]:
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        
        dob_idx = -1
        for i, line in enumerate(lines):
            if re.search(r"(?i)(?:dob|yob|birth|जन्म|तिथि|वर्ष)", line):
                dob_idx = i
                break
                
        if dob_idx > 0:
            for idx in range(dob_idx - 1, -1, -1):
                cand = lines[idx]
                cleaned = re.sub(r'[^A-Za-z\s\.]', '', cand).strip()
                words = cleaned.split()
                ignore_words = {"GOVERNMENT", "INDIA", "UNIQUE", "AUTHORITY", "GOVT", "UNION", "REGISTRATION"}
                filtered_words = [w for w in words if w.upper() not in ignore_words]
                if filtered_words and len("".join(filtered_words)) >= 3:
                    return " ".join(filtered_words)
                    
        for line in lines:
            match = re.search(r"(?i)(?:name|नाम|नाम\s*[:\/])\s*[:\/]?\s*([A-Za-z\s\.]+)", line)
            if match:
                name_cand = match.group(1).strip()
                if len(name_cand.replace(" ", "")) >= 3:
                    return name_cand
                    
        return None

    def _extract_name(self, text: str, classification: str) -> Optional[str]:
        if classification == "PAN":
            details = self._extract_pan_details(text)
            if details["name"]:
                return details["name"]
        elif classification == "Aadhaar":
            name = self._extract_aadhaar_name(text)
            if name:
                return name
                            
        match = re.search(r"(?i)(?:name|employee\s+name|customer\s+name)[:\s]+([A-Z\s\.]{3,30})", text)
        if match:
            return match.group(1).strip()
        return None

    def _extract_father_name(self, text: str) -> Optional[str]:
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        for i, line in enumerate(lines):
            if re.search(r"(?i)(?:father'?s\s+name|पिता\s*का\s*नाम)", line):
                for offset in [1, 2]:
                    if i + offset < len(lines):
                        candidate = lines[i + offset].strip()
                        if re.match(r"^[A-Z\s\.]+$", candidate) and len(candidate.replace(" ", "")) >= 3:
                            if not any(w in candidate for w in ["GOVT", "INDIA", "INCOME", "TAX", "DEPARTMENT"]):
                                return candidate
        return None

    def _extract_dob(self, text: str) -> Optional[str]:
        match = re.search(r"\b(\d{2})[/.-](\d{2})[/.-](\d{4})\b", text)
        if match:
            dd, mm, yyyy = match.groups()
            return f"{dd}/{mm}/{yyyy}"
        match_yob = re.search(r"(?i)(?:yob|year\s+of\s+birth|जन्म\s+का\s+वर्ष|जन्म\s+तिथि)[:\s]*(\d{4})", text)
        if match_yob:
            return f"01/01/{match_yob.group(1)}"
        return None

    def _extract_gender(self, text: str) -> Optional[str]:
        if re.search(r"(?i)\b(?:female|महिला|स्त्री)\b", text):
            return "Female"
        elif re.search(r"(?i)\b(?:male|पुरुष|मर्द)\b", text):
            return "Male"
        elif re.search(r"(?i)\b(?:transgender|तीसरा लिंग)\b", text):
            return "Transgender"
        return None

    def _extract_pan(self, text: str) -> Optional[str]:
        match = re.search(r"\b[A-Z0-9]{10}\b", text, re.IGNORECASE)
        if match:
            return match.group(0)
        return None

    def _extract_aadhaar(self, text: str) -> Optional[str]:
        match = re.search(r"\b\d{4}[\s-]\d{4}[\s-]\d{4}\b", text)
        if match:
            return match.group(0)
        match_raw = re.search(r"\b\d{12}\b", text)
        if match_raw:
            return match_raw.group(0)
        return None

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
        lines = text.split("\n")
        for i, line in enumerate(lines):
            l = line.strip()
            if re.search(r"(?i)\b(?:address|पता|c/o|s/o|d/o|w/o)\b\s*[:/]?\s*", l):
                addr_lines = []
                first_line = re.sub(r"(?i)\b(?:address|पता|c/o|s/o|d/o|w/o)\b\s*[:/]?\s*", "", l).strip()
                if first_line:
                    addr_lines.append(first_line)
                for j in range(i + 1, min(i + 5, len(lines))):
                    next_l = lines[j].strip()
                    if not next_l:
                        break
                    if re.search(r"\b\d{4}\s\d{4}\s\d{4}\b", next_l) or re.search(r"(?i)(?:unique|authority|government|signature|www\.)", next_l):
                        break
                    addr_lines.append(next_l)
                if addr_lines:
                    return " ".join(addr_lines).strip()
                    
        match = re.search(r"(?i)address[:\s]+(.*?)(?:\n\n|\r\n\r\n|\.\s|\n[A-Z])", text, re.DOTALL)
        if match:
            return match.group(1).replace("\n", " ").strip()
        return None

    def _extract_salary(self, text: str) -> Optional[float]:
        match = re.search(r"(?i)(?:net\s+pay|gross\s+salary|net\s+salary)[:\s]+(?:rs\.?|inr)?\s*([\d,.]+)", text)
        if match:
            try:
                val = match.group(1).replace(",", "")
                return float(val)
            except:
                pass
        return None

    def _extract_employer(self, text: str) -> Optional[str]:
        match = re.search(r"(?i)(?:employer|company|organization)[:\s]+([A-Z\s\&]{3,40})", text)
        if match:
            return match.group(1).strip()
        return None

    def _extract_property_id(self, text: str) -> Optional[str]:
        match = re.search(r"(?i)(?:property\s+id|survey\s+no|khasra\s+no)[:\s]+([A-Z0-9/-]{3,20})", text)
        return match.group(1).strip() if match else None

    def _extract_property_owner(self, text: str) -> Optional[str]:
        match = re.search(r"(?i)(?:owner|title\s+holder)[:\s]+([A-Z\s\.]{3,30})", text)
        return match.group(1).strip() if match else None

    def _call_ai(self, text: str, classification: str) -> Dict[str, Any]:
        """
        Leverages ai_provider_manager to extract structured entities.
        Provides a highly structured schema and strict instruction.
        """
        from core.ai_provider_manager import ai_provider_manager
        
        system_prompt = (
            "You are a structured forensic document entity parser. Extract fields exactly as they appear in the OCR text. "
            "If a field cannot be confidently extracted, is missing, or is illegible, default it strictly to null. "
            "Never guess, extrapolate, or fabricate any identifiers, names, or addresses under any circumstances."
        )
        text_excerpt = text[:8000]
        if len(text) > len(text_excerpt):
            text_excerpt += "\n\n[OCR text truncated for structured entity parsing; deterministic regex parsers inspect the full text.]"

        prompt = f"""
Analyze the raw forensic OCR text below from a document classified as {classification}. 
Extract key identity and document entities and output ONLY a valid JSON object matching this schema:
{{
  "name": null or "Holder's Full Name (normalized, uppercase)",
  "dob": null or "Date of Birth (format strictly: DD/MM/YYYY)",
  "pan": null or "10-character alphanumeric PAN (exactly uppercase, e.g. ABCDE1234F)",
  "aadhaar": null or "12-digit Aadhaar Number (exactly 12 digits, e.g. 123456789012)",
  "address": null or "Normalized Address",
  "gender": null or "Male/Female/Transgender",
  "father_name": null or "Father's Full Name",
  "account_number": null or "Bank Account Number",
  "phone": null or "Phone Number",
  "email": null or "Email Address",
  "salary": null or float (e.g. 45000.0, only for Payslip),
  "employer": null or "Employer Company Name (only for Payslip)",
  "property_id": null or "Property ID / Survey Number (only for Property Record)",
  "property_owner": null or "Property Owner Name (only for Property Record)"
}}
Verification guidelines:
- If a field is not explicitly present in the text, return null for it.
- Never guess or generate random values. If you are unsure, set the field to null.
- Return ONLY raw JSON content. Do not include markdown code block syntax (like ```json) or explanation.

OCR Text:
{text_excerpt}
"""
        try:
            return ai_provider_manager.generate_json(
                system_prompt=system_prompt,
                user_prompt=prompt,
                temperature=0.1,
                max_tokens=700,
                timeout=45.0
            )
        except Exception as e:
            logger.error(f"Ollama/Gemini entity extraction call failed: {e}")
            return {}

entity_extractor = EntityExtractor()
