"""
Pydantic schemas for the MarketMaker API.
Defines the data validation and serialization rules for API responses.
"""
from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel

class SignalOut(BaseModel):
    """
    Schema for returning Signal data.
    This acts as a Data Transfer Object (DTO).
    It decouples the internal Database Model from the external API Contract.
    """
    id: str
    created_at: datetime
    source: str
    symbol: str
    kind: str
    direction: str
    notional: float

    # Updated to match DB model naming and type (JSONB -> dict)
    raw: dict
    features: dict

    anomaly_score: float
    class_label: str
    class_confidence: float


class AlertOut(BaseModel):
    """
    Schema for returning Alert data.
    """
    id: str
    created_at: datetime
    symbol: str
    severity: str
    title: str
    body: str

    # Note: The database model stores 'signal_ids' as a list of strings.
    # This field is typed as str, implying a different format (e.g. comma-separated).
    signal_ids: str