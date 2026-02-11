from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db import SessionLocal
from app.core.ingest import refit_models_from_db

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
    
@router.post("/refit")
def refit(db: Session = Depends(get_db)):
    refit_models_from_db(db)
    return{"ok": True}