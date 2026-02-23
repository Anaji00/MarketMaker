from __future__ import annotations

import logging
import json
from sqlalchemy.orm import Session
import asyncio
from app.core.normalize import NormalizedSignal
from app.core.features import stock_features, options_features, features_json
from app.core.scoring import ScoringEngine
from app.models import Signal, Alert
from app.config import settings

from app.services.stocks_yf import fetch_recent_stock_bars
from app.services.options_yf import fetch_options_snapshot
from app.services.polymarket_gamma import fetch_events, extract_market_signals_from_event
from app.services.fmp_adapter import FMPAdapter

log = logging.getLogger("core.ingest")

# Now, we instantiate the Scoring Engine and Adapters.
# These are effectively Singletons within this module scope.
scoring = ScoringEngine()
fmp = FMPAdapter(
    settings.fmp_api_key,
    settings.fmp_rate_limit_per_minute,
    settings.fmp_rate_limit_per_day,
)

def _persist_signal(db: Session, ns: NormalizedSignal, scored: dict) -> Signal:
    # Now, we map the NormalizedSignal and Score results to the Database Model.
    s = Signal(
        source = ns.source,
        symbol = ns.symbol,
        kind = ns.kind,
        direction = ns.direction,
        notional = ns.notional, 
        raw = ns.raw,
        features = scored["features"],
        anomaly_score = float(scored["anomaly_score"]),
        class_label = scored["class_label"],
        class_confidence = float(scored["class_confidence"]),
    )
    # Now, we save to DB.
    db.add(s)
    db.commit()
    db.refresh(s)
    return s

async def _possible_alert(db: Session, signal: Signal) -> None:
    """
    Evaluates if a Signal deserves a User Alert.
    """
    # Now, we check "Must Alert" conditions (High Priority sources).
    must_alert = signal.class_label in ("insider_trade", "congress_trade")
    
    # Now, we check the Anomaly Score against the configured threshold.
    if not must_alert and signal.anomaly_score < settings.anomaly_threshold:
        return # No alert
    
    severity = "high" if signal.anomaly_score >= 0.9 or must_alert else "warn"
    title = f"{signal.symbol}: {signal.class_label} ({signal.source})"
    body = (
        f"Kind = {signal.kind}\n"
        f"Anomaly Score = {signal.anomaly_score:.3f}\n"
        f"Notional = {signal.notional:.2f}\n"
        f"Features = {signal.features}\n"
        f"Direction = {signal.direction}\n"
        
    )
    a = Alert(symbol=signal.symbol, severity=severity, title=title, body=body, signal_ids=[signal.id])
    db.add(a)
    db.commit()

async def ingest_stocks_and_options(db: Session):
    # Dependency Injection: We receive the 'db' session from the caller.
    # This keeps the function pure regarding connection management.
    # STOCK + OPTIONS are per ticker
    for sym in settings.stock_watchlist:
        # 1. Fetch Stock Data
        df = fetch_recent_stock_bars(sym)
        sf = stock_features(df)
        ns = NormalizedSignal(
            source="STOCK",
            symbol=sym,
            kind="stock_move",
            direction="N/A",
            notional=0.0,
            raw={"provider": "yfinance", "rows": int(len(df)), "tail": df.tail(3).to_dict("records") if not df.empty else []},
        )

        # 2. Score & Persist Stock Signal
        scored = scoring.score(ns.source, ns.kind, sf, ns.raw, ns.notional)
        sig = _persist_signal(db, ns, scored)
        _possible_alert(db, sig)

        # 3. Fetch Options Data
        opt = fetch_options_snapshot(sym)
        of = options_features(opt)
        ns2 = NormalizedSignal(
            source="OPTIONS",
            symbol=sym,
            kind="options_snapshot",
            direction="N/A",
            notional=float(opt.get("calls_volume", 0.0) + opt.get("puts_volume", 0.0)),
            raw=opt,
        )
        # 4. Score & Persist Options Signal
        scored2 = scoring.score(ns2.source, ns2.kind, of, ns2.raw, ns2.notional)
        sig2 = _persist_signal(db, ns2, scored2)
        _possible_alert(db, sig2)

