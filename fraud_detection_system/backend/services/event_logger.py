from sqlalchemy.orm import Session
from models.database import InvestigationEvent
from typing import Any, Optional

def log_event(
    db: Session,
    investigation_id: str,
    event_type: str,
    message: str,
    metadata: Optional[Any] = None
) -> InvestigationEvent:
    event = InvestigationEvent(
        investigation_id=investigation_id,
        event_type=event_type,
        message=message,
        metadata_json=metadata
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event
