import os
import shutil
from pathlib import Path
from fastapi import UploadFile
from sqlalchemy.orm import Session
from models.database import Document
from core.config import settings

def save_upload_file(upload_file: UploadFile, investigation_id: str) -> str:
    """Saves an uploaded file to the investigation's directory after sanitizing the filename."""
    investigation_dir = Path(settings.UPLOAD_DIR) / investigation_id
    investigation_dir.mkdir(parents=True, exist_ok=True)
    
    # Extract only the base name to prevent directory traversal
    import os
    base_name = os.path.basename(upload_file.filename)
    # Further strip any traversal characters
    safe_filename = base_name.replace("..", "").replace("/", "").replace("\\", "")
    
    file_path = investigation_dir / safe_filename
    with file_path.open("wb") as buffer:
        shutil.copyfileobj(upload_file.file, buffer)
    
    return str(file_path)

def add_document_to_db(
    db: Session,
    investigation_id: str,
    filename: str,
    file_type: str,
    storage_path: str
) -> Document:
    document = Document(
        investigation_id=investigation_id,
        filename=filename,
        file_type=file_type,
        storage_path=storage_path
    )
    db.add(document)
    db.commit()
    db.refresh(document)
    return document
