import re
from typing import List, Optional
from thefuzz import fuzz
from pyjarowinkler import distance as jw_distance
import Levenshtein

class EntityNormalizer:
    """
    Provides normalization and fuzzy matching for identity and financial entities.
    """
    
    TITLES = [r"\bmr\.?\b", r"\bms\.?\b", r"\bmrs\.?\b", r"\bdr\.?\b", r"\badv\.?\b", r"\bprof\.?\b"]
    ADDRESS_MAP = {
        "st": "street",
        "rd": "road",
        "h.no": "house no",
        "apt": "apartment",
        "flt": "flat",
        "blvd": "boulevard",
        "sq": "square"
    }
    EMPLOYER_MAP = {
        "pvt": "private",
        "ltd": "limited",
        "corp": "corporation",
        "inc": "incorporated"
    }

    def normalize_name(self, name: str) -> str:
        if not name: return ""
        name = name.lower().strip()
        # Remove titles
        for title in self.TITLES:
            name = re.sub(title, "", name)
        # Remove special chars and extra spaces
        name = re.sub(r"[^a-z\s]", " ", name)
        name = " ".join(name.split())
        return name

    def normalize_address(self, address: str) -> str:
        if not address: return ""
        address = address.lower().strip()
        # Remove punctuation
        address = re.sub(r"[^a-z0-9\s]", " ", address)
        # Standardize suffixes
        tokens = address.split()
        standardized = [self.ADDRESS_MAP.get(t, t) for t in tokens]
        return " ".join(standardized)

    def normalize_employer(self, employer: str) -> str:
        if not employer: return ""
        employer = employer.lower().strip()
        # Remove punctuation
        employer = re.sub(r"[^a-z0-9\s]", " ", employer)
        # Standardize suffixes
        tokens = employer.split()
        standardized = [self.EMPLOYER_MAP.get(t, t) for t in tokens]
        return " ".join(standardized)

    def calculate_similarity(self, s1: str, s2: str, method: str = "jaro_winkler") -> float:
        """
        Calculates similarity between two strings using specified method.
        Returns score between 0.0 and 1.0.
        """
        if not s1 or not s2:
            return 0.0
            
        if method == "jaro_winkler":
            return Levenshtein.jaro_winkler(s1, s2)
        elif method == "levenshtein":
            return Levenshtein.ratio(s1, s2)
        elif method == "token_set_ratio":
            return fuzz.token_set_ratio(s1, s2) / 100.0
        return 0.0

    def is_match(self, s1: str, s2: str, threshold: float = 0.92, method: str = "jaro_winkler") -> bool:
        return self.calculate_similarity(s1, s2, method) >= threshold

    def handle_abbreviation(self, short_name: str, full_name: str) -> float:
        """
        Handles cases like 'R. Sharma' vs 'Rahul Sharma'.
        If initial matches and last name is a high match, returns high similarity.
        """
        short_parts = short_name.split()
        full_parts = full_name.split()
        
        if len(short_parts) < 2 or len(full_parts) < 2:
            return 0.0
            
        # Check if first part of short name is an initial of first part of full name
        if len(short_parts[0]) == 1 or (len(short_parts[0]) == 2 and short_parts[0][1] == "."):
            if short_parts[0][0] == full_parts[0][0]:
                # Compare last parts (usually surnames)
                last_sim = self.calculate_similarity(short_parts[-1], full_parts[-1])
                if last_sim >= 0.95:
                    return 0.96 # High match for abbreviation
                    
        return 0.0

normalizer = EntityNormalizer()