async def ingest_polymarket(db: Session) -> None:
    events = await fetch_events(settings.polymarket_query, limit=25)
    for e in events:
        for m in extract_market_signals_from_event(e):
            symbol = (m.get("slug") or m.get("condition_id") or str(m.get("market_id") or "unknown")).upper()
            ns = NormalizedSignal(
                source="POLY",
                symbol=symbol,
                kind="polymarket_market",
                direction="N/A",
                notional=float(m.get("volume") or 0.0),
                raw=m,
            )
            # features minimal for now; anomaly model still benefits from notional_log
            scored = scoring.score(ns.source, ns.kind, {}, ns.raw, ns.notional)
            sig = _persist_signal(db, ns, scored)
            _possible_alert(db, sig)

async def ingest_fmp_altdata(db: Session) -> None:
    # Now, we check if the adapter is enabled (Token present).
    if not fmp.enabled():
        log.info("FMP Adapter Disabled (Check API KEY)")
        return
    
    senate_trades, house_trades, insider_trades = await asyncio,gather(
        fmp.fetch_senate_trades(),
        fmp.fetch_house_trades(),
        fmp.fetch_insider_trades(),
    
    )
    if isinstance(senate_trades, list):
        for row in senate_trades:
            sym = str(row.get("Ticker", "")).upper()
            if not sym or sym == "N/A":
                continue
            
            ns = NormalizedSignal(
                source="SENATE",
                symbol=sym,
                kind="senate_trade",
                direction=str(row.get("Transaction", "") or row.get("transaction") or "N/A").lower(),
                notional=float(row.get("Amount", 0.0) or row.get("amount") or 0.0),
                raw=row,
            )
            scored = scoring.score(ns.source, ns.kind, {}, ns.raw, ns.notional)
            sig = _persist_signal(db, ns, scored)
            await _possible_alert(db, sig)

    if isinstance(house_trades, list):
        for row in house_trades:
            sym = str(row.get("Ticker", "")).upper()
            if not sym or sym == "N/A":
                continue
            
            ns = NormalizedSignal(
                source="HOUSE",
                symbol=sym,
                kind="house_trade",
                direction=str(row.get("Transaction", "")).lower()
                notional=float(row.get("Amount", 0.0) or row.get("amount") or 0.0),
                raw=row,
            )
            scored = scoring.score(ns.source, ns.kind, {}, ns.raw, ns.notional)
            sig = _persist_signal(db, ns, scored)
            await _possible_alert(db, sig)

    if isinstance(insider_trades, list):
        for row in insider_trades:
            sym = str(row.get("Ticker", "")).upper()
            if not sym or sym == "N/A":
                continue
        
            ns = NormalizedSignal(
                source="INSIDER",
                symbol=sym,
                kind="insider_trade",
                direction=str(row.get("Transaction", "")).lower(),
                notional=float(row.get("Value", 0.0) or row.get("value") or 0.0),
                raw=row,
            )
            scored = scoring.score(ns.source, ns.kind, {}, ns.raw, ns.notional)
            sig = _persist_signal(db, ns, scored)
            await _possible_alert(db, sig)

def refit_models_from_db(db: Session) -> None:
    """
    Refits the Anomaly Detection model using recent history.
    In a production enterprise system, this would be an offline batch job (Airflow/Kubeflow).
    For this MVP, we do it in-process on startup.
    """
    # Now, we fetch the last 2000 signals to build a representative dataset.
    rows = db.query(Signal).order_by(Signal.created_at.desc()).limit(2000).all()
    feats = []
    for r in rows:
        try:
            feats.append(r.features)
        except Exception:
            continue
    scoring.fit_anomaly_model(feats)
    log.info(f"refitted anomaly model with {len(feats)} historical signals")
