import json
from pathlib import Path
from typing import List, Dict, Any, Optional

class TrustedRepository:
    """
    Manages the storage and retrieval of feature vectors for high-trust investigations.
    """
    
    def __init__(self, repo_path: str = "trusted_repository/data.json"):
        self.repo_path = Path(repo_path)
        self.repo_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.repo_path.exists():
            self.repo_path.write_text(json.dumps([]))

    def add_entry(self, features: Dict[str, Any], metadata: Dict[str, Any]):
        """
        Adds a new trusted entry to the repository.
        """
        data = json.loads(self.repo_path.read_text())
        investigation_id = metadata.get("investigation_id")
        if investigation_id:
            data = [
                entry for entry in data
                if entry.get("metadata", {}).get("investigation_id") != investigation_id
            ]
        data.append({
            "features": features,
            "metadata": metadata
        })
        self.repo_path.write_text(json.dumps(data))

    def get_all_features(self) -> List[Dict[str, Any]]:
        """
        Returns all feature vectors in the repository.
        """
        return json.loads(self.repo_path.read_text())

repository_manager = TrustedRepository()
