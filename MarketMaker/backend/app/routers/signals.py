from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.db import SessionLocal
from app.models import Signal
from app.schemas import SignalOut

router = APIRouter(prefix="/api/v1/signals", tags=["signals"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("", response_model=list[SignalOut])
def list_signals(
    symbol: str | None = Query(None),
    source: str | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    q = db.query(Signal).order_by(Signal.created_at.desc())
    if symbol:
        q = q.filter(Signal.symbol == symbol.upper())
    if source:
        q = q.filter(Signal.source == source.upper())
    return q.limit(limit).all()

