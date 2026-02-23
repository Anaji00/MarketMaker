from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.db import SessionLocal
from app.models import Alert
from app.schemas import AlertOut

router = APIRouter(prefix="/api/v1/alerts", tags=["alerts"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("", response_model=list[AlertOut])
def list_alerts(
    symbol: str | None = Query(None),
    limit: int = Query(100, ge=1, le=200),
    db: Session = Depends(get_db),
):
    q = db.query(Alert).order_by(Alert.created_at.desc())
    if symbol:
        q = q.filter(Alert.symbol == symbol.upper())
    return q.limit(limit).all()