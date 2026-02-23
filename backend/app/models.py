"""
Database models for the MarketMaker application.
Defines the schema for Signals (market events) and Alerts (notifications).
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Float, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from app.db import Base
from sqlalchemy.dialects.postgresql import JSONB

# Helper function to get current UTC time, ensuring timezone awareness
def now_utc() -> datetime:
    # Now, we get the current time.
    # We explicitly enforce UTC to avoid timezone headaches later.
    return datetime.now(timezone.utc)

class Signal(Base):
    """
    Represents a market signal or event detected by the system.
    Stores both raw data and processed ML features.
    """
    __tablename__ = "signals"

    # Now, we define the Primary Key.
    # We use UUIDs (String 36) instead of Integers.
    # This allows for distributed ID generation and prevents ID enumeration attacks.
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    # Now, we index the timestamp. This is crucial for time-series queries (e.g., "Give me last 24h of signals").
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, index=True)

    # Metadata about the signal source and type
    source: Mapped[str] = mapped_column(String(32), index=True)
    symbol: Mapped[str] = mapped_column(String(32), index=True)
    kind: Mapped[str] = mapped_column(String(64), index=True)
    direction: Mapped[str] = mapped_column(String(8), default="N/A")

    # Financial value associated with the signal (if applicable)
    notional: Mapped[float] = mapped_column(Float, default=0.0)

    # Now, we use Postgres-native JSONB.
    # This allows us to store unstructured data ('raw') and semi-structured data ('features')
    # without needing strict schema migrations for every new field.
    raw: Mapped[dict] = mapped_column(JSONB, default=dict)
    features: Mapped[dict] = mapped_column(JSONB, default=dict)

    # Machine Learning inference results
    anomaly_score: Mapped[float] = mapped_column(Float, default=0.0)
    class_label: Mapped[str] = mapped_column(String(64), default="unknown")
    class_confidence: Mapped[float] = mapped_column(Float, default=0.0)

class Alert(Base):
    """
    Represents a notification generated for the user based on significant signals.
    """
    __tablename__ = "alerts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, index=True)

    symbol: Mapped[str] = mapped_column(String(32), index=True)
    # Severity level (e.g., "INFO", "WARNING", "CRITICAL")
    severity: Mapped[str] = mapped_column(String(16), index=True)
    title: Mapped[str] = mapped_column(String(128))
    body: Mapped[str] = mapped_column(String)

    # List of related Signal IDs that triggered this alert, stored as a JSON array
    signal_ids: Mapped[list[str]] = mapped_column(JSONB, default=list)