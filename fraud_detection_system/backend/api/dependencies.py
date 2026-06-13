from sqlalchemy.orm import Session
from fastapi import Depends, HTTPException
from core.database import get_db

# Re-export get_db for easier access
__all__ = ["get_db"]
